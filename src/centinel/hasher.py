"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `src/centinel/hasher.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - SnapshotEntry
  - ensure_snapshot_metadata
  - canonical_metadata_bytes
  - compute_snapshot_hash
  - _parse_timestamp
  - _load_snapshot_entry
  - collect_snapshot_entries
  - verify_hashchain_from_snapshots

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `src/centinel/hasher.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - SnapshotEntry
  - ensure_snapshot_metadata
  - canonical_metadata_bytes
  - compute_snapshot_hash
  - _parse_timestamp
  - _load_snapshot_entry
  - collect_snapshot_entries
  - verify_hashchain_from_snapshots

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
"""

# Hasher Module
# AUTO-DOC-INDEX
#
# ES: Índice rápido
#   1) Propósito del módulo
#   2) Componentes principales
#   3) Puntos de extensión
#
# EN: Quick index
#   1) Module purpose
#   2) Main components
#   3) Extension points
#
# Secciones / Sections:
#   - Configuración / Configuration
#   - Lógica principal / Core logic
#   - Integraciones / Integrations


from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .download import chained_hash
from .core.custody import verify_hash_record_signature

_SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")


def _validate_hash_format(value: str, field_name: str) -> None:
    """Validate that a string is a canonical SHA-256 hex digest.

    Rejects payloads with malformed previous_hash values (e.g. injected
    'MALFORMED' or truncated hashes), so a tampering attempt surfaces as a
    detectable integrity error rather than a downstream cryptographic crash.

    Valida que el string sea un digest SHA-256 hexadecimal canonico.
    Rechaza valores manipulados (p. ej. 'MALFORMED' inyectado o hashes
    truncados) para que un intento de manipulacion sea un error de
    integridad detectable y no un crash criptografico aguas abajo.
    """
    if not isinstance(value, str) or not _SHA256_HEX_RE.match(value):
        raise ValueError(f"invalid_hash_format field={field_name} value={value!r}")


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
    return json.dumps(metadata, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def compute_snapshot_hash(
    content: bytes,
    metadata: Dict[str, Any],
    previous_hash: Optional[str],
) -> str:
    """Compute the chained hash for a snapshot. (Calcula el hash encadenado de un snapshot.)"""
    timestamp_iso = metadata.get("timestamp_utc")
    if not timestamp_iso:
        raise ValueError("metadata_missing_timestamp_utc")
    if previous_hash is not None:
        _validate_hash_format(previous_hash, "previous_hash")
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
    _validate_hash_format(expected_hash, "expected_hash")

    previous_hash = metadata.get("previous_hash")
    if previous_hash is not None:
        _validate_hash_format(previous_hash, "metadata.previous_hash")

    return SnapshotEntry(
        snapshot_dir=snapshot_dir,
        content=raw_path.read_bytes(),
        metadata=metadata,
        expected_hash=expected_hash,
        timestamp=_parse_timestamp(timestamp_iso),
        previous_hash=previous_hash,
    )


@dataclass(frozen=True)
class SnapshotMeta:
    """Lightweight snapshot view WITHOUT the raw payload.

    A hostile count in Honduras can run for over a month. In election
    mode (5-min cadence) that is thousands of snapshots. Every public
    audit read (timeline / snapshots-by-day / proof / Merkle root) only
    needs metadata + hash + timestamp — never the payload bytes — yet
    loading full SnapshotEntry objects pulled every payload into RAM at
    once. Under sustained observer polling during the contested count
    that is exactly when the process would fall over.

    SnapshotMeta duck-types the attributes those read paths use
    (snapshot_dir, expected_hash, previous_hash, timestamp, metadata)
    so callers and serializers are unchanged — only `content` is absent,
    by design. Hashing logic and integrity guarantees are untouched.
    """

    snapshot_dir: Path
    metadata: Dict[str, Any]
    expected_hash: str
    timestamp: datetime
    previous_hash: Optional[str]


def _load_snapshot_meta(snapshot_dir: Path) -> SnapshotMeta:
    """Load only metadata + hash for a snapshot (no payload read)."""
    metadata_path = snapshot_dir / "snapshot.metadata.json"
    hash_path = snapshot_dir / "hash.txt"

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    timestamp_iso = metadata.get("timestamp_utc")
    if not timestamp_iso:
        raise ValueError(f"metadata_missing_timestamp_utc path={metadata_path}")

    expected_hash = hash_path.read_text(encoding="utf-8").strip()
    _validate_hash_format(expected_hash, "expected_hash")

    previous_hash = metadata.get("previous_hash")
    if previous_hash is not None:
        _validate_hash_format(previous_hash, "metadata.previous_hash")

    return SnapshotMeta(
        snapshot_dir=snapshot_dir,
        metadata=metadata,
        expected_hash=expected_hash,
        timestamp=_parse_timestamp(timestamp_iso),
        previous_hash=previous_hash,
    )


def _ordered_snapshot_dirs(snapshot_root: Path) -> List[Path]:
    """Return snapshot dirs ordered by capture timestamp (cheap scan).

    Reads only the small metadata file per snapshot to establish order,
    never the payload — so ordering a month of snapshots costs kilobytes
    of RAM, not the full evidence corpus.
    """
    metas: List[SnapshotMeta] = []
    for meta_path in snapshot_root.rglob("snapshot.metadata.json"):
        metas.append(_load_snapshot_meta(meta_path.parent))
    metas.sort(key=lambda m: m.timestamp)
    return [m.snapshot_dir for m in metas]


def collect_snapshot_metadata(snapshot_root: Path) -> List[SnapshotMeta]:
    """Collect snapshot metadata ordered by timestamp (no payloads).

    Use this for any read path that does not recompute hashes. Peak
    memory is proportional to metadata size, not to the total captured
    payload volume — the difference between surviving a month-long
    hostile count and falling over under observer load.
    """
    metas: List[SnapshotMeta] = []
    for meta_path in snapshot_root.rglob("snapshot.metadata.json"):
        metas.append(_load_snapshot_meta(meta_path.parent))
    return sorted(metas, key=lambda m: m.timestamp)


def collect_snapshot_entries(snapshot_root: Path) -> List[SnapshotEntry]:
    """Collect snapshots ordered by timestamp. (Recolecta snapshots ordenados por timestamp.)

    Loads full payloads; reserved for hash recomputation. Read-only
    endpoints must use collect_snapshot_metadata instead.
    """
    entries = []
    for raw_path in snapshot_root.rglob("snapshot.raw"):
        entries.append(_load_snapshot_entry(raw_path.parent))
    return sorted(entries, key=lambda entry: entry.timestamp)


def verify_hashchain_from_snapshots(snapshot_root: Path) -> Dict[str, Any]:
    """Verify chained hashes from a snapshot directory.

    Strict semantics: stops at the first integrity violation and reports the
    exact break point. A broken chain is mathematically unrecoverable, so
    continuing past a mismatch produces misleading output for third-party
    auditors.

    Returns:
        valid: bool — True only if the entire chain verified without errors.
        count: int — total snapshots inspected (including the broken one).
        verified_count: int — snapshots successfully verified before the break.
        last_valid_hash: str|None — the last good chained hash; useful as a
            recovery anchor (the chain was canonical up to this point).
        broken_at: int|None — zero-based index of the first failing snapshot,
            or None if the chain is fully valid.
        broken_at_path: str|None — filesystem path of the first failing snapshot.
        errors: list[str] — at most one error describing the break point.

    Semantica estricta: detiene la verificacion ante la primera violacion de
    integridad y reporta el punto exacto de ruptura. Una cadena rota es
    matematicamente irrecuperable, asi que continuar produce salidas engañosas
    para auditores externos.
    """
    # Stream verification: order payload-bearing dirs by timestamp using
    # only their small metadata files, then load ONE full payload at a
    # time inside the loop and let it be reclaimed. Peak memory is a
    # single snapshot, not the whole month's corpus — so a month-long
    # hostile count under observer polling does not exhaust RAM. The set
    # of verified entries and their order are identical to the previous
    # behavior (payload-present dirs, timestamp-ordered): pure endurance
    # optimization, integrity semantics unchanged.
    raw_dirs = [p.parent for p in snapshot_root.rglob("snapshot.raw")]
    ordered_dirs = sorted(raw_dirs, key=lambda d: _load_snapshot_meta(d).timestamp)
    total_count = len(ordered_dirs)
    errors: List[str] = []
    signature_failures: List[str] = []
    previous_hash: Optional[str] = None
    last_valid_hash: Optional[str] = None
    verified_count = 0
    broken_at: Optional[int] = None
    broken_at_path: Optional[str] = None

    # Forensic timestamp sanity (non-fatal, additive). The hash covers
    # content + metadata + previous_hash but NOT wall-clock ordering, so a
    # backdated or future-dated snapshot can still hash-verify. In a hostile
    # environment an attacker may also manipulate the system clock. These
    # anomalies never flip `valid` (a clock issue is not a chain break) but
    # they give auditors a signal that the timeline was tampered with.
    _FUTURE_TOLERANCE_SECONDS = 300
    now_utc = datetime.now(timezone.utc)
    timestamp_anomalies: List[Dict[str, Any]] = []
    previous_timestamp: Optional[datetime] = None

    for idx, snapshot_dir in enumerate(ordered_dirs):
        entry = _load_snapshot_entry(snapshot_dir)
        entry_ts = entry.timestamp
        if entry_ts.tzinfo is None:
            entry_ts = entry_ts.replace(tzinfo=timezone.utc)
        if (entry_ts - now_utc).total_seconds() > _FUTURE_TOLERANCE_SECONDS:
            timestamp_anomalies.append(
                {
                    "index": idx,
                    "snapshot": entry.snapshot_dir.name,
                    "kind": "future_timestamp",
                    "detail": f"timestamp {entry_ts.isoformat()} is ahead of "
                    f"verification time {now_utc.isoformat()}",
                }
            )
        if previous_timestamp is not None and entry_ts < previous_timestamp:
            timestamp_anomalies.append(
                {
                    "index": idx,
                    "snapshot": entry.snapshot_dir.name,
                    "kind": "non_monotonic_vs_chain_predecessor",
                    "detail": f"timestamp {entry_ts.isoformat()} precedes "
                    f"chain predecessor {previous_timestamp.isoformat()}",
                }
            )
        previous_timestamp = entry_ts

        expected_previous = entry.previous_hash

        if expected_previous and previous_hash and expected_previous != previous_hash:
            broken_at = idx
            broken_at_path = str(entry.snapshot_dir)
            errors.append(
                f"previous_hash_mismatch path={entry.snapshot_dir} "
                f"expected={expected_previous} actual={previous_hash}"
            )
            break

        try:
            computed_hash = compute_snapshot_hash(
                entry.content,
                entry.metadata,
                previous_hash,
            )
        except ValueError as exc:
            broken_at = idx
            broken_at_path = str(entry.snapshot_dir)
            errors.append(f"hash_compute_error path={entry.snapshot_dir} error={exc}")
            break

        if computed_hash != entry.expected_hash:
            broken_at = idx
            broken_at_path = str(entry.snapshot_dir)
            errors.append(
                f"hash_mismatch path={entry.snapshot_dir} "
                f"expected={entry.expected_hash} computed={computed_hash}"
            )
            break

        # Verify signature if present (non-fatal failure)
        metadata_file = entry.snapshot_dir / "snapshot.metadata.json"
        if metadata_file.exists():
            try:
                metadata_content = metadata_file.read_text(encoding="utf-8")
                metadata_obj = json.loads(metadata_content)
                if "operator_signature" in metadata_obj:
                    if not verify_hash_record_signature(metadata_obj):
                        signature_failures.append(
                            f"invalid_signature index={idx} path={entry.snapshot_dir.name}"
                        )
            except Exception:
                # Non-fatal: ignore failures reading/parsing signature
                pass

        previous_hash = computed_hash
        last_valid_hash = computed_hash
        verified_count += 1

    return {
        "valid": not errors,
        "count": total_count,
        "verified_count": verified_count,
        "last_valid_hash": last_valid_hash,
        "last_hash": last_valid_hash,  # backward-compat alias
        "broken_at": broken_at,
        "broken_at_path": broken_at_path,
        "errors": errors,
        "signature_failures": signature_failures,
        "timestamp_anomalies": timestamp_anomalies,
    }
