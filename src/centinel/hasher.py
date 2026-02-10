"""Snapshot hashing helpers for Centinel. (Utilidades de hashing de snapshots para Centinel.)"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .download import chained_hash


@dataclass(frozen=True)
class SnapshotEntry:
    """Snapshot entry loaded from disk. (Entrada de snapshot cargada desde disco.)"""

    snapshot_dir: Path
    content: bytes
    metadata: Dict[str, Any]
    expected_hash: str
    timestamp: datetime
    previous_hash: Optional[str]


def ensure_snapshot_metadata(
    metadata: Dict[str, Any],
    *,
    timestamp_iso: str,
    source_url: Optional[str],
    software_version: str,
    previous_hash: Optional[str] = None,
) -> Dict[str, Any]:
    """Ensure required metadata fields are present. (Asegura campos requeridos en metadatos.)"""
    enriched = dict(metadata)
    resolved_source = enriched.get("source_url") or enriched.get("source") or source_url
    enriched.setdefault("source_url", resolved_source or "unknown")
    enriched.setdefault("timestamp_utc", timestamp_iso)
    enriched.setdefault("software_version", software_version)
    if previous_hash is not None:
        enriched.setdefault("previous_hash", previous_hash)
    return enriched


def canonical_metadata_bytes(metadata: Dict[str, Any]) -> bytes:
    """Serialize metadata canonically for hashing. (Serializa metadatos en forma canónica para hashing.)"""
    return json.dumps(metadata, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def compute_snapshot_hash(
    content: bytes,
    metadata: Dict[str, Any],
    previous_hash: Optional[str],
) -> str:
    """Compute the chained hash for a snapshot. (Calcula el hash encadenado de un snapshot.)"""
    timestamp_iso = metadata.get("timestamp_utc")
    if not timestamp_iso:
        raise ValueError("metadata_missing_timestamp_utc")
    return chained_hash(
        content,
        previous_hash,
        metadata=canonical_metadata_bytes(metadata),
        timestamp=timestamp_iso,
    )


def _parse_timestamp(timestamp_iso: str) -> datetime:
    """Parse ISO timestamp with UTC support. (Parsea timestamp ISO con soporte UTC.)"""
    normalized = timestamp_iso.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized).astimezone(timezone.utc)


def _load_snapshot_entry(snapshot_dir: Path) -> SnapshotEntry:
    """Load snapshot files from a directory. (Carga archivos de snapshot desde un directorio.)"""
    metadata_path = snapshot_dir / "snapshot.metadata.json"
    raw_path = snapshot_dir / "snapshot.raw"
    hash_path = snapshot_dir / "hash.txt"

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    timestamp_iso = metadata.get("timestamp_utc")
    if not timestamp_iso:
        raise ValueError(f"metadata_missing_timestamp_utc path={metadata_path}")

    expected_hash = hash_path.read_text(encoding="utf-8").strip()
    return SnapshotEntry(
        snapshot_dir=snapshot_dir,
        content=raw_path.read_bytes(),
        metadata=metadata,
        expected_hash=expected_hash,
        timestamp=_parse_timestamp(timestamp_iso),
        previous_hash=metadata.get("previous_hash"),
    )


def collect_snapshot_entries(snapshot_root: Path) -> List[SnapshotEntry]:
    """Collect snapshots ordered by timestamp. (Recolecta snapshots ordenados por timestamp.)"""
    entries = []
    for raw_path in snapshot_root.rglob("snapshot.raw"):
        entries.append(_load_snapshot_entry(raw_path.parent))
    return sorted(entries, key=lambda entry: entry.timestamp)


def verify_hashchain_from_snapshots(snapshot_root: Path) -> Dict[str, Any]:
    """Verify chained hashes from a snapshot directory. (Verifica hashes encadenados desde un directorio.)"""
    entries = collect_snapshot_entries(snapshot_root)
    errors: List[str] = []
    previous_hash: Optional[str] = None

    for entry in entries:
        expected_previous = entry.previous_hash
        if expected_previous and previous_hash and expected_previous != previous_hash:
            errors.append(
                f"previous_hash_mismatch path={entry.snapshot_dir} expected={expected_previous} actual={previous_hash}"
            )
        previous_to_use = expected_previous if expected_previous is not None else previous_hash
        try:
            computed_hash = compute_snapshot_hash(
                entry.content,
                entry.metadata,
                previous_to_use,
            )
        except ValueError as exc:
            errors.append(f"hash_compute_error path={entry.snapshot_dir} error={exc}")
            previous_hash = entry.expected_hash
            continue

        if computed_hash != entry.expected_hash:
            errors.append(
                f"hash_mismatch path={entry.snapshot_dir} expected={entry.expected_hash} computed={computed_hash}"
            )
        previous_hash = computed_hash

    return {
        "valid": not errors,
        "count": len(entries),
        "last_hash": previous_hash,
        "errors": errors,
    }
