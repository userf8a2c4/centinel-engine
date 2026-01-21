"""Pruebas de almacenamiento de snapshots en Centinel.

Tests for Centinel snapshot storage.
"""

from pathlib import Path

from centinel.storage import save_snapshot


def test_save_snapshot_creates_files(tmp_path):
    content = b"payload"
    metadata = {"source": "test"}
    previous_hash = "abc"

    new_hash = save_snapshot(content, metadata, previous_hash, base_path=tmp_path)

    snapshots = list((tmp_path / "snapshots").rglob("snapshot.raw"))
    assert snapshots, "snapshot.raw not created"

    snapshot_dir = snapshots[0].parent
    assert (snapshot_dir / "snapshot.metadata.json").exists()
    assert (snapshot_dir / "hash.txt").exists()

    chain_path = tmp_path / "hashes" / "chain.json"
    assert chain_path.exists()
    assert new_hash in chain_path.read_text(encoding="utf-8")
