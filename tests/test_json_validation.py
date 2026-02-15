"""Pruebas de manejo defensivo de JSON malformado.

Tests for defensive handling of malformed JSON across the system.
"""

import json
import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

from sentinel.api.main import (
    fetch_latest_snapshot,
    fetch_snapshot_by_hash,
    load_alerts_payload,
    ALERTS_JSON,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_test_db(tmp_path: Path, *, canonical_json: str = '{"valid": true}'):
    """Create a minimal SQLite database with one snapshot for testing."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE snapshot_index (
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
    """)
    conn.execute("""
        CREATE TABLE dept_01_snapshots (
            timestamp_utc TEXT PRIMARY KEY,
            hash TEXT NOT NULL,
            previous_hash TEXT,
            canonical_json TEXT NOT NULL,
            registered_voters INTEGER NOT NULL DEFAULT 0,
            total_votes INTEGER NOT NULL DEFAULT 0,
            valid_votes INTEGER NOT NULL DEFAULT 0,
            null_votes INTEGER NOT NULL DEFAULT 0,
            blank_votes INTEGER NOT NULL DEFAULT 0,
            candidates_json TEXT NOT NULL DEFAULT '[]',
            tx_hash TEXT,
            ipfs_cid TEXT,
            ipfs_tx_hash TEXT
        )
    """)
    conn.execute(
        """INSERT INTO snapshot_index
           (department_code, timestamp_utc, table_name, hash, previous_hash, tx_hash)
           VALUES (?, ?, ?, ?, ?, ?)""",
        ("01", "2025-12-03T17:00:00Z", "dept_01_snapshots", "abc123", None, None),
    )
    conn.execute(
        """INSERT INTO dept_01_snapshots
           (timestamp_utc, hash, previous_hash, canonical_json)
           VALUES (?, ?, ?, ?)""",
        ("2025-12-03T17:00:00Z", "abc123", None, canonical_json),
    )
    conn.commit()
    return conn


# ---------------------------------------------------------------------------
# fetch_latest_snapshot: corrupted canonical_json
# ---------------------------------------------------------------------------

class TestFetchLatestSnapshotCorruptedJson:
    """Validate fetch_latest_snapshot handles corrupted canonical_json."""

    def test_returns_none_snapshot_on_invalid_json(self, tmp_path):
        conn = _create_test_db(tmp_path, canonical_json="{INVALID JSON!!!")
        result = fetch_latest_snapshot(conn)
        conn.close()

        assert result is not None, "Should still return metadata even with bad JSON"
        assert result["snapshot"] is None
        assert result["snapshot_id"] == "abc123"

    def test_returns_parsed_snapshot_on_valid_json(self, tmp_path):
        conn = _create_test_db(tmp_path, canonical_json='{"cargo": "presidencial"}')
        result = fetch_latest_snapshot(conn)
        conn.close()

        assert result["snapshot"] == {"cargo": "presidencial"}


# ---------------------------------------------------------------------------
# fetch_snapshot_by_hash: corrupted canonical_json
# ---------------------------------------------------------------------------

class TestFetchSnapshotByHashCorruptedJson:
    """Validate fetch_snapshot_by_hash handles corrupted canonical_json."""

    def test_returns_none_snapshot_on_invalid_json(self, tmp_path):
        conn = _create_test_db(tmp_path, canonical_json="NOT-JSON")
        result = fetch_snapshot_by_hash(conn, "abc123")
        conn.close()

        assert result is not None
        assert result["snapshot"] is None
        assert result["snapshot_id"] == "abc123"

    def test_returns_parsed_snapshot_on_valid_json(self, tmp_path):
        conn = _create_test_db(tmp_path, canonical_json='{"ok": true}')
        result = fetch_snapshot_by_hash(conn, "abc123")
        conn.close()

        assert result["snapshot"] == {"ok": True}

    def test_returns_none_for_missing_hash(self, tmp_path):
        conn = _create_test_db(tmp_path)
        result = fetch_snapshot_by_hash(conn, "nonexistent")
        conn.close()

        assert result is None


# ---------------------------------------------------------------------------
# load_alerts_payload: corrupted alerts.json
# ---------------------------------------------------------------------------

class TestLoadAlertsCorruptedJson:
    """Validate load_alerts_payload handles corrupted files with logging."""

    def test_corrupted_alerts_returns_empty_and_logs(self, tmp_path):
        alerts_file = tmp_path / "alerts.json"
        alerts_file.write_text("{BROKEN", encoding="utf-8")

        with patch("sentinel.api.main.ALERTS_JSON", alerts_file), \
             patch("sentinel.api.main.ALERTS_LOG", tmp_path / "nonexistent.log"), \
             patch("sentinel.api.main.logger") as mock_logger:
            result = load_alerts_payload()

        assert result == []
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args[0]
        assert "corrupted_alerts_json" in call_args[0]

    def test_valid_alerts_returns_list(self, tmp_path):
        alerts_file = tmp_path / "alerts.json"
        alerts_file.write_text('[{"alert": "test"}]', encoding="utf-8")

        with patch("sentinel.api.main.ALERTS_JSON", alerts_file), \
             patch("sentinel.api.main.ALERTS_LOG", tmp_path / "nonexistent.log"):
            result = load_alerts_payload()

        assert result == [{"alert": "test"}]


# ---------------------------------------------------------------------------
# storage: canonical_json validation before DB insert
# ---------------------------------------------------------------------------

class TestStorageCanonicalJsonValidation:
    """Validate that store_snapshot rejects invalid canonical JSON."""

    def test_canonical_json_is_always_valid(self):
        """Verify snapshot_to_canonical_json always produces valid JSON."""
        from sentinel.core.normalize import normalize_snapshot, snapshot_to_canonical_json

        raw = {
            "cargo": "presidencial",
            "departamento": "Cortés",
            "registered_voters": 500,
            "total_votes": 400,
            "valid_votes": 390,
            "null_votes": 5,
            "blank_votes": 5,
            "candidates": {"1": 200, "2": 190},
        }
        snapshot = normalize_snapshot(raw, "Cortés", "2025-12-03T19:00:00Z")
        assert snapshot is not None

        canonical = snapshot_to_canonical_json(snapshot)
        parsed = json.loads(canonical)
        assert isinstance(parsed, dict)
        assert "meta" in parsed
        assert "totals" in parsed
        assert "candidates" in parsed
