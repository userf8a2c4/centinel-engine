#!/usr/bin/env python3
"""Audit secret hygiene and rotation metadata."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SENSITIVE_ENV_KEYS = [
    "ARBITRUM_PRIVATE_KEY",
    "SECRET_ENCRYPTION_KEY",
    "API_KEY",
    "TOKEN",
]


def run_audit(rotation_file: Path | None, max_age_days: int) -> dict[str, Any]:
    errors: list[str] = []
    checks: dict[str, Any] = {"env": {}, "rotation": None}

    for key in SENSITIVE_ENV_KEYS:
        value = os.getenv(key)
        checks["env"][key] = {
            "present": bool(value),
            "looks_redacted": (value in {None, "", "[REDACTED]", "***"}),
        }
        if value and value not in {"[REDACTED]", "***"} and len(value) < 8:
            errors.append(f"weak_secret_value:{key}")

    if rotation_file is not None:
        if not rotation_file.exists():
            errors.append("rotation_metadata_missing")
            checks["rotation"] = {"exists": False}
        else:
            payload = json.loads(rotation_file.read_text(encoding="utf-8"))
            last_rotated = payload.get("last_rotated_utc")
            if not last_rotated:
                errors.append("rotation_last_rotated_missing")
            else:
                dt = datetime.fromisoformat(last_rotated.replace("Z", "+00:00"))
                age_days = (datetime.now(timezone.utc) - dt).days
                checks["rotation"] = {"exists": True, "age_days": age_days}
                if age_days > max_age_days:
                    errors.append("rotation_stale")

    return {
        "schema_version": "1.0",
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "checks": checks,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit secrets and rotation hygiene")
    parser.add_argument("--output", required=True)
    parser.add_argument("--rotation-file")
    parser.add_argument("--max-age-days", type=int, default=90)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run_audit(
        rotation_file=Path(args.rotation_file) if args.rotation_file else None,
        max_age_days=args.max_age_days,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"secrets_audit={report['status']}")
    if report["status"] == "PASS":
        return 0
    for err in report["errors"]:
        print(err)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
