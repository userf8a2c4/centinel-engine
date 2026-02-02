from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone

import pytest

from monitoring import strict_health


def _make_checkpoint_payload(timestamp: datetime) -> tuple[bytes, dict]:
    payload = {"timestamp": timestamp.isoformat(), "hash": "placeholder"}
    raw = json.dumps(payload, sort_keys=True).encode("utf-8")
    expected_hash = hashlib.sha256(raw).hexdigest()
    payload["hash"] = expected_hash
    raw = json.dumps(payload, sort_keys=True).encode("utf-8")
    return raw, payload


def test_verify_checkpoint_integrity_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    raw, payload = _make_checkpoint_payload(datetime.now(timezone.utc))
    expected_hash = hashlib.sha256(raw).hexdigest()
    monkeypatch.setenv("CHECKPOINT_EXPECTED_HASH", expected_hash)
    ok, message = strict_health._verify_checkpoint_integrity(
        {"payload": payload, "raw": raw, "meta": {}}
    )
    assert ok is True
    assert message == "checkpoint_hash_ok"


def test_verify_checkpoint_age_stale(monkeypatch: pytest.MonkeyPatch) -> None:
    timestamp = datetime.now(timezone.utc) - timedelta(minutes=30)
    raw, payload = _make_checkpoint_payload(timestamp)
    monkeypatch.setenv("MAX_AGE_CHECKPOINT_SECONDS", "60")
    ok, message = strict_health._verify_checkpoint_age(
        {"payload": payload, "raw": raw, "meta": {}}
    )
    assert ok is False
    assert message == "checkpoint_stale"


def test_is_healthy_strict_failure_logs_reason(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(strict_health, "_read_checkpoint", lambda: (True, "ok", {}))
    monkeypatch.setattr(
        strict_health, "_verify_checkpoint_integrity", lambda _: (False, "bad_hash")
    )
    monkeypatch.setattr(
        strict_health, "_verify_checkpoint_age", lambda _: (True, "fresh")
    )
    monkeypatch.setattr(
        strict_health, "_check_pending_actas", lambda: (True, "pending_ok")
    )
    monkeypatch.setattr(
        strict_health, "_check_critical_errors", lambda: (True, "critical_ok")
    )
    monkeypatch.setattr(strict_health, "_check_resources", lambda: (True, "resources_ok"))
    monkeypatch.setattr(
        strict_health, "_check_storage_write", lambda: (True, "write_ok")
    )

    with caplog.at_level("CRITICAL"):
        ok, message = strict_health.is_healthy_strict()

    assert ok is False
    assert "bad_hash" in message
    assert any("strict_healthcheck_failed" in record.message for record in caplog.records)


def test_is_healthy_strict_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(strict_health, "_read_checkpoint", lambda: (True, "ok", {}))
    monkeypatch.setattr(
        strict_health, "_verify_checkpoint_integrity", lambda _: (True, "hash_ok")
    )
    monkeypatch.setattr(
        strict_health, "_verify_checkpoint_age", lambda _: (True, "fresh")
    )
    monkeypatch.setattr(
        strict_health, "_check_pending_actas", lambda: (True, "pending_ok")
    )
    monkeypatch.setattr(
        strict_health, "_check_critical_errors", lambda: (True, "critical_ok")
    )
    monkeypatch.setattr(strict_health, "_check_resources", lambda: (True, "resources_ok"))
    monkeypatch.setattr(
        strict_health, "_check_storage_write", lambda: (True, "write_ok")
    )

    ok, message = strict_health.is_healthy_strict()

    assert ok is True
    assert message == "healthcheck_strict_ok"
