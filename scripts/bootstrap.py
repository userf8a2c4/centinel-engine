#!/usr/bin/env python3
"""Bootstrap initial configuration files for Centinel.

This helper copies template files into command_center if they do not exist and
validates minimal configuration requirements.
"""

import argparse
import hashlib
import json
import logging
import shutil
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from centinel.paths import iter_all_hashes, SNAPSHOTS_SUBDIR
from scripts.logging_utils import configure_logging, log_event
from centinel.core.hashchain import compute_hash

logger = configure_logging("centinel.bootstrap", log_file="logs/centinel.log")

COMMAND_CENTER_DIR = Path("command_center")
CONFIG_TEMPLATE_PATH = COMMAND_CENTER_DIR / "config.yaml.example"
CONFIG_PATH = COMMAND_CENTER_DIR / "config.yaml"
ENV_TEMPLATE_PATH = COMMAND_CENTER_DIR / ".env.example"
ENV_PATH = COMMAND_CENTER_DIR / ".env"

REQUIRED_CONFIG_KEYS = ("base_url", "endpoints")


@dataclass
class HashEntry:
    """Español:
        Representa una entrada de hash leída desde hashes/.

    English:
        Represents a hash entry loaded from hashes/.

    Attributes:
        name: Nombre base del snapshot.
        stored_hash: Hash encadenado almacenado.
        stored_current_hash: Hash del snapshot si viene en JSON.
    """

    name: str
    stored_hash: str
    stored_current_hash: str | None = None
    source_dir: str | None = None


def _copy_if_missing(source_path: Path, destination_path: Path) -> bool:
    """/** Copia un template si falta. / Copy a template if missing. **/"""
    if destination_path.exists():
        log_event(logger, logging.INFO, "bootstrap_file_exists", path=str(destination_path))
        return False
    if not source_path.exists():
        raise FileNotFoundError(f"Missing template: {source_path}")
    shutil.copyfile(source_path, destination_path)
    log_event(logger, logging.INFO, "bootstrap_file_created", path=str(destination_path))
    return True


def _load_config(config_path: Path) -> dict[str, Any]:
    """/** Carga YAML de configuración. / Load YAML configuration. **/"""
    if not config_path.exists():
        log_event(logger, logging.WARNING, "bootstrap_config_missing", path=str(config_path))
        return {}
    return yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}


def _validate_config(config: dict[str, Any]) -> list[str]:
    """Español:
        Valida claves mínimas en la configuración.

    English:
        Validate minimal keys in the configuration.

    Args:
        config: Diccionario de configuración.

    Returns:
        Lista de claves faltantes.
    """
    missing_keys = [key for key in REQUIRED_CONFIG_KEYS if key not in config]
    return missing_keys


def _load_hash_entries(hashes_dir: Path) -> list[HashEntry]:
    """Español:
        Carga entradas de hashes desde subdirectorios por fuente.

    English:
        Load hash entries from per-source subdirectories.

    Args:
        hashes_dir: Ruta al directorio raíz de hashes.

    Returns:
        Lista de entradas de hash encontradas.
    """
    entries: list[HashEntry] = []
    for hash_file in iter_all_hashes(hash_root=hashes_dir):
        raw = hash_file.read_text(encoding="utf-8").strip()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = None

        source_dir = hash_file.parent.name

        if isinstance(payload, dict):
            chained = payload.get("chained_hash") or payload.get("hash")
            current = payload.get("hash") if payload.get("chained_hash") else None
            if chained:
                entries.append(
                    HashEntry(
                        name=hash_file.stem,
                        stored_hash=str(chained),
                        stored_current_hash=str(current) if current else None,
                        source_dir=source_dir,
                    )
                )
            continue

        if raw:
            entries.append(HashEntry(name=hash_file.stem, stored_hash=raw, source_dir=source_dir))
    return entries


def _canonical_json(snapshot_path: Path) -> str:
    """Español:
        Obtiene JSON canónico desde un snapshot.

    English:
        Get canonical JSON from a snapshot.

    Args:
        snapshot_path: Ruta del snapshot.

    Returns:
        Cadena JSON canónica o texto original si no es JSON válido.
    """
    text = snapshot_path.read_text(encoding="utf-8")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return text
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _validate_hash_dir(hashes_dir: Path, data_dir: Path) -> tuple[bool, str]:
    """Español:
        Valida cadena de hashes usando hashes/ y snapshots en data/.

    English:
        Validate hash chain using hashes/ and snapshots in data/.

    Args:
        hashes_dir: Ruta a hashes/.
        data_dir: Ruta a data/.

    Returns:
        Tuple (ok, message) con estado y detalle.
    """
    entries = _load_hash_entries(hashes_dir)
    if not entries:
        return True, "sin_hashes"

    previous_hash: str | None = None
    for entry in entries:
        source_dir = entry.source_dir or ""
        snapshot_path = data_dir / SNAPSHOTS_SUBDIR / source_dir / f"{entry.name}.json"
        if not snapshot_path.exists():
            return False, f"snapshot_missing:{entry.name}"
        canonical_json = _canonical_json(snapshot_path)
        current_hash = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
        chained_hash = compute_hash(canonical_json, previous_hash)

        if entry.stored_current_hash and entry.stored_current_hash != current_hash:
            return False, f"hash_mismatch:{entry.name}"

        if entry.stored_hash != chained_hash:
            return False, f"hash_chain_mismatch:{entry.name}"

        previous_hash = chained_hash

    return True, "hash_chain_ok"


def _validate_sqlite(sqlite_path: Path) -> tuple[bool, str]:
    """Español:
        Valida cadena de hashes usando la base SQLite.

    English:
        Validate hash chain using the SQLite database.

    Args:
        sqlite_path: Ruta al archivo SQLite.

    Returns:
        Tuple (ok, message) con estado y detalle.
    """
    if not sqlite_path.exists():
        return True, "sqlite_missing"

    connection = sqlite3.connect(sqlite_path)
    connection.row_factory = sqlite3.Row

    previous_by_department: dict[str, str | None] = {}
    latest_hash: str | None = None

    try:
        rows = connection.execute("""
            SELECT department_code, timestamp_utc, table_name, hash, previous_hash
            FROM snapshot_index
            ORDER BY department_code, timestamp_utc
            """).fetchall()

        for row in rows:
            department_code = row["department_code"]
            snapshot_hash = row["hash"]
            previous_hash = row["previous_hash"]
            table_name = row["table_name"]

            expected_previous = previous_by_department.get(department_code)
            if expected_previous != previous_hash:
                return False, f"sqlite_prev_mismatch:{snapshot_hash}"

            snapshot_row = connection.execute(
                f"SELECT canonical_json FROM {table_name} WHERE hash = ? LIMIT 1",  # nosec B608
                (snapshot_hash,),
            ).fetchone()
            if not snapshot_row:
                return False, f"sqlite_snapshot_missing:{snapshot_hash}"

            computed_hash = compute_hash(snapshot_row["canonical_json"], previous_hash)
            if computed_hash != snapshot_hash:
                return False, f"sqlite_hash_mismatch:{snapshot_hash}"

            previous_by_department[department_code] = snapshot_hash
            latest_hash = snapshot_hash
    finally:
        connection.close()

    if latest_hash is None:
        return True, "sqlite_empty"

    return True, "sqlite_hash_chain_ok"


def validate_hash_chain(
    hashes_dir: Path,
    data_dir: Path,
    sqlite_path: Path | None,
) -> tuple[bool, str]:
    """Español:
        Valida la cadena de hashes al iniciar el sistema.

    English:
        Validate the hash chain at system startup.

    Args:
        hashes_dir: Ruta al directorio hashes/.
        data_dir: Ruta al directorio data/.
        sqlite_path: Ruta a SQLite si existe.

    Returns:
        Tuple (ok, message) con estado y detalle.
    """
    if hashes_dir.exists():
        ok, message = _validate_hash_dir(hashes_dir, data_dir)
        if ok and message == "sin_hashes":
            if sqlite_path:
                return _validate_sqlite(sqlite_path)
            return True, "sin_hashes"
        return ok, message

    if sqlite_path:
        return _validate_sqlite(sqlite_path)

    return True, "sin_hashes"


def bootstrap_config(force: bool = False) -> int:
    """Español:
        Inicializa configuración base y valida cadena de hashes.

    English:
        Initialize base configuration and validate the hash chain.

    Args:
        force: Forzar sobreescritura de archivos existentes.

    Returns:
        Código de salida del bootstrap.
    """
    COMMAND_CENTER_DIR.mkdir(parents=True, exist_ok=True)

    created_any = False
    if force and CONFIG_PATH.exists():
        CONFIG_PATH.unlink()
    if force and ENV_PATH.exists():
        ENV_PATH.unlink()

    created_any |= _copy_if_missing(CONFIG_TEMPLATE_PATH, CONFIG_PATH)
    created_any |= _copy_if_missing(ENV_TEMPLATE_PATH, ENV_PATH)

    config = _load_config(CONFIG_PATH)
    missing_keys = _validate_config(config)
    if missing_keys:
        log_event(logger, logging.WARNING, "bootstrap_missing_keys", missing_keys=missing_keys)
        return 2

    sqlite_path_value = (
        config.get("rules", {}).get("irreversibility", {}).get("sqlite_path", "reports/irreversibility_state.db")
        if isinstance(config, dict)
        else "reports/irreversibility_state.db"
    )
    sqlite_path = Path(sqlite_path_value) if sqlite_path_value else None
    ok, message = validate_hash_chain(
        hashes_dir=Path("hashes"),
        data_dir=Path("data"),
        sqlite_path=sqlite_path,
    )
    if not ok:
        log_event(logger, logging.CRITICAL, "hash_chain_invalid", detail=message)
        raise RuntimeError(f"Hash chain inválida: {message}")
    log_event(logger, logging.INFO, "hash_chain_validated", detail=message)

    if created_any:
        log_event(logger, logging.INFO, "bootstrap_complete", created=True)
    else:
        log_event(logger, logging.INFO, "bootstrap_complete", created=False)
    return 0


def main() -> int:
    """/** Entrada principal del script. / Script entry point. **/"""
    parser = argparse.ArgumentParser(description="Bootstrap Centinel configuration")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing config/env files",
    )
    args = parser.parse_args()
    return bootstrap_config(force=args.force)


if __name__ == "__main__":
    raise SystemExit(main())
