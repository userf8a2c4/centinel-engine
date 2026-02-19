from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from centinel.core.custody import generate_operator_keypair, sign_hash_record


def test_verify_snapshot_bundle_pass_with_signature_and_anchor(tmp_path: Path) -> None:
    snapshot = tmp_path / "snapshot.json"
    snapshot.write_text('{"ok": true}', encoding="utf-8")
    sha = hashlib.sha256(snapshot.read_bytes()).hexdigest()

    record = {
        "manifest": [{"file": snapshot.name, "sha256": sha}],
        "chained_hash": "abc123",
        "pipeline_version": "v1.0.0",
    }
    generate_operator_keypair(key_dir=tmp_path, operator_id="test-op")
    signed_record = sign_hash_record(record, key_path=tmp_path / "operator_private.pem", operator_id="test-op")
    hash_record = tmp_path / "hash_record.json"
    hash_record.write_text(json.dumps(signed_record), encoding="utf-8")

    anchor = tmp_path / "anchor.json"
    anchor.write_text(json.dumps({"root_hash": "abc123"}), encoding="utf-8")

    rules = tmp_path / "rules.json"
    rules.write_text(json.dumps({"rules": {"global_enabled": True, "turnout_impossible": {"enabled": True}}}), encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            "scripts/verify_snapshot_bundle.py",
            "--snapshot",
            str(snapshot),
            "--hash-record",
            str(hash_record),
            "--rules",
            str(rules),
            "--pipeline-version",
            "v1.0.0",
            "--require-signature",
            "--anchor-log",
            str(anchor),
        ],
        check=True,
    )


def test_verify_snapshot_bundle_fail_on_mismatch(tmp_path: Path) -> None:
    snapshot = tmp_path / "snapshot.json"
    snapshot.write_text('{"ok": true}', encoding="utf-8")

    hash_record = tmp_path / "hash_record.json"
    hash_record.write_text(
        json.dumps({"manifest": [{"file": snapshot.name, "sha256": "0" * 64}], "chained_hash": "x"}),
        encoding="utf-8",
    )
    rules = tmp_path / "rules.json"
    rules.write_text(json.dumps({"rules": {"global_enabled": True}}), encoding="utf-8")

    proc = subprocess.run(
        [
            sys.executable,
            "scripts/verify_snapshot_bundle.py",
            "--snapshot",
            str(snapshot),
            "--hash-record",
            str(hash_record),
            "--rules",
            str(rules),
            "--pipeline-version",
            "v1.0.0",
            "--require-signature",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 1
    assert "verification=FAIL" in proc.stdout
    assert "snapshot_hash_mismatch" in proc.stdout
    assert "no_enabled_rules" in proc.stdout
    assert "missing_operator_signature" in proc.stdout
