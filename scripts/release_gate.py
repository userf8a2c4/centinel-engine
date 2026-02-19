#!/usr/bin/env python3
"""Mandatory release gate for lockfile + SBOM integrity."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any


def run_lock_integrity_check() -> tuple[bool, str]:
    """Run lock integrity check with Poetry-version compatibility.

    Tries `poetry lock --check` first, falls back to `poetry check --lock`.
    """
    attempts = [
        ["poetry", "lock", "--check"],
        ["poetry", "check", "--lock"],
    ]
    last_output = ""
    for cmd in attempts:
        proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
        output = (proc.stdout or "") + (proc.stderr or "")
        last_output = output.strip()
        if proc.returncode == 0:
            return True, f"lock_check_ok:{' '.join(cmd)}"
        if "does not exist" in output and cmd[-1] == "--check":
            continue
    return False, f"lock_check_failed:{last_output[:300]}"


def run_release_gate(
    *,
    release_version: str,
    sbom_path: Path,
    output_path: Path,
    check_lock: bool = True,
) -> dict[str, Any]:
    errors: list[str] = []
    checks: dict[str, Any] = {
        "release_version": release_version,
        "lock_integrity": None,
        "sbom_exists": sbom_path.exists(),
        "sbom_size": sbom_path.stat().st_size if sbom_path.exists() else 0,
    }

    if not re.match(r"^[A-Za-z0-9._-]+$", release_version):
        errors.append("invalid_release_version")

    if check_lock:
        ok, detail = run_lock_integrity_check()
        checks["lock_integrity"] = {"ok": ok, "detail": detail}
        if not ok:
            errors.append("lock_integrity_failed")

    if not checks["sbom_exists"] or checks["sbom_size"] <= 0:
        errors.append("sbom_missing_or_empty")

    report = {
        "schema_version": "1.0",
        "gate": "release_mandatory_checklist",
        "status": "PASS" if not errors else "FAIL",
        "checks": checks,
        "errors": errors,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run mandatory release governance gate")
    parser.add_argument("--release-version", required=True)
    parser.add_argument("--sbom", required=True, help="Path to release-versioned SBOM")
    parser.add_argument("--output", required=True, help="Output release gate report JSON")
    parser.add_argument("--skip-lock-check", action="store_true", help="Skip lock integrity validation")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run_release_gate(
        release_version=args.release_version,
        sbom_path=Path(args.sbom),
        output_path=Path(args.output),
        check_lock=not args.skip_lock_check,
    )
    print(f"release_gate={report['status']}")
    if report["status"] == "PASS":
        return 0
    for err in report["errors"]:
        print(err)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
