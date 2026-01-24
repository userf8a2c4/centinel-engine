"""Motor de simulación retroactiva para snapshots históricos."""

from __future__ import annotations

import csv
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from sentinel.core.models import CandidateResult, Meta, Snapshot, Totals
from sentinel.core.hashchain import compute_hash
from sentinel.core.normalize import snapshot_to_canonical_json, snapshot_to_dict
from sentinel.core.rules.common import (
    extract_candidate_votes,
    extract_registered_voters,
    extract_total_votes,
    extract_vote_breakdown,
)
from sentinel.core.rules_engine import RulesEngine
from sentinel.core.storage import LocalSnapshotStore
from utils.file_utils import (
    get_nested_value,
    iter_nested_fields,
    list_snapshot_files,
    parse_filename_timestamp,
    sorted_by_filename_timestamp,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SimulationSnapshotResult:
    """Resultado completo de un snapshot simulado."""

    source_file: str
    source_timestamp: str
    simulated_timestamp: str
    snapshot_hash: str
    previous_hash: Optional[str]
    rules: dict
    metrics: dict
    storage: dict
    errors: list[str]


def _safe_int(value: object, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(str(value).replace(",", "").split(".")[0])
    except (ValueError, TypeError):
        return default


def _extract_vote_fields(
    payload: dict,
    fields_list: Iterable[str],
    pattern: Optional[str],
) -> Dict[str, int]:
    results: Dict[str, int] = {}
    for field in fields_list:
        value = get_nested_value(payload, field)
        if value is None:
            for key, nested_value in iter_nested_fields(payload):
                if key == field:
                    value = nested_value
                    break
        if value is None:
            continue
        results[field] = _safe_int(value)

    if pattern:
        regex = re.compile(pattern)
        for key, value in iter_nested_fields(payload):
            if regex.match(key):
                results.setdefault(key, _safe_int(value))

    return results


def _build_candidate_results(
    raw: dict,
    vote_fields: Dict[str, int],
) -> list[CandidateResult]:
    candidate_map = extract_candidate_votes(raw)
    if not candidate_map and vote_fields:
        ordered = sorted(vote_fields.items(), key=lambda item: item[0])
        return [
            CandidateResult(
                slot=idx,
                votes=votes,
                candidate_id=field,
                name=field,
                party=None,
            )
            for idx, (field, votes) in enumerate(ordered, start=1)
        ]

    candidates: list[CandidateResult] = []
    items = sorted(candidate_map.items(), key=lambda item: item[0])
    for idx, (key, payload) in enumerate(items, start=1):
        candidates.append(
            CandidateResult(
                slot=idx,
                votes=_safe_int(payload.get("votes")),
                candidate_id=str(payload.get("id") or key),
                name=str(payload.get("name") or key),
                party=payload.get("party"),
            )
        )

    existing_keys = {
        candidate.candidate_id or candidate.name or str(candidate.slot)
        for candidate in candidates
    }
    for field_name, votes in sorted(vote_fields.items(), key=lambda item: item[0]):
        if field_name in existing_keys:
            continue
        candidates.append(
            CandidateResult(
                slot=len(candidates) + 1,
                votes=votes,
                candidate_id=field_name,
                name=field_name,
                party=None,
            )
        )
    return candidates


def _build_totals(raw: dict) -> Totals:
    breakdown = extract_vote_breakdown(raw)
    total_votes = extract_total_votes(raw)
    valid_votes = breakdown.get("valid_votes") or 0
    null_votes = breakdown.get("null_votes") or 0
    blank_votes = breakdown.get("blank_votes") or 0
    if not total_votes and any([valid_votes, null_votes, blank_votes]):
        total_votes = valid_votes + null_votes + blank_votes

    return Totals(
        registered_voters=extract_registered_voters(raw) or 0,
        total_votes=total_votes or 0,
        valid_votes=valid_votes,
        null_votes=null_votes,
        blank_votes=blank_votes,
    )


def _first_digit_distribution(values: Iterable[int]) -> dict:
    digits = [int(str(value)[0]) for value in values if value and str(value)[0].isdigit()]
    counts = {digit: digits.count(digit) for digit in range(1, 10)}
    total = len(digits) or 1
    percentages = {digit: round((count / total) * 100, 2) for digit, count in counts.items()}
    return {"counts": counts, "percentages": percentages, "samples": len(digits)}


def _last_digit_distribution(values: Iterable[int]) -> dict:
    digits = [abs(value) % 10 for value in values if value is not None]
    counts = {digit: digits.count(digit) for digit in range(10)}
    total = len(digits) or 1
    percentages = {digit: round((count / total) * 100, 2) for digit, count in counts.items()}
    return {"counts": counts, "percentages": percentages, "samples": len(digits)}


def _candidate_vote_deltas(
    current: list[CandidateResult],
    previous: list[CandidateResult] | None,
) -> dict:
    if not previous:
        return {"total_delta": 0, "per_candidate": {}}

    def key_for(candidate: CandidateResult) -> str:
        return candidate.candidate_id or candidate.name or str(candidate.slot)

    prev_map = {key_for(candidate): candidate.votes for candidate in previous}
    deltas: dict[str, int] = {}
    total_delta = 0
    for candidate in current:
        key = key_for(candidate)
        prev_votes = prev_map.get(key, 0)
        delta = candidate.votes - prev_votes
        deltas[key] = delta
        total_delta += delta
    return {"total_delta": total_delta, "per_candidate": deltas}


class RetroSimulationEngine:
    """Ejecuta simulaciones retroactivas a partir de snapshots en disco."""

    def __init__(self, config: dict) -> None:
        self.config = config
        self.data_folder = Path(config.get("data_folder", "data"))
        self.file_pattern = config.get("file_pattern", "*.json")
        self.sort_by = config.get("sort_by", "filename_timestamp")
        self.interval_seconds = int(config.get("simulation_interval_seconds", 600))
        self.country = config.get("country", "HN")
        self.year = int(config.get("year", 2025))
        self.scope = config.get("scope", "NATIONAL")
        self.department_code = config.get("department_code", "00")
        self.sleep_enabled = bool(config.get("sleep_between_snapshots", False))
        self.results_dir = Path(config.get("results_dir", "results/simulation"))
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.rules_log_path = self.results_dir / "rules_log.jsonl"
        self.rules_engine = RulesEngine(
            config=self._build_rules_config(),
            log_path=self.rules_log_path,
        )
        db_path = config.get("database_path", "data/snapshots_simulation.db")
        self.store = LocalSnapshotStore(
            db_path=db_path,
            publish_blockchain=False,
            publish_ipfs=False,
        )

    def _build_rules_config(self) -> dict:
        rules_config = json.loads(json.dumps(self.config.get("rules", {})))
        rules_config.setdefault("global_enabled", True)
        enabled_rules = self.config.get("integrity_rules")
        if enabled_rules:
            enabled = {str(rule).strip() for rule in enabled_rules}
            for key, value in rules_config.items():
                if key == "global_enabled" or not isinstance(value, dict):
                    continue
                value["enabled"] = key in enabled
        return {**self.config, "rules": rules_config}

    def _sorted_files(self) -> list[Path]:
        files = list_snapshot_files(self.data_folder, self.file_pattern)
        if self.sort_by == "filename_timestamp":
            return sorted_by_filename_timestamp(files)
        return sorted(files)

    def _load_json(self, path: Path) -> tuple[dict | None, list[str]]:
        errors: list[str] = []
        try:
            return json.loads(path.read_text(encoding="utf-8")), errors
        except json.JSONDecodeError as exc:
            errors.append(f"json_error: {exc}")
            return None, errors

    def _resolve_source_timestamp(self, path: Path) -> datetime:
        parsed = parse_filename_timestamp(path.name)
        if parsed:
            return parsed
        fallback = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        return fallback

    def _build_snapshot(
        self,
        raw: dict,
        timestamp: datetime,
        vote_fields: Dict[str, int],
    ) -> Snapshot:
        candidates = _build_candidate_results(raw, vote_fields)
        totals = _build_totals(raw)
        meta = Meta(
            election=f"{self.country}-PRESIDENTIAL",
            year=self.year,
            source="historical",
            scope=self.scope,
            department_code=self.department_code,
            timestamp_utc=timestamp.isoformat(),
        )
        return Snapshot(meta=meta, totals=totals, candidates=candidates)

    def _collect_vote_fields(self, raw: dict) -> Dict[str, int]:
        fields_list = (
            self.config.get("vote_fields_list")
            or self.config.get("vote_fields")
            or []
        )
        if isinstance(fields_list, str):
            fields_list = [item.strip() for item in fields_list.split(",") if item.strip()]
        pattern = self.config.get("vote_fields_pattern") or self.config.get(
            "vote_fields_regex"
        )
        return _extract_vote_fields(raw, fields_list, pattern)

    def _compute_metrics(
        self,
        snapshot: Snapshot,
        previous_snapshot: Snapshot | None,
        simulated_timestamp: datetime,
    ) -> dict:
        candidate_votes = [candidate.votes for candidate in snapshot.candidates]
        metrics = {
            "first_digit_distribution": _first_digit_distribution(candidate_votes),
            "last_digit_distribution": _last_digit_distribution(candidate_votes),
            "candidate_changes": _candidate_vote_deltas(
                snapshot.candidates,
                previous_snapshot.candidates if previous_snapshot else None,
            ),
            "totals": snapshot.totals.__dict__,
            "activity_hour": simulated_timestamp.hour,
        }
        if previous_snapshot:
            metrics["totals_delta"] = (
                snapshot.totals.total_votes - previous_snapshot.totals.total_votes
            )
        else:
            metrics["totals_delta"] = 0
        return metrics

    def run(self) -> list[SimulationSnapshotResult]:
        files = self._sorted_files()
        if not files:
            logger.warning("simulation_no_files folder=%s", self.data_folder)
            return []

        results: list[SimulationSnapshotResult] = []
        previous_hash: Optional[str] = None
        previous_snapshot: Snapshot | None = None
        simulated_timestamp: Optional[datetime] = None

        for idx, path in enumerate(files):
            raw, errors = self._load_json(path)
            if raw is None:
                results.append(
                    SimulationSnapshotResult(
                        source_file=path.name,
                        source_timestamp="",
                        simulated_timestamp="",
                        snapshot_hash="",
                        previous_hash=previous_hash,
                        rules={"alerts": [], "critical_alerts": [], "pause_snapshots": False},
                        metrics={},
                        storage={},
                        errors=errors,
                    )
                )
                continue

            source_ts = self._resolve_source_timestamp(path)
            if simulated_timestamp is None:
                simulated_timestamp = source_ts
            else:
                simulated_timestamp = simulated_timestamp + timedelta(
                    seconds=self.interval_seconds
                )

            vote_fields = self._collect_vote_fields(raw)
            snapshot = self._build_snapshot(raw, simulated_timestamp, vote_fields)
            canonical_json = snapshot_to_canonical_json(snapshot)
            root_hash = compute_hash(canonical_json, previous_hash=None)
            snapshot_hash = self.store.store_snapshot(snapshot, previous_hash)
            snapshot_dict = snapshot_to_dict(snapshot)
            rules_result = self.rules_engine.run(
                snapshot_dict,
                snapshot_to_dict(previous_snapshot) if previous_snapshot else None,
                snapshot_id=snapshot_hash,
            )

            metrics = self._compute_metrics(
                snapshot,
                previous_snapshot,
                simulated_timestamp,
            )
            storage = {
                "db_path": self.store.db_path,
                "root_hash": root_hash,
                "chained_hash": snapshot_hash,
                "canonical_json_length": len(canonical_json),
            }

            results.append(
                SimulationSnapshotResult(
                    source_file=path.name,
                    source_timestamp=source_ts.isoformat(),
                    simulated_timestamp=simulated_timestamp.isoformat(),
                    snapshot_hash=snapshot_hash,
                    previous_hash=previous_hash,
                    rules={
                        "alerts": rules_result.alerts,
                        "critical_alerts": rules_result.critical_alerts,
                        "pause_snapshots": rules_result.pause_snapshots,
                    },
                    metrics=metrics,
                    storage=storage,
                    errors=errors,
                )
            )

            previous_hash = snapshot_hash
            previous_snapshot = snapshot

            if self.sleep_enabled and idx < len(files) - 1:
                logger.info(
                    "simulation_sleep seconds=%s snapshot=%s",
                    self.interval_seconds,
                    path.name,
                )
                time_to_sleep = self.interval_seconds
                while time_to_sleep > 0:
                    sleep_chunk = min(5, time_to_sleep)
                    time_to_sleep -= sleep_chunk
                    if sleep_chunk:
                        import time

                        time.sleep(sleep_chunk)

        self._write_outputs(results)
        return results

    def _write_outputs(self, results: list[SimulationSnapshotResult]) -> None:
        snapshots_path = self.results_dir / "snapshots.jsonl"
        metrics_csv_path = self.results_dir / "metrics_evolution.csv"
        summary_path = self.results_dir / "summary.json"

        with snapshots_path.open("w", encoding="utf-8") as handle:
            for result in results:
                handle.write(
                    json.dumps(result.__dict__, ensure_ascii=False, sort_keys=True)
                    + "\n"
                )

        fieldnames = [
            "index",
            "source_file",
            "source_timestamp",
            "simulated_timestamp",
            "snapshot_hash",
            "previous_hash",
            "total_votes",
            "totals_delta",
            "alerts_count",
            "critical_alerts_count",
        ]
        with metrics_csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for idx, result in enumerate(results):
                totals = result.metrics.get("totals", {})
                writer.writerow(
                    {
                        "index": idx,
                        "source_file": result.source_file,
                        "source_timestamp": result.source_timestamp,
                        "simulated_timestamp": result.simulated_timestamp,
                        "snapshot_hash": result.snapshot_hash,
                        "previous_hash": result.previous_hash,
                        "total_votes": totals.get("total_votes"),
                        "totals_delta": result.metrics.get("totals_delta"),
                        "alerts_count": len(result.rules.get("alerts", [])),
                        "critical_alerts_count": len(
                            result.rules.get("critical_alerts", [])
                        ),
                    }
                )

        activity_by_hour: dict[str, int] = {}
        for result in results:
            hour = result.metrics.get("activity_hour")
            if hour is None:
                continue
            key = f"{hour:02d}:00"
            activity_by_hour[key] = activity_by_hour.get(key, 0) + 1

        summary = {
            "snapshots": len(results),
            "results_dir": str(self.results_dir),
            "metrics_csv": str(metrics_csv_path),
            "activity_by_hour": dict(sorted(activity_by_hour.items())),
        }
        summary_path.write_text(
            json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def close(self) -> None:
        self.store.close()
