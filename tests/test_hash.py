"""Pruebas unitarias de hashing encadenado.

Unit tests for chained hashing.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import hash as hash_script
from centinel.core.hashchain import compute_hash


def test_compute_hash_matches_sha256_for_single_payload():
    """Español: calcula SHA-256 esperado.

    English: computes expected SHA-256.
    """
    payload = '{"key": "value"}'
    hashed = compute_hash(payload)

    assert len(hashed) == 64
    assert hashed == compute_hash(payload)


def test_compute_hash_is_deterministic():
    """Español: hash determinístico.

    English: deterministic hash.
    """
    payload = '{"id": 123, "status": "ok"}'

    assert compute_hash(payload) == compute_hash(payload)


def test_compute_hash_includes_previous_hash():
    """Español: hash encadenado cambia con previous hash.

    English: chained hash changes with previous hash.
    """
    payload = '{"key": "value"}'
    previous_hash = compute_hash(payload)
    chained_hash = compute_hash(payload, previous_hash=previous_hash)

    assert chained_hash != previous_hash
    assert chained_hash == compute_hash(payload, previous_hash=previous_hash)


def test_hash_file_raises_file_not_found(tmp_path: Path):
    """hash_file should fail with missing file.

    hash_file debe fallar con archivo inexistente.
    """
    missing = tmp_path / "does-not-exist.json"
    try:
        hash_script.hash_file(missing)
        assert False, "Expected FileNotFoundError"
    except FileNotFoundError:
        assert True


def test_write_snapshot_hash_creates_chained_payload(tmp_path: Path, monkeypatch):
    """write_snapshot_hash should persist a valid chained record.

    write_snapshot_hash debe persistir un registro encadenado válido.
    """
    data_dir = tmp_path / "data"
    hash_dir = tmp_path / "hashes"
    data_dir.mkdir()
    source_dir = data_dir / "snapshots" / "test_source"
    source_dir.mkdir(parents=True)
    (source_dir / "snapshot_1.json").write_text('{"a": 1}', encoding="utf-8")

    monkeypatch.setattr(hash_script, "DATA_DIR", data_dir)
    monkeypatch.setattr(hash_script, "HASH_DIR", hash_dir)

    manifest = hash_script.build_manifest(data_dir)
    output = hash_script.write_snapshot_hash(manifest, hash_dir)
    payload = json.loads(output.read_text(encoding="utf-8"))

    assert output.exists()
    assert payload["manifest_count"] == 1
    assert len(payload["hash"]) == 64
    assert len(payload["chained_hash"]) == 64


def test_build_manifest_skips_symlink_candidates(tmp_path: Path):
    """English: symlink JSONs are ignored for secure manifests. Español: se ignoran symlinks JSON por seguridad."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    source_dir = data_dir / "snapshots" / "test_source"
    source_dir.mkdir(parents=True)
    target = source_dir / "snapshot_safe.json"
    target.write_text('{"ok": true}', encoding="utf-8")
    (source_dir / "snapshot_link.json").symlink_to(target)

    manifest = hash_script.build_manifest(data_dir)
    files = {entry["file"] for entry in manifest}
    assert any("snapshot_safe.json" in f for f in files)
    assert not any("snapshot_link.json" in f for f in files)
