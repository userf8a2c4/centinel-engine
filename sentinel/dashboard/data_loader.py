"""Utilities to load snapshot data for Streamlit dashboards."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
from typing import Any, Iterable

from dateutil import parser
import pandas as pd
import requests

from sentinel.core.normalyze import normalize_snapshot, snapshot_to_dict


REPO_OWNER = "userf8a2c4"
REPO_NAME = "sentinel"
BRANCH = "dev-v3"
SNAPSHOT_DIRS = ("data", "tests/fixtures/snapshots_2025")

RAW_BASE = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/{BRANCH}"
TREE_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/git/trees/{BRANCH}?recursive=1"


@dataclass(frozen=True)
class SnapshotRecord:
    source_path: str
    raw_payload: dict[str, Any]
    normalized: dict[str, Any]
    timestamp: datetime
    department_name: str


def _safe_int(value: Any) -> int:
    try:
        if value is None:
            return 0
        return int(str(value).replace(",", "").split(".")[0])
    except (TypeError, ValueError):
        return 0


def _payload_has_signal(payload: dict[str, Any]) -> bool:
    numeric_keys = [
        "votos_emitidos",
        "votos_validos",
        "votos_nulos",
        "votos_blancos",
        "inscritos",
        "total_votes",
        "valid_votes",
        "null_votes",
        "blank_votes",
        "registered_voters",
    ]
    for key in numeric_keys:
        if _safe_int(payload.get(key)) > 0:
            return True

    candidates = payload.get("candidatos") or payload.get("candidates")
    if isinstance(candidates, list):
        return any(
            _safe_int(item.get("votos") or item.get("votes")) > 0 for item in candidates
        )
    return False


def _extract_department(payload: dict[str, Any]) -> str:
    return (
        payload.get("departamento")
        or payload.get("department")
        or payload.get("depto")
        or payload.get("dept")
        or "Desconocido"
    )


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return parser.parse(value)
    except (parser.ParserError, TypeError, ValueError):
        return None


def _timestamp_from_filename(filename: str) -> datetime | None:
    cleaned = (
        filename.replace("snapshot_", "")
        .replace(".json", "")
        .replace("T", " ")
        .replace("Z", "")
    )
    cleaned = cleaned.replace("_", " ")
    return _parse_timestamp(cleaned)


def _extract_timestamp(payload: dict[str, Any], source_path: str) -> datetime:
    for key in ("timestamp_utc", "timestamp", "fecha", "date"):
        parsed = _parse_timestamp(payload.get(key))
        if parsed:
            return parsed
    fallback = _timestamp_from_filename(Path(source_path).name)
    return fallback or datetime.utcnow()


def list_snapshot_paths(snapshot_dirs: Iterable[str] = SNAPSHOT_DIRS) -> list[str]:
    local_paths: list[str] = []
    for directory in snapshot_dirs:
        base_path = Path(directory)
        if base_path.exists():
            local_paths.extend(sorted(str(path) for path in base_path.glob("*.json")))
    if local_paths:
        return local_paths

    try:
        response = requests.get(TREE_URL, timeout=15)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException:
        return []

    paths: list[str] = []
    for item in data.get("tree", []):
        path = item.get("path")
        if not path or not path.endswith(".json"):
            continue
        if any(path.startswith(f"{directory}/") for directory in snapshot_dirs):
            paths.append(path)
    return sorted(paths)


def _load_payload_from_path(path: str) -> dict[str, Any] | None:
    local_path = Path(path)
    if local_path.exists():
        try:
            return json.loads(local_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    raw_url = f"{RAW_BASE}/{path}"
    try:
        response = requests.get(raw_url, timeout=12)
        response.raise_for_status()
        return json.loads(response.text)
    except (requests.RequestException, json.JSONDecodeError):
        return None


def load_snapshot_records(max_files: int = 50) -> list[SnapshotRecord]:
    paths = list_snapshot_paths()
    if not paths:
        return []

    selected_paths = paths[-max_files:]
    records: list[SnapshotRecord] = []
    for path in selected_paths:
        payload = _load_payload_from_path(path)
        if not payload:
            continue
        if not _payload_has_signal(payload):
            continue
        department = _extract_department(payload)
        timestamp = _extract_timestamp(payload, path)
        normalized = snapshot_to_dict(
            normalize_snapshot(payload, department, timestamp.isoformat())
        )
        records.append(
            SnapshotRecord(
                source_path=path,
                raw_payload=payload,
                normalized=normalized,
                timestamp=timestamp,
                department_name=department,
            )
        )
    return sorted(records, key=lambda record: record.timestamp)


def build_totals_frame(records: list[SnapshotRecord]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for record in records:
        totals = record.normalized.get("totals", {})
        meta = record.normalized.get("meta", {})
        rows.append(
            {
                "timestamp": record.timestamp,
                "department": record.department_name,
                "department_code": meta.get("department_code"),
                "registered_voters": totals.get("registered_voters", 0),
                "total_votes": totals.get("total_votes", 0),
                "valid_votes": totals.get("valid_votes", 0),
                "null_votes": totals.get("null_votes", 0),
                "blank_votes": totals.get("blank_votes", 0),
                "source_path": record.source_path,
            }
        )
    return pd.DataFrame(rows)


def build_candidates_frame(records: list[SnapshotRecord]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for record in records:
        for candidate in record.normalized.get("candidates", []):
            rows.append(
                {
                    "timestamp": record.timestamp,
                    "department": record.department_name,
                    "candidate": candidate.get("name") or "Sin nombre",
                    "party": candidate.get("party") or "",
                    "votes": candidate.get("votes", 0),
                    "slot": candidate.get("slot"),
                    "source_path": record.source_path,
                }
            )
    return pd.DataFrame(rows)


def latest_record(records: list[SnapshotRecord]) -> SnapshotRecord | None:
    return max(records, key=lambda record: record.timestamp, default=None)
