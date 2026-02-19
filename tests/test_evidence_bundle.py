from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_evidence_bundle_create_and_verify(tmp_path: Path) -> None:
    data_dir = tmp_path / "snapshots"
    data_dir.mkdir()
    (data_dir / "a.json").write_text('{"x":1}', encoding="utf-8")
    (data_dir / "b.json").write_text('{"y":2}', encoding="utf-8")

    bundle = tmp_path / "bundle.json"

    subprocess.run(
        [
            sys.executable,
            "scripts/evidence_bundle.py",
            "--input-dir",
            str(data_dir),
            "--output",
            str(bundle),
        ],
        check=True,
    )

    parsed = json.loads(bundle.read_text(encoding="utf-8"))
    assert parsed["file_count"] == 2
    assert len(parsed["files"]) == 2
    assert parsed["merkle_root_sha256"]

    subprocess.run(
        [
            sys.executable,
            "scripts/verify_evidence_bundle.py",
            "--bundle",
            str(bundle),
            "--base-dir",
            str(data_dir),
        ],
        check=True,
    )


def test_evidence_bundle_detects_tampering(tmp_path: Path) -> None:
    data_dir = tmp_path / "snapshots"
    data_dir.mkdir()
    target = data_dir / "a.json"
    target.write_text('{"x":1}', encoding="utf-8")

    bundle = tmp_path / "bundle.json"
    subprocess.run(
        [
            sys.executable,
            "scripts/evidence_bundle.py",
            "--input-dir",
            str(data_dir),
            "--output",
            str(bundle),
        ],
        check=True,
    )

    target.write_text('{"x":999}', encoding="utf-8")

    proc = subprocess.run(
        [
            sys.executable,
            "scripts/verify_evidence_bundle.py",
            "--bundle",
            str(bundle),
            "--base-dir",
            str(data_dir),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 1
    assert "verification=FAIL" in proc.stdout
    assert "hash_mismatch:a.json" in proc.stdout
