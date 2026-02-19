from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts import secrets_audit


def test_secrets_audit_pass_without_rotation_file() -> None:
    report = secrets_audit.run_audit(rotation_file=None, max_age_days=90)
    assert report["status"] == "PASS"


def test_secrets_audit_detects_stale_rotation(tmp_path: Path) -> None:
    rotation = tmp_path / "rotation.json"
    stale = datetime.now(timezone.utc) - timedelta(days=120)
    rotation.write_text(json.dumps({"last_rotated_utc": stale.isoformat()}), encoding="utf-8")

    report = secrets_audit.run_audit(rotation_file=rotation, max_age_days=90)
    assert report["status"] == "FAIL"
    assert "rotation_stale" in report["errors"]
