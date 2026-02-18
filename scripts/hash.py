#!/usr/bin/env python
"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `scripts/hash.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - configure_logging
  - hash_file
  - is_safe_snapshot_file
  - load_previous_chain_hash
  - build_manifest
  - write_snapshot_hash
  - run_hash_snapshot
  - main
  - bloque_main

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `scripts/hash.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - configure_logging
  - hash_file
  - is_safe_snapshot_file
  - load_previous_chain_hash
  - build_manifest
  - write_snapshot_hash
  - run_hash_snapshot
  - main
  - bloque_main

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
"""

# Hash Module
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

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from centinel.paths import iter_all_hashes, iter_all_snapshots

LOGGER = logging.getLogger("centinel.hash")
DATA_DIR = Path("data")
HASH_DIR = Path("hashes")


def configure_logging() -> None:
    """Configure hash logger.

    Configura el logger de hash.
    """
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")


def hash_file(path: Path) -> str:
    """Hash a file with SHA-256.

    Hashea un archivo con SHA-256.
    """
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_safe_snapshot_file(path: Path, data_dir: Path) -> bool:
    """Validate candidate files for secure manifest generation.

    Valida archivos candidatos para generación segura del manifiesto.
    """
    if path.suffix.lower() != ".json":
        return False
    if path.is_symlink():
        return False
    resolved = path.resolve()
    base = data_dir.resolve()
    return str(resolved).startswith(str(base))


def load_previous_chain_hash() -> str:
    """Read the latest chained hash if any.

    Lee el último hash encadenado si existe.
    """
    all_hashes = iter_all_hashes(hash_root=HASH_DIR)
    if not all_hashes:
        return "0" * 64
    try:
        payload = json.loads(all_hashes[-1].read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return "0" * 64
    return payload.get("chained_hash", "0" * 64)


def build_manifest(data_dir: Path = DATA_DIR) -> list[dict[str, Any]]:
    """Build manifest for current JSON snapshots.

    Construye manifiesto para snapshots JSON actuales.
    """
    manifest: list[dict[str, Any]] = []
    for candidate in iter_all_snapshots(data_root=data_dir):
        if not is_safe_snapshot_file(candidate, data_dir):
            LOGGER.warning("hash_skip_unsafe_candidate file=%s", candidate)
            continue
        try:
            manifest.append(
                {
                    "file": str(candidate.relative_to(data_dir)),
                    "sha256": hash_file(candidate),
                    "mtime_utc": datetime.fromtimestamp(candidate.stat().st_mtime, tz=timezone.utc).isoformat(),
                }
            )
        except FileNotFoundError:
            LOGGER.warning("hash_file_missing file=%s", candidate)
    return manifest


def write_snapshot_hash(manifest: list[dict[str, Any]], hash_dir: Path = HASH_DIR) -> Path:
    """Persist a hash snapshot with timestamps and chained hash.

    Persiste un snapshot de hash con timestamps y hash encadenado.
    """
    hash_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
    payload = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "manifest_count": len(manifest),
        "manifest": manifest,
    }
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    payload_hash = hashlib.sha256(body).hexdigest()
    previous = load_previous_chain_hash()
    chained_hash = hashlib.sha256(f"{previous}:{payload_hash}".encode("utf-8")).hexdigest()
    payload["hash"] = payload_hash
    payload["previous_hash"] = previous
    payload["chained_hash"] = chained_hash

    target = hash_dir / f"snapshot_{timestamp}.sha256"
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def run_hash_snapshot() -> int:
    """Generate hash snapshot from data directory.

    Genera snapshot de hash desde el directorio data.
    """
    configure_logging()
    if not DATA_DIR.exists():
        LOGGER.warning("hash_data_dir_missing path=%s", DATA_DIR)
        DATA_DIR.mkdir(parents=True, exist_ok=True)

    manifest = build_manifest(DATA_DIR)
    output = write_snapshot_hash(manifest, HASH_DIR)
    LOGGER.info("hash_snapshot_written path=%s items=%s", output, len(manifest))
    return 0


def main() -> None:
    """CLI entrypoint.

    Punto de entrada CLI.
    """
    raise SystemExit(run_hash_snapshot())


if __name__ == "__main__":
    main()
