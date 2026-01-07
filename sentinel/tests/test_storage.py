import csv
import json

from sentinel.core.hashchain import compute_hash
from sentinel.core.normalyze import normalize_snapshot, snapshot_to_canonical_json
from sentinel.core.storage import LocalSnapshotStore


def test_store_snapshot_creates_index(tmp_path):
    db_path = tmp_path / "snapshots.db"
    store = LocalSnapshotStore(str(db_path))

    raw = {
        "registered_voters": 1000,
        "total_votes": 900,
        "valid_votes": 880,
        "null_votes": 10,
        "blank_votes": 10,
        "candidates": {"1": 400, "2": 300, "3": 180},
    }
    snapshot = normalize_snapshot(raw, "Atlántida", "2025-12-03T17:00:00Z")
    snapshot_hash = store.store_snapshot(snapshot)

    canonical_json = snapshot_to_canonical_json(snapshot)
    expected_hash = compute_hash(canonical_json)

    entries = store.get_index_entries("01")
    store.close()

    assert snapshot_hash == expected_hash
    assert entries == [
        {
            "department_code": "01",
            "timestamp_utc": "2025-12-03T17:00:00Z",
            "table_name": "dept_01_snapshots",
            "hash": expected_hash,
            "previous_hash": None,
        }
    ]


def test_exports_for_external_review(tmp_path):
    db_path = tmp_path / "snapshots.db"
    store = LocalSnapshotStore(str(db_path))

    raw = {
        "registered_voters": 2000,
        "total_votes": 1800,
        "valid_votes": 1700,
        "null_votes": 50,
        "blank_votes": 50,
        "candidates": {"1": 800, "2": 600, "3": 300},
    }
    snapshot = normalize_snapshot(raw, "Comayagua", "2025-12-03T18:00:00Z")
    snapshot_hash = store.store_snapshot(snapshot)

    json_path = tmp_path / "exports.json"
    csv_path = tmp_path / "exports.csv"
    store.export_department_json("04", str(json_path))
    store.export_department_csv("04", str(csv_path))
    store.close()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload[0]["hash"] == snapshot_hash
    assert payload[0]["snapshot"]["meta"]["department_code"] == "04"

    with csv_path.open(newline="", encoding="utf-8") as csv_file:
        rows = list(csv.DictReader(csv_file))
    assert rows[0]["hash"] == snapshot_hash
    assert rows[0]["registered_voters"] == "2000"
