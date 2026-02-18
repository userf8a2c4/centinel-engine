# Storage Module
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

"""Almacenamiento histórico de snapshots y cadena de hashes.

Historical snapshot storage and hash chain.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from .download import chained_hash, write_atomic
from .hasher import canonical_metadata_bytes, ensure_snapshot_metadata
from . import __version__

logger = logging.getLogger(__name__)


def _snapshot_directory(base_path: Path, timestamp: datetime) -> Path:
    """Construye ruta de snapshot con jerarquía temporal.

    Build snapshot path with time hierarchy.
    """
    return (
        base_path
        / "snapshots"
        / timestamp.strftime("%Y")
        / timestamp.strftime("%m")
        / timestamp.strftime("%d")
        / timestamp.strftime("%H-%M-%S")
    )


def _append_hash(chain_path: Path, entry: Dict[str, Any]) -> None:
    """Agrega entrada a la cadena de hashes (append-only).

    Append entry to the hash chain (append-only).
    """
    chain_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        if chain_path.exists():
            data = json.loads(chain_path.read_text(encoding="utf-8"))
        else:
            data = []
    except json.JSONDecodeError as exc:
        logger.error("hashchain_corrupt_chain_file path=%s error=%s", chain_path, exc)
        raise
    data.append(entry)
    write_atomic(
        chain_path,
        json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"),
    )


def save_snapshot(
    content: bytes,
    metadata: Dict[str, Any],
    previous_hash: str,
    base_path: Path | None = None,
) -> str:
    """Guarda snapshot, metadata y hash encadenado.

    Save snapshot, metadata, and chained hash.
    """
    base = base_path or Path("data")
    timestamp = datetime.now(timezone.utc)
    timestamp_iso = timestamp.isoformat()
    snapshot_dir = _snapshot_directory(base, timestamp)
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    raw_path = snapshot_dir / "snapshot.raw"
    metadata_path = snapshot_dir / "snapshot.metadata.json"
    hash_path = snapshot_dir / "hash.txt"

    enriched_metadata = ensure_snapshot_metadata(
        metadata,
        timestamp_iso=timestamp_iso,
        source_url=metadata.get("source_url") or metadata.get("source"),
        software_version=__version__,
        previous_hash=previous_hash,
    )
    metadata_bytes = canonical_metadata_bytes(enriched_metadata)
    new_hash = chained_hash(
        content,
        previous_hash,
        metadata=metadata_bytes,
        timestamp=timestamp_iso,
    )

    write_atomic(raw_path, content)
    write_atomic(
        metadata_path,
        json.dumps(enriched_metadata, ensure_ascii=False, indent=2).encode("utf-8"),
    )
    write_atomic(hash_path, f"{new_hash}\n".encode("utf-8"))

    chain_entry = {
        "timestamp": timestamp_iso,
        "hash": new_hash,
        "previous_hash": previous_hash,
        "snapshot_path": str(snapshot_dir),
    }
    chain_path = base / "hashes" / "chain.json"
    _append_hash(chain_path, chain_entry)
    logger.info(
        "hashchain_snapshot_saved hash=%s previous_hash=%s path=%s",
        new_hash,
        previous_hash,
        snapshot_dir,
    )

    return new_hash
