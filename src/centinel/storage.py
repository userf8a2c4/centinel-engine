from __future__ import annotations

"""Almacenamiento histórico de snapshots y cadena de hashes.

English: Historical snapshot storage and hash chain.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from .download import chained_hash, write_atomic


def _snapshot_directory(base_path: Path, timestamp: datetime) -> Path:
    """Construye ruta de snapshot con jerarquía temporal.

    English: Build snapshot path with time hierarchy.
    """
    return base_path / "snapshots" / timestamp.strftime("%Y") / timestamp.strftime("%m") / timestamp.strftime("%d") / timestamp.strftime("%H-%M-%S")


def _append_hash(chain_path: Path, entry: Dict[str, Any]) -> None:
    """Agrega entrada a la cadena de hashes (append-only).

    English: Append entry to the hash chain (append-only).
    """
    chain_path.parent.mkdir(parents=True, exist_ok=True)
    if chain_path.exists():
        data = json.loads(chain_path.read_text(encoding="utf-8"))
    else:
        data = []
    data.append(entry)
    write_atomic(chain_path, json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"))


def save_snapshot(content: bytes, metadata: Dict[str, Any], previous_hash: str, base_path: Path | None = None) -> str:
    """Guarda snapshot, metadata y hash encadenado.

    English: Save snapshot, metadata, and chained hash.
    """
    base = base_path or Path("data")
    timestamp = datetime.utcnow()
    snapshot_dir = _snapshot_directory(base, timestamp)
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    raw_path = snapshot_dir / "snapshot.raw"
    metadata_path = snapshot_dir / "snapshot.metadata.json"
    hash_path = snapshot_dir / "hash.txt"

    new_hash = chained_hash(content, previous_hash)

    write_atomic(raw_path, content)
    write_atomic(metadata_path, json.dumps(metadata, ensure_ascii=False, indent=2).encode("utf-8"))
    write_atomic(hash_path, f"{new_hash}\n".encode("utf-8"))

    chain_entry = {
        "timestamp": timestamp.isoformat() + "Z",
        "hash": new_hash,
        "previous_hash": previous_hash,
        "snapshot_path": str(snapshot_dir),
    }
    chain_path = base / "hashes" / "chain.json"
    _append_hash(chain_path, chain_entry)

    return new_hash
