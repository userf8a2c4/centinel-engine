import csv
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from sentinel.core.hashchain import compute_hash
from sentinel.core.models import Snapshot
from sentinel.core.normalyze import snapshot_to_canonical_json


class LocalSnapshotStore:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._connection = sqlite3.connect(db_path)
        self._connection.row_factory = sqlite3.Row
        self._ensure_index_table()

    def close(self) -> None:
        self._connection.close()

    def store_snapshot(self, snapshot: Snapshot, previous_hash: Optional[str] = None) -> str:
        canonical_json = snapshot_to_canonical_json(snapshot)
        snapshot_hash = compute_hash(canonical_json, previous_hash=previous_hash)
        department_code = snapshot.meta.department_code
        table_name = self._department_table_name(department_code)
        self._ensure_department_table(table_name)

        candidates_json = json.dumps(
            [candidate.__dict__ for candidate in snapshot.candidates],
            sort_keys=True,
            separators=(",", ":"),
        )

        totals = snapshot.totals
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
                    candidates_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
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
                ),
            )
            self._connection.execute(
                """
                INSERT OR REPLACE INTO snapshot_index (
                    department_code,
                    timestamp_utc,
                    table_name,
                    hash,
                    previous_hash
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    department_code,
                    snapshot.meta.timestamp_utc,
                    table_name,
                    snapshot_hash,
                    previous_hash,
                ),
            )

        return snapshot_hash

    def get_index_entries(self, department_code: Optional[str] = None) -> List[Dict[str, Any]]:
        if department_code:
            rows = self._connection.execute(
                """
                SELECT department_code, timestamp_utc, table_name, hash, previous_hash
                FROM snapshot_index
                WHERE department_code = ?
                ORDER BY timestamp_utc
                """,
                (department_code,),
            ).fetchall()
        else:
            rows = self._connection.execute(
                """
                SELECT department_code, timestamp_utc, table_name, hash, previous_hash
                FROM snapshot_index
                ORDER BY department_code, timestamp_utc
                """
            ).fetchall()

        return [dict(row) for row in rows]

    def export_department_json(self, department_code: str, output_path: str) -> None:
        rows = self._fetch_department_rows(department_code)
        payload = [
            {
                "timestamp_utc": row["timestamp_utc"],
                "hash": row["hash"],
                "previous_hash": row["previous_hash"],
                "snapshot": json.loads(row["canonical_json"]),
            }
            for row in rows
        ]
        Path(output_path).write_text(json.dumps(payload, ensure_ascii=False, indent=2))

    def export_department_csv(self, department_code: str, output_path: str) -> None:
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
        ]
        with Path(output_path).open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow({key: row[key] for key in fieldnames})

    def _fetch_department_rows(self, department_code: str) -> Iterable[sqlite3.Row]:
        table_name = self._department_table_name(department_code)
        self._ensure_department_table(table_name)
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
                candidates_json
            FROM {table_name}
            ORDER BY timestamp_utc
            """
        ).fetchall()

    def _ensure_index_table(self) -> None:
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS snapshot_index (
                department_code TEXT NOT NULL,
                timestamp_utc TEXT NOT NULL,
                table_name TEXT NOT NULL,
                hash TEXT NOT NULL,
                previous_hash TEXT,
                PRIMARY KEY (department_code, timestamp_utc)
            )
            """
        )

    def _ensure_department_table(self, table_name: str) -> None:
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
                candidates_json TEXT NOT NULL
            )
            """
        )
        self._connection.execute(
            f"CREATE INDEX IF NOT EXISTS idx_{table_name}_timestamp ON {table_name}(timestamp_utc)"
        )

    @staticmethod
    def _department_table_name(department_code: str) -> str:
        sanitized = "".join(char for char in department_code if char.isalnum())
        return f"dept_{sanitized}_snapshots"
