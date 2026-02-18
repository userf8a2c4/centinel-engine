"""Motor sandbox aislado para pruebas de caos y laboratorio de reglas.

Ejecuta reglas sobre datos en memoria sin tocar producción (SQLite, hash chain, etc.).
Todas las operaciones son efímeras y se descartan al cerrar la sesión.

---

Isolated sandbox engine for chaos testing and rules laboratory.

Runs rules on in-memory data without touching production (SQLite, hash chain, etc.).
All operations are ephemeral and discarded when the session ends.
"""

from __future__ import annotations

import copy
import hashlib
import importlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Rule registry – maps config keys to module paths
# ---------------------------------------------------------------------------

RULE_MODULES = {
    "benford_law": "sentinel.core.rules.benford_law_rule",
    "basic_diff": "sentinel.core.rules.basic_diff_rule",
    "trend_shift": "sentinel.core.rules.trend_shift_rule",
    "processing_speed": "sentinel.core.rules.processing_speed_rule",
    "participation_anomaly": "sentinel.core.rules.participation_anomaly_rule",
    "ml_outliers": "sentinel.core.rules.ml_outliers_rule",
}

# Default parameter values for each rule (used as slider defaults)
DEFAULT_RULE_PARAMS: dict[str, dict[str, Any]] = {
    "benford_law": {
        "chi_square_threshold": 0.05,
        "deviation_pct": 15.0,
        "min_samples": 10,
    },
    "basic_diff": {
        "relative_vote_change_pct": 15.0,
    },
    "trend_shift": {
        "threshold_percent": 10.0,
        "max_hours": 3.0,
    },
    "processing_speed": {
        "max_actas_per_15min": 500,
    },
    "participation_anomaly": {
        "scrutiny_jump_pct": 5.0,
    },
    "ml_outliers": {
        "contamination": 0.1,
        "min_samples": 5,
    },
}


# ---------------------------------------------------------------------------
# Load historical 2025 snapshots from disk
# ---------------------------------------------------------------------------


def _safe_int(value: Any) -> int:
    """Parse a string like '1,023,359' into an int."""
    if value is None:
        return 0
    try:
        return int(str(value).replace(",", "").split(".")[0])
    except (TypeError, ValueError):
        return 0


def _parse_timestamp_from_filename(filename: str) -> datetime | None:
    """Extract datetime from filenames like '...2025-12-03 14_32_13.json'."""
    name = Path(filename).stem
    parts = name.rsplit(" ", 2)
    if len(parts) < 3:
        return None
    try:
        date_str = parts[-2]
        time_str = parts[-1].replace("_", ":")
        return datetime.fromisoformat(f"{date_str}T{time_str}")
    except (ValueError, IndexError):
        return None


def load_historical_snapshots(data_dir: str | None = None) -> list[dict[str, Any]]:
    """Load all 2025 JSON snapshots sorted by timestamp.

    Returns a list of dicts with raw payload + parsed timestamp.
    """
    if data_dir is None:
        candidates = [
            Path("data/2025"),
            Path(__file__).resolve().parents[3] / "data" / "2025",
        ]
        data_path = next((p for p in candidates if p.exists()), None)
        if data_path is None:
            return []
    else:
        data_path = Path(data_dir)

    if not data_path.exists():
        return []

    snapshots: list[dict[str, Any]] = []
    for filepath in sorted(data_path.glob("*.json")):
        try:
            payload = json.loads(filepath.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        ts = _parse_timestamp_from_filename(filepath.name)
        if ts is None:
            continue
        snapshots.append(
            {"payload": payload, "timestamp": ts, "filename": filepath.name}
        )

    return sorted(snapshots, key=lambda s: s["timestamp"])


# ---------------------------------------------------------------------------
# Convert raw CNE snapshot to the dict format that rules expect
# ---------------------------------------------------------------------------


def snapshot_to_rule_format(raw: dict[str, Any], timestamp: datetime) -> dict[str, Any]:
    """Convert a raw CNE JSON snapshot into the flat dict rules expect."""
    resultados = raw.get("resultados", [])
    estadisticas = raw.get("estadisticas", {})
    totalizacion = estadisticas.get("totalizacion_actas", {})
    distribucion = estadisticas.get("distribucion_votos", {})
    estado_actas = estadisticas.get("estado_actas_divulgadas", {})

    candidates = []
    for r in resultados:
        candidates.append(
            {
                "name": r.get("candidato", ""),
                "party": r.get("partido", ""),
                "votes": _safe_int(r.get("votos")),
                "id": r.get("candidato", ""),
            }
        )

    return {
        "timestamp": timestamp.isoformat(),
        "departamento": "NACIONAL",
        "candidatos": candidates,
        "totals": {
            "total_votes": _safe_int(distribucion.get("validos", 0))
            + _safe_int(distribucion.get("nulos", 0))
            + _safe_int(distribucion.get("blancos", 0)),
            "valid_votes": _safe_int(distribucion.get("validos")),
            "null_votes": _safe_int(distribucion.get("nulos")),
            "blank_votes": _safe_int(distribucion.get("blancos")),
            "actas_totales": _safe_int(totalizacion.get("actas_totales")),
            "actas_procesadas": _safe_int(totalizacion.get("actas_divulgadas")),
        },
        "actas": {
            "totales": _safe_int(totalizacion.get("actas_totales")),
            "divulgadas": _safe_int(totalizacion.get("actas_divulgadas")),
            "correctas": _safe_int(estado_actas.get("actas_correctas")),
            "inconsistentes": _safe_int(estado_actas.get("actas_inconsistentes")),
        },
    }


# ---------------------------------------------------------------------------
# Convert a rule-format dict to a DataFrame row for dashboard display
# ---------------------------------------------------------------------------


def rule_format_to_df_row(data: dict[str, Any]) -> dict[str, Any]:
    """Turn a rule-format dict into a flat row suitable for a DataFrame."""
    totals = data.get("totals", {})
    candidates = data.get("candidatos", [])

    row: dict[str, Any] = {
        "timestamp": pd.Timestamp(data.get("timestamp", "")),
        "departamento": data.get("departamento", "NACIONAL"),
        "total_votos": totals.get("total_votes", 0),
        "actas_divulgadas": totals.get("actas_procesadas", 0),
        "actas_totales": totals.get("actas_totales", 0),
        "votos_validos": totals.get("valid_votes", 0),
        "votos_nulos": totals.get("null_votes", 0),
        "votos_blancos": totals.get("blank_votes", 0),
    }

    for c in candidates:
        name = c.get("party", "") or c.get("name", "")
        short = _short_party_name(name)
        row[short] = c.get("votes", 0)

    hash_input = (
        f"{data.get('timestamp')}_{row['total_votos']}_{row.get('actas_divulgadas')}"
    )
    row["hash"] = hashlib.sha256(hash_input.encode()).hexdigest()

    return row


def _short_party_name(full_name: str) -> str:
    """Map full party names to short display names."""
    mapping = {
        "PARTIDO LIBERAL DE HONDURAS": "Liberal",
        "PARTIDO NACIONAL DE HONDURAS": "Nacional",
        "PARTIDO LIBERTAD Y REFUNDACION": "Libre",
        "PARTIDO INNOVACION Y UNIDAD SOCIAL DEMOCRATA": "PINU-SD",
        "PARTIDO DEMOCRATA CRISTIANO DE HONDURAS": "DC",
    }
    for key, short in mapping.items():
        if key in full_name.upper():
            return short
    return full_name[:15]


# ---------------------------------------------------------------------------
# Chaos injection utilities
# ---------------------------------------------------------------------------


def inject_vote_spike(
    snapshot: dict[str, Any], candidate_idx: int, extra_votes: int
) -> dict[str, Any]:
    """Add extra votes to a specific candidate (simulates ballot stuffing)."""
    modified = copy.deepcopy(snapshot)
    candidates = modified.get("candidatos", [])
    if 0 <= candidate_idx < len(candidates):
        candidates[candidate_idx]["votes"] = (
            candidates[candidate_idx].get("votes", 0) + extra_votes
        )
        totals = modified.get("totals", {})
        totals["total_votes"] = totals.get("total_votes", 0) + extra_votes
        totals["valid_votes"] = totals.get("valid_votes", 0) + extra_votes
    return modified


def inject_arithmetic_mismatch(snapshot: dict[str, Any], offset: int) -> dict[str, Any]:
    """Break arithmetic consistency: total != sum of candidates."""
    modified = copy.deepcopy(snapshot)
    totals = modified.get("totals", {})
    totals["total_votes"] = totals.get("total_votes", 0) + offset
    return modified


def inject_vote_regression(
    snapshot: dict[str, Any], candidate_idx: int, reduction: int
) -> dict[str, Any]:
    """Reduce a candidate's votes (simulates impossible regression)."""
    modified = copy.deepcopy(snapshot)
    candidates = modified.get("candidatos", [])
    if 0 <= candidate_idx < len(candidates):
        candidates[candidate_idx]["votes"] = max(
            0, candidates[candidate_idx].get("votes", 0) - reduction
        )
    return modified


def inject_acta_speed_anomaly(
    snapshot: dict[str, Any], extra_actas: int
) -> dict[str, Any]:
    """Inflate processed actas to trigger speed anomaly."""
    modified = copy.deepcopy(snapshot)
    actas = modified.get("actas", {})
    actas["divulgadas"] = actas.get("divulgadas", 0) + extra_actas
    totals = modified.get("totals", {})
    totals["actas_procesadas"] = totals.get("actas_procesadas", 0) + extra_actas
    return modified


def inject_scrutiny_jump(snapshot: dict[str, Any], jump_pct: float) -> dict[str, Any]:
    """Add a scrutiny percentage field that jumps abruptly."""
    modified = copy.deepcopy(snapshot)
    actas = modified.get("actas", {})
    total = actas.get("totales", 19152)
    current_divulgadas = actas.get("divulgadas", 0)
    new_divulgadas = min(total, int(current_divulgadas + total * jump_pct / 100))
    actas["divulgadas"] = new_divulgadas
    totals = modified.get("totals", {})
    totals["actas_procesadas"] = new_divulgadas
    return modified


def inject_benford_violation(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Replace vote counts with numbers that violate Benford's law (all start with 1)."""
    modified = copy.deepcopy(snapshot)
    candidates = modified.get("candidatos", [])
    rng = np.random.default_rng(99)
    for c in candidates:
        base = rng.integers(100000, 199999)
        c["votes"] = int(base)
    total = sum(c["votes"] for c in candidates)
    totals = modified.get("totals", {})
    totals["total_votes"] = total
    totals["valid_votes"] = total
    return modified


CHAOS_INJECTIONS = {
    "spike_votos": {
        "label": "Inyectar pico de votos",
        "description": "Agrega votos masivos a un candidato (ballot stuffing)",
        "fn": "inject_vote_spike",
    },
    "descuadre_aritmetico": {
        "label": "Descuadre aritmético",
        "description": "Total != suma de candidatos",
        "fn": "inject_arithmetic_mismatch",
    },
    "regresion_votos": {
        "label": "Regresión de votos",
        "description": "Reduce votos de un candidato (imposible en elección real)",
        "fn": "inject_vote_regression",
    },
    "velocidad_actas": {
        "label": "Velocidad anómala de actas",
        "description": "Infla actas procesadas a velocidad no humana",
        "fn": "inject_acta_speed_anomaly",
    },
    "salto_escrutinio": {
        "label": "Salto de escrutinio",
        "description": "Salto abrupto en porcentaje escrutado",
        "fn": "inject_scrutiny_jump",
    },
    "violacion_benford": {
        "label": "Violación Ley de Benford",
        "description": "Reemplaza votos con números que violan Benford",
        "fn": "inject_benford_violation",
    },
}


# ---------------------------------------------------------------------------
# Sandbox rule execution (in-memory, no side effects)
# ---------------------------------------------------------------------------


def run_rules_sandbox(
    current_data: dict[str, Any],
    previous_data: dict[str, Any] | None,
    rule_configs: dict[str, dict[str, Any]],
    enabled_rules: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Execute rules in sandbox mode.

    Uses the real rule modules but avoids any persistent side effects:
    - irreversibility_rule is skipped (writes to SQLite)
    - ml_outliers uses a local history copy
    """
    all_alerts: list[dict[str, Any]] = []
    rules_to_run = enabled_rules or list(RULE_MODULES.keys())

    for rule_name in rules_to_run:
        module_path = RULE_MODULES.get(rule_name)
        if not module_path:
            continue
        config = rule_configs.get(rule_name, DEFAULT_RULE_PARAMS.get(rule_name, {}))
        try:
            module = importlib.import_module(module_path)
            alerts = module.apply(current_data, previous_data, config)
            for alert in alerts:
                alert["rule"] = rule_name
            all_alerts.extend(alerts)
        except Exception as exc:
            all_alerts.append(
                {
                    "type": f"Error en regla {rule_name}",
                    "severity": "Low",
                    "department": "SISTEMA",
                    "justification": str(exc),
                    "rule": rule_name,
                }
            )

    return all_alerts


# ---------------------------------------------------------------------------
# Build replay DataFrame from historical snapshots
# ---------------------------------------------------------------------------


def build_replay_dataframe(snapshots: list[dict[str, Any]]) -> pd.DataFrame:
    """Convert a list of historical snapshots into a DataFrame for the dashboard."""
    rows = []
    for snap in snapshots:
        rule_data = snapshot_to_rule_format(snap["payload"], snap["timestamp"])
        row = rule_format_to_df_row(rule_data)
        rows.append(row)

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp").reset_index(drop=True)

    return df
