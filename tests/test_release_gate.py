from __future__ import annotations

import json
from pathlib import Path

from scripts import release_gate


def test_release_gate_pass_with_sbom_and_skip_lock(tmp_path: Path) -> None:
    sbom = tmp_path / "sbom.v5.0.0.json"
    sbom.write_text('{"bomFormat":"CycloneDX"}', encoding="utf-8")
    out = tmp_path / "release_gate.json"

    report = release_gate.run_release_gate(
        release_version="v5.0.0",
        sbom_path=sbom,
        output_path=out,
        check_lock=False,
    )

    assert report["status"] == "PASS"
    assert out.exists()


def test_release_gate_fail_on_missing_sbom(tmp_path: Path) -> None:
    out = tmp_path / "release_gate.json"

    report = release_gate.run_release_gate(
        release_version="v5.0.1",
        sbom_path=tmp_path / "missing.json",
        output_path=out,
        check_lock=False,
    )

    assert report["status"] == "FAIL"
    assert "sbom_missing_or_empty" in report["errors"]


def test_release_gate_fail_on_invalid_release_version(tmp_path: Path) -> None:
    sbom = tmp_path / "sbom.json"
    sbom.write_text('{"bomFormat":"CycloneDX"}', encoding="utf-8")
    out = tmp_path / "release_gate.json"

    report = release_gate.run_release_gate(
        release_version="v5 invalid",
        sbom_path=sbom,
        output_path=out,
        check_lock=False,
    )

    assert report["status"] == "FAIL"
    assert "invalid_release_version" in report["errors"]
    parsed = json.loads(out.read_text(encoding="utf-8"))
    assert parsed["gate"] == "release_mandatory_checklist"
