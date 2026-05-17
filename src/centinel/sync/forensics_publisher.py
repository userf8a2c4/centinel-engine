"""Forensic publisher — runs the inconsistent-acts tracker over stored
snapshots and publishes a panel-ready forensics block plus coverage
accounting to Supabase.

Publicador forense: ejecuta el rastreador de actas inconsistentes sobre los
snapshots almacenados y publica un bloque forense listo para el panel más la
contabilidad de cobertura a Supabase.

Design / Diseño:
- Always non-fatal: local SQLite + hash chain remain the source of truth.
- The forensics block matches exactly the shape `renderForensics` /
  `renderBenford` already consume in web/panel/index.html (no JS changes).
- Coverage accounting makes any capture gap an alert by default: the hole
  itself is the signal (continuous vigilance, not night-only detection).
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from auditor.inconsistent_acts import Anomaly, InconsistentActsTracker

from . import supabase_sync

logger = logging.getLogger(__name__)

_TS_RE = re.compile(r"snapshot_(\d{4}-\d{2}-\d{2})_(\d{2})-(\d{2})-(\d{2})")


def parse_snapshot_timestamp(path: Path) -> Optional[datetime]:
    """Parse the UTC timestamp embedded in a snapshot filename.

    Extrae la marca de tiempo UTC del nombre de archivo del snapshot.
    """
    match = _TS_RE.search(path.name)
    if not match:
        return None
    date_part, hh, mm, ss = match.groups()
    return datetime.fromisoformat(f"{date_part}T{hh}:{mm}:{ss}+00:00")


def build_forensics_block(tracker: InconsistentActsTracker) -> dict[str, Any]:
    """Map tracker detectors to the exact shape the public panel consumes.

    Mapea los detectores del tracker al shape exacto que consume el panel.
    """
    progressive = tracker.detect_progressive_injection()
    if progressive:
        net_swing = progressive.get("net_swing", {})
        total_injected = sum(v for v in net_swing.values() if v > 0)
        progressive_block = {
            "detected": True,
            "num_injections": int(progressive.get("cycles_count", 0)),
            "total_injected": int(total_injected),
            "p_value": float(progressive.get("z_score_pvalue", 1.0)),
        }
    else:
        progressive_block = {
            "detected": False,
            "num_injections": 0,
            "total_injected": 0,
            "p_value": 1.0,
        }

    velocity = tracker.detect_resolution_velocity_anomalies()
    velocity_block = {
        "detected": bool(velocity),
        "max_rate": max((v["rate_per_minute"] for v in velocity), default=0.0),
        "threshold": tracker.max_resolution_rate,
    }

    asymmetry = tracker.detect_asymmetric_benefit()
    if asymmetry and asymmetry.get("significant"):
        asymmetry_block = {
            "detected": True,
            "benefiting_candidate": asymmetry.get("beneficiary", "—"),
            "expected_pct": float(asymmetry.get("normal_proportion", 0.0)),
            "observed_pct": float(asymmetry.get("special_proportion", 0.0)),
        }
    else:
        asymmetry_block = {"detected": False}

    patterns = tracker.detect_hold_and_release()
    if patterns:
        worst = max(patterns, key=lambda p: p["released_actas"])
        duration_min = round(
            (worst["release_timestamp"] - worst["stagnation_start"]).total_seconds() / 60.0,
            1,
        )
        hold_block = {
            "detected": True,
            "stagnation_duration_minutes": duration_min,
            "release_actas": int(worst["released_actas"]),
        }
    else:
        hold_block = {"detected": False}

    benford = tracker.detect_benford_special_scrutiny()
    if benford:
        digits = [
            {
                "d": d,
                "exp": info["expected_pct"],
                "obs": info["observed_pct"],
            }
            for d, info in sorted(benford["digit_analysis"].items())
        ]
        benford_block = {
            "chi2": float(benford["chi2_statistic"]),
            "pvalue": float(benford["chi2_pvalue"]),
            "digits": digits,
        }
    else:
        benford_block = {"chi2": 0.0, "pvalue": 1.0, "digits": []}

    anomalies = tracker.detect_anomalies()
    outliers = [
        {
            "timestamp": a.timestamp.isoformat(),
            "delta_votes": a.metadata.get("delta_votes"),
        }
        for a in anomalies
        if a.kind == "vote_outlier_3sigma"
    ]
    zscore_block = {"detected": bool(outliers), "outliers": outliers}

    blackouts = tracker.detect_blackout_windows()
    gaps = [
        {
            "gap_start": b["gap_start"].isoformat(),
            "gap_end": b["gap_end"].isoformat(),
            "gap_minutes": b["gap_minutes"],
            "delta_inconsistent": b["delta_inconsistent"],
            "trend_shifts_pp": b["trend_shifts_pp"],
            # A gap that coincides with a trend shift is an interference signal.
            "interference_signal": bool(b["trend_shifts_pp"]),
        }
        for b in blackouts
    ]
    blackout_block = {"detected": bool(gaps), "gaps": gaps}

    return {
        "progressive_injection": progressive_block,
        "velocity_anomaly": velocity_block,
        "asymmetric_benefit": asymmetry_block,
        "hold_and_release": hold_block,
        "benford": benford_block,
        "zscore": zscore_block,
        "blackout": blackout_block,
    }


def build_coverage(
    timestamps: list[datetime],
    *,
    target_cadence_minutes: float,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    """Compute capture-coverage accounting; any gap is suspicious by default.

    Calcula la contabilidad de cobertura de captura; todo hueco es sospechoso
    por defecto.
    """
    now = now or datetime.now(timezone.utc)
    ordered = sorted(timestamps)
    if not ordered:
        return {
            "monitoring_since": None,
            "last_capture": None,
            "target_cadence_minutes": target_cadence_minutes,
            "coverage_pct": 0.0,
            "open_gap_minutes": 0.0,
            "gaps_count": 0,
            "gaps": [],
        }

    grace_seconds = target_cadence_minutes * 60.0 * 2.0
    first, last = ordered[0], ordered[-1]
    total_span = (last - first).total_seconds()

    covered = 0.0
    gaps: list[dict[str, Any]] = []
    for prev, curr in zip(ordered, ordered[1:]):
        delta = (curr - prev).total_seconds()
        if delta <= grace_seconds:
            covered += delta
        else:
            covered += grace_seconds
            gaps.append(
                {
                    "gap_start": prev.isoformat(),
                    "gap_end": curr.isoformat(),
                    "gap_minutes": round(delta / 60.0, 1),
                }
            )

    coverage_pct = round((covered / total_span) * 100.0, 2) if total_span > 0 else 100.0

    open_gap_seconds = (now - last).total_seconds()
    open_gap_minutes = (
        round(open_gap_seconds / 60.0, 1) if open_gap_seconds > grace_seconds else 0.0
    )

    return {
        "monitoring_since": first.isoformat(),
        "last_capture": last.isoformat(),
        "target_cadence_minutes": target_cadence_minutes,
        "coverage_pct": coverage_pct,
        "open_gap_minutes": open_gap_minutes,
        "gaps_count": len(gaps),
        "gaps": gaps,
    }


def _load_tracker(snapshot_paths: list[Path]) -> tuple[InconsistentActsTracker, list[datetime]]:
    """Feed ordered snapshots into a fresh tracker; return it with timestamps.

    Alimenta snapshots ordenados a un tracker nuevo; lo devuelve con marcas.
    """
    tracker = InconsistentActsTracker()
    timestamps: list[datetime] = []
    pairs: list[tuple[datetime, Path]] = []
    for path in snapshot_paths:
        ts = parse_snapshot_timestamp(path)
        if ts is None:
            continue
        pairs.append((ts, path))

    for ts, path in sorted(pairs, key=lambda item: item[0]):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("forensics_snapshot_unreadable path=%s error=%s", path, exc)
            continue
        try:
            tracker.load_snapshot(payload, ts)
            timestamps.append(ts)
        except (KeyError, ValueError, TypeError) as exc:
            logger.warning("forensics_snapshot_skipped path=%s error=%s", path, exc)

    return tracker, timestamps


def run_and_publish(
    snapshot_paths: list[Path],
    *,
    captured_at: str,
    chain_hash: str,
    merkle_root: str,
    chain_length: int = 0,
    target_cadence_minutes: float = 5.0,
    dept_code: Optional[str] = None,
) -> Optional[int]:
    """Run forensics over snapshots and publish to Supabase. Always non-fatal.

    Ejecuta forenses sobre los snapshots y publica a Supabase. No fatal.

    Returns the inserted snapshot row id (or None).
    """
    if not supabase_sync.is_configured():
        logger.info("forensics_publish_skipped supabase_not_configured")
        return None

    try:
        tracker, timestamps = _load_tracker(snapshot_paths)
        forensics = build_forensics_block(tracker)
        coverage = build_coverage(
            timestamps, target_cadence_minutes=target_cadence_minutes
        )
        anomalies: list[Anomaly] = tracker.detect_anomalies()
    except Exception as exc:  # noqa: BLE001 - publishing must never break pipeline
        logger.warning("forensics_build_failed error=%s", exc)
        return None

    coverage_breached = (
        coverage["coverage_pct"] < 100.0 or coverage["open_gap_minutes"] > 0.0
    )
    anomaly_flag = (
        any(a.severity == "critical" for a in anomalies) or coverage_breached
    )
    alert_state = "anomaly" if anomaly_flag else "normal"

    raw_meta = {"forensics": forensics, "coverage": coverage}

    snapshot_id = supabase_sync.push_snapshot(
        captured_at=captured_at,
        chain_hash=chain_hash,
        merkle_root=merkle_root,
        chain_length=chain_length,
        dept_code=dept_code,
        anomaly_flag=anomaly_flag,
        alert_state=alert_state,
        raw_meta=raw_meta,
    )

    for anomaly in anomalies:
        if anomaly.severity != "critical":
            continue
        supabase_sync.push_alert(
            created_at=anomaly.timestamp.isoformat(),
            severity="CRITICAL",
            description=anomaly.message,
            kind=anomaly.kind,
            dept_code=dept_code,
            snapshot_id=snapshot_id,
        )

    # The hole itself is the alert: every uncovered window is reported even
    # when no trend shift follows it.
    for gap in coverage["gaps"]:
        supabase_sync.push_alert(
            created_at=gap["gap_end"],
            severity="HIGH",
            description=(
                f"Ventana sin captura de {gap['gap_minutes']:.0f} min "
                f"({gap['gap_start']} → {gap['gap_end']}). "
                "Toda ventana sin datos es sospechosa por defecto."
            ),
            kind="capture_gap",
            dept_code=dept_code,
            snapshot_id=snapshot_id,
        )
    if coverage["open_gap_minutes"] > 0.0:
        supabase_sync.push_alert(
            created_at=datetime.now(timezone.utc).isoformat(),
            severity="HIGH",
            description=(
                f"Captura interrumpida: {coverage['open_gap_minutes']:.0f} min "
                "sin nuevos datos. El canal puede estar cortado."
            ),
            kind="capture_gap_open",
            dept_code=dept_code,
            snapshot_id=snapshot_id,
        )

    logger.info(
        "forensics_published id=%s coverage=%.1f anomalies=%d",
        snapshot_id,
        coverage["coverage_pct"],
        len(anomalies),
    )
    return snapshot_id
