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


def collect_snapshot_entries(snapshot_root: Path) -> List[SnapshotEntry]:
    """Collect snapshots ordered by timestamp. (Recolecta snapshots ordenados por timestamp.)"""
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
    entries = collect_snapshot_entries(snapshot_root)
    errors: List[str] = []
    previous_hash: Optional[str] = None
    last_valid_hash: Optional[str] = None
    verified_count = 0
    broken_at: Optional[int] = None
    broken_at_path: Optional[str] = None

    for idx, entry in enumerate(entries):
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

        previous_hash = computed_hash
        last_valid_hash = computed_hash
        verified_count += 1

    return {
        "valid": not errors,
        "count": len(entries),
        "verified_count": verified_count,
        "last_valid_hash": last_valid_hash,
        "last_hash": last_valid_hash,  # backward-compat alias
        "broken_at": broken_at,
        "broken_at_path": broken_at_path,
        "errors": errors,
    }
