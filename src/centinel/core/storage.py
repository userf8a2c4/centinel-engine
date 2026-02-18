"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `src/centinel/core/storage.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - LocalSnapshotStore

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `src/centinel/core/storage.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - LocalSnapshotStore

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
"""

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



import csv
import json
import logging
import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from centinel.core.blockchain import publish_cid_to_chain, publish_hash_to_chain
from centinel.core.hashchain import compute_hash
from centinel.core.ipfs import upload_snapshot_to_ipfs
from centinel.core.models import Snapshot
from centinel.core.normalize import snapshot_to_canonical_json

logger = logging.getLogger(__name__)


class LocalSnapshotStore:
    """Gestiona almacenamiento SQLite de snapshots locales.

    English:
        Manages SQLite storage for local snapshots.
    """

    def __init__(self, db_path: str) -> None:
        """Inicializa la conexión SQLite y la tabla índice.

        Args:
            db_path (str): Ruta del archivo SQLite.

        English:
            Initializes the SQLite connection and index table.

        Args:
            db_path (str): Path to the SQLite file.
        """
        self.db_path = db_path
        self._connection = sqlite3.connect(db_path)
        self._connection.row_factory = sqlite3.Row
        self._ensure_index_table()

    def close(self) -> None:
        """Cierra la conexión a la base de datos.

        English:
            Closes the database connection.
        """
        self._connection.close()

    def store_snapshot(self, snapshot: Snapshot, previous_hash: Optional[str] = None) -> str:
        """Guarda un snapshot y actualiza su hash en la cadena.

        Args:
            snapshot (Snapshot): Snapshot canónico a persistir.
            previous_hash (Optional[str]): Hash anterior para encadenar.

        Returns:
            str: Hash SHA-256 del snapshot almacenado.

        English:
            Stores a snapshot and updates the hash chain.

        Args:
            snapshot (Snapshot): Canonical snapshot to persist.
            previous_hash (Optional[str]): Previous hash for chaining.

        Returns:
            str: SHA-256 hash of the stored snapshot.
        """
        canonical_json = snapshot_to_canonical_json(snapshot)
        try:
            json.loads(canonical_json)
        except (json.JSONDecodeError, TypeError) as exc:
            raise ValueError(f"canonical_json generation produced invalid JSON: {exc}") from exc
        snapshot_hash = compute_hash(canonical_json, previous_hash=previous_hash)
        tx_hash = None
        ipfs_cid = None
        ipfs_tx_hash = None
        try:
            tx_hash = publish_hash_to_chain(snapshot_hash) or None
        except Exception as exc:  # noqa: BLE001
            logger.warning("blockchain_publish_failed error=%s", exc)
        try:
            ipfs_cid = upload_snapshot_to_ipfs(json.loads(canonical_json)) or None
        except Exception as exc:  # noqa: BLE001
            logger.warning("ipfs_upload_failed error=%s", exc)
        if ipfs_cid:
            try:
                ipfs_tx_hash = publish_cid_to_chain(ipfs_cid) or None
            except Exception as exc:  # noqa: BLE001
                logger.warning("ipfs_blockchain_publish_failed error=%s", exc)
        department_code = snapshot.meta.department_code
        table_name = self._department_table_name(department_code)
        self._ensure_department_table(table_name)

        candidates_json = json.dumps(
            [candidate.__dict__ for candidate in snapshot.candidates],
            sort_keys=True,
            separators=(",", ":"),
        )

        totals = snapshot.totals
        self._assert_safe_identifier(table_name, "table_name")
        with self._connection:
            self._connection.execute(
                f"""
                INSERT OR REPLACE INTO {table_name} (
                    timestamp_utc,
                    hash,
                    previous_hash,
                    canonical_json,
                    registered_voters,
                    total_votes,
                    valid_votes,
                    null_votes,
                    blank_votes,
                    candidates_json,
                    tx_hash,
                    ipfs_cid,
                    ipfs_tx_hash
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,  # nosec B608 - validated by _assert_safe_identifier.
                (
                    snapshot.meta.timestamp_utc,
                    snapshot_hash,
                    previous_hash,
                    canonical_json,
                    totals.registered_voters,
                    totals.total_votes,
                    totals.valid_votes,
                    totals.null_votes,
                    totals.blank_votes,
                    candidates_json,
                    tx_hash,
                    ipfs_cid,
                    ipfs_tx_hash,
                ),
            )
            self._connection.execute(
                """
                INSERT OR REPLACE INTO snapshot_index (
                    department_code,
                    timestamp_utc,
                    table_name,
                    hash,
                    previous_hash,
                    tx_hash,
                    ipfs_cid,
                    ipfs_tx_hash
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    department_code,
                    snapshot.meta.timestamp_utc,
                    table_name,
                    snapshot_hash,
                    previous_hash,
                    tx_hash,
                    ipfs_cid,
                    ipfs_tx_hash,
                ),
            )

        return snapshot_hash

    def get_index_entries(self, department_code: Optional[str] = None) -> List[Dict[str, Any]]:
        """Devuelve el índice de snapshots, filtrado por departamento si aplica.

        Args:
            department_code (Optional[str]): Código de departamento a filtrar.

        Returns:
            List[Dict[str, Any]]: Entradas del índice con hashes y metadatos.

        English:
            Returns snapshot index entries, optionally filtered by department.

        Args:
            department_code (Optional[str]): Department code to filter by.

        Returns:
            List[Dict[str, Any]]: Index entries with hashes and metadata.
        """
        if department_code:
            rows = self._connection.execute(
                """
                SELECT department_code, timestamp_utc, table_name, hash, previous_hash, tx_hash, ipfs_cid, ipfs_tx_hash
                FROM snapshot_index
                WHERE department_code = ?
                ORDER BY timestamp_utc
                """,
                (department_code,),
            ).fetchall()
        else:
            rows = self._connection.execute(
                """
                SELECT department_code, timestamp_utc, table_name, hash, previous_hash, tx_hash, ipfs_cid, ipfs_tx_hash
                FROM snapshot_index
                ORDER BY department_code, timestamp_utc
                """
            ).fetchall()

        return [dict(row) for row in rows]

    def export_department_json(self, department_code: str, output_path: str) -> None:
        """Exporta snapshots de un departamento a un JSON legible.

        Args:
            department_code (str): Código de departamento.
            output_path (str): Ruta de salida para el JSON.

        English:
            Exports department snapshots to a readable JSON file.

        Args:
            department_code (str): Department code.
            output_path (str): Output JSON path.
        """
        rows = self._fetch_department_rows(department_code)
        payload = []
        for row in rows:
            try:
                snapshot_data = json.loads(row["canonical_json"])
            except (json.JSONDecodeError, TypeError) as exc:
                logger.error("corrupted_canonical_json_export hash=%s error=%s", row["hash"], exc)
                snapshot_data = None
            payload.append(
                {
                    "timestamp_utc": row["timestamp_utc"],
                    "hash": row["hash"],
                    "previous_hash": row["previous_hash"],
                    "snapshot": snapshot_data,
                    "tx_hash": row["tx_hash"],
                    "ipfs_cid": row["ipfs_cid"],
                    "ipfs_tx_hash": row["ipfs_tx_hash"],
                }
            )
        Path(output_path).write_text(json.dumps(payload, ensure_ascii=False, indent=2))

    def export_department_csv(self, department_code: str, output_path: str) -> None:
        """Exporta snapshots de un departamento a un CSV.

        Args:
            department_code (str): Código de departamento.
            output_path (str): Ruta de salida para el CSV.

        English:
            Exports department snapshots to a CSV file.

        Args:
            department_code (str): Department code.
            output_path (str): Output CSV path.
        """
        rows = self._fetch_department_rows(department_code)
        fieldnames = [
            "timestamp_utc",
            "hash",
            "previous_hash",
            "registered_voters",
            "total_votes",
            "valid_votes",
            "null_votes",
            "blank_votes",
            "candidates_json",
            "canonical_json",
            "tx_hash",
            "ipfs_cid",
            "ipfs_tx_hash",
        ]
        with Path(output_path).open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow({key: row[key] for key in fieldnames})

    def _fetch_department_rows(self, department_code: str) -> Iterable[sqlite3.Row]:
        """Obtiene filas de snapshots por departamento ordenadas por timestamp.

        Asegura que la tabla del departamento exista antes de consultar.

        English:
            Fetch snapshot rows for a department ordered by timestamp.

            Ensures the department table exists before querying.
        """
        table_name = self._department_table_name(department_code)
        self._ensure_department_table(table_name)
        self._assert_safe_identifier(table_name, "table_name")
        return self._connection.execute(
            f"""
            SELECT
                timestamp_utc,
                hash,
                previous_hash,
                canonical_json,
                registered_voters,
                total_votes,
                valid_votes,
                null_votes,
                blank_votes,
                candidates_json,
                tx_hash,
                ipfs_cid,
                ipfs_tx_hash
            FROM {table_name}
            ORDER BY timestamp_utc
            """,  # nosec B608 - validated by _assert_safe_identifier.
        ).fetchall()

    def _ensure_index_table(self) -> None:
        """Garantiza la existencia de la tabla índice y columnas opcionales.

        English:
            Ensure the index table and optional columns exist.
        """
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS snapshot_index (
                department_code TEXT NOT NULL,
                timestamp_utc TEXT NOT NULL,
                table_name TEXT NOT NULL,
                hash TEXT NOT NULL,
                previous_hash TEXT,
                tx_hash TEXT,
                ipfs_cid TEXT,
                ipfs_tx_hash TEXT,
                PRIMARY KEY (department_code, timestamp_utc)
            )
            """
        )
        self._ensure_column("snapshot_index", "tx_hash", "TEXT")
        self._ensure_column("snapshot_index", "ipfs_cid", "TEXT")
        self._ensure_column("snapshot_index", "ipfs_tx_hash", "TEXT")

    def _ensure_department_table(self, table_name: str) -> None:
        """Crea la tabla de snapshots de un departamento si falta.

        También asegura índices y columnas adicionales (tx/IPFS).

        English:
            Create the department snapshot table if missing.

            Also ensures indexes and extra columns (tx/IPFS).
        """
        self._assert_safe_identifier(table_name, "table_name")
        self._connection.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                timestamp_utc TEXT PRIMARY KEY,
                hash TEXT NOT NULL,
                previous_hash TEXT,
                canonical_json TEXT NOT NULL,
                registered_voters INTEGER NOT NULL,
                total_votes INTEGER NOT NULL,
                valid_votes INTEGER NOT NULL,
                null_votes INTEGER NOT NULL,
                blank_votes INTEGER NOT NULL,
                candidates_json TEXT NOT NULL,
                tx_hash TEXT,
                ipfs_cid TEXT,
                ipfs_tx_hash TEXT
            )
            """,  # nosec B608 - validated by _assert_safe_identifier.
        )
        idx_name = f"idx_{table_name}_timestamp"
        self._assert_safe_identifier(idx_name, "index_name")
        self._connection.execute(
            f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table_name}(timestamp_utc)"  # nosec B608 - validated by _assert_safe_identifier.
        )
        self._ensure_column(table_name, "tx_hash", "TEXT")
        self._ensure_column(table_name, "ipfs_cid", "TEXT")
        self._ensure_column(table_name, "ipfs_tx_hash", "TEXT")

    _TABLE_NAME_RE = re.compile(r"^[A-Za-z0-9_]+$")

    @classmethod
    def _department_table_name(cls, department_code: str) -> str:
        """Normaliza el código de departamento y genera el nombre de tabla.

        Raises ``ValueError`` if the sanitized code is empty or contains
        characters outside ``[A-Za-z0-9_]``.

        English:
            Normalize the department code and build the table name.
        """
        sanitized = "".join(char for char in department_code if char.isalnum())
        if not sanitized:
            raise ValueError(f"Invalid department_code produces empty table name: {department_code!r}")
        table_name = f"dept_{sanitized}_snapshots"
        if not cls._TABLE_NAME_RE.match(table_name):
            raise ValueError(f"Unsafe table name derived: {table_name!r}")
        return table_name

    _IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

    @classmethod
    def _assert_safe_identifier(cls, value: str, label: str = "identifier") -> str:
        """Validate that *value* is a safe SQL identifier (alphanumeric + underscore)."""
        if not cls._IDENTIFIER_RE.match(value):
            raise ValueError(f"Unsafe SQL {label}: {value!r}")
        return value

    def _ensure_column(self, table_name: str, column_name: str, column_type: str) -> None:
        """Agrega una columna si no existe en la tabla indicada.

        English:
            Add a column if it does not exist in the specified table.
        """
        self._assert_safe_identifier(table_name, "table_name")
        self._assert_safe_identifier(column_name, "column_name")
        self._assert_safe_identifier(column_type, "column_type")
        cursor = self._connection.execute(
            f"PRAGMA table_info({table_name})"  # nosec B608 - validated by _assert_safe_identifier.
        )
        columns = {row[1] for row in cursor.fetchall()}
        if column_name in columns:
            return
        self._connection.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"  # nosec B608 - validated by _assert_safe_identifier.
        )
