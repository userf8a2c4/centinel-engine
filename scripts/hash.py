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
  - maybe_sign_hash_record
  - run_hash_snapshot
  - parse_args
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
import os
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Lazy import – custody pulls in cryptography which may not be installed
# in lightweight CI test environments. Imported on first use.
# from centinel.core.custody import sign_hash_record
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




def validate_json_file(path: Path) -> None:
    """Validate JSON syntax strictly before hashing.

    Valida sintaxis JSON estricta antes de hashear.
    """
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid_json_snapshot:{path}") from exc


def build_manifest(data_dir: Path = DATA_DIR, *, strict_json: bool = True) -> list[dict[str, Any]]:
    """Build manifest for current JSON snapshots.

    Construye manifiesto para snapshots JSON actuales.
    """
    manifest: list[dict[str, Any]] = []
    for candidate in iter_all_snapshots(data_root=data_dir):
        if not is_safe_snapshot_file(candidate, data_dir):
            LOGGER.warning("hash_skip_unsafe_candidate file=%s", candidate)
            continue
        try:
            if strict_json:
                validate_json_file(candidate)
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


def maybe_sign_hash_record(
    payload: dict[str, Any],
    *,
    sign_records: bool,
    key_path: Path | None,
    operator_id: str | None,
) -> dict[str, Any]:
    """Optionally sign hash records with Ed25519 operator signature.

    Firma opcional de registros de hash con firma Ed25519 del operador.
    """
    if not sign_records:
        return payload
    from centinel.core.custody import sign_hash_record  # lazy import
    return sign_hash_record(payload, key_path=key_path, operator_id=operator_id)


def write_snapshot_hash(
    manifest: list[dict[str, Any]],
    hash_dir: Path = HASH_DIR,
    *,
    pipeline_version: str | None = None,
    sign_records: bool = False,
    key_path: Path | None = None,
    operator_id: str | None = None,
) -> Path:
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
    if pipeline_version:
        payload["pipeline_version"] = pipeline_version
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    payload_hash = hashlib.sha256(body).hexdigest()
    previous = load_previous_chain_hash()
    chained_hash = hashlib.sha256(f"{previous}:{payload_hash}".encode("utf-8")).hexdigest()
    payload["hash"] = payload_hash
    payload["previous_hash"] = previous
    payload["chained_hash"] = chained_hash
    payload = maybe_sign_hash_record(
        payload,
        sign_records=sign_records,
        key_path=key_path,
        operator_id=operator_id,
    )

    target = hash_dir / f"snapshot_{timestamp}.sha256"
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def run_hash_snapshot(
    *,
    pipeline_version: str | None = None,
    sign_records: bool = False,
    key_path: Path | None = None,
    operator_id: str | None = None,
    strict_json: bool = True,
) -> int:
    """Generate hash snapshot from data directory.

    Genera snapshot de hash desde el directorio data.
    """
    configure_logging()
    if not DATA_DIR.exists():
        LOGGER.warning("hash_data_dir_missing path=%s", DATA_DIR)
        DATA_DIR.mkdir(parents=True, exist_ok=True)

    manifest = build_manifest(DATA_DIR, strict_json=strict_json)
    output = write_snapshot_hash(
        manifest,
        HASH_DIR,
        pipeline_version=pipeline_version,
        sign_records=sign_records,
        key_path=key_path,
        operator_id=operator_id,
    )
    LOGGER.info("hash_snapshot_written path=%s items=%s", output, len(manifest))
    return 0


def parse_args() -> argparse.Namespace:
    """Parse CLI args for hash snapshot generation.

    Parsea argumentos CLI para generación de hash snapshot.
    """
    parser = argparse.ArgumentParser(description="Generate chained hash snapshot records")
    parser.add_argument("--pipeline-version", default=os.getenv("CENTINEL_PIPELINE_VERSION"))
    parser.add_argument("--sign-records", action="store_true", help="Sign hash records with Ed25519")
    parser.add_argument("--key-path", default=os.getenv("CENTINEL_OPERATOR_KEY_PATH"))
    parser.add_argument("--operator-id", default=os.getenv("CENTINEL_OPERATOR_ID"))
    parser.add_argument("--no-strict-json", action="store_true", help="Disable strict JSON validation before hashing")
    return parser.parse_args()


def main() -> None:
    """CLI entrypoint.

    Punto de entrada CLI.
    """
    args = parse_args()
    raise SystemExit(
        run_hash_snapshot(
            pipeline_version=args.pipeline_version,
            sign_records=args.sign_records,
            key_path=Path(args.key_path) if args.key_path else None,
            operator_id=args.operator_id,
            strict_json=not args.no_strict_json,
        )
    )


if __name__ == "__main__":
    main()
