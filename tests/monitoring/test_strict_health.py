"""Español: Módulo con utilidades y definiciones para tests/monitoring/test_strict_health.py.

English: Module utilities and definitions for tests/monitoring/test_strict_health.py.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from monitoring import strict_health


def _make_payload(timestamp: datetime) -> dict:
    """Español: Función _make_payload del módulo tests/monitoring/test_strict_health.py.

    English: Function _make_payload defined in tests/monitoring/test_strict_health.py.
    """
    return {"metadata": {"checkpoint_timestamp": timestamp.isoformat()}, "state": {}}


def test_check_checkpoint_age_stale(monkeypatch: pytest.MonkeyPatch) -> None:
    """Español: Función test_check_checkpoint_age_stale del módulo tests/monitoring/test_strict_health.py.

    English: Function test_check_checkpoint_age_stale defined in tests/monitoring/test_strict_health.py.
    """
    timestamp = datetime.now(timezone.utc) - timedelta(minutes=30)
    monkeypatch.setenv("MAX_CHECKPOINT_AGE_SECONDS", "60")
    result = strict_health._check_checkpoint_age(timestamp)
    assert result["ok"] is False
    assert result["message"] == "checkpoint_stale"


def test_is_healthy_strict_failure_logs_reason(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Español: Función test_is_healthy_strict_failure_logs_reason del módulo tests/monitoring/test_strict_health.py.

    English: Function test_is_healthy_strict_failure_logs_reason defined in tests/monitoring/test_strict_health.py.
    """
    monkeypatch.setattr(
        strict_health, "_get_checkpoint_manager", lambda: (object(), None)
    )
    monkeypatch.setattr(strict_health, "_build_s3_client", lambda: object())
    monkeypatch.setattr(
        strict_health,
        "_check_bucket_latency",
        lambda *_: {"ok": True, "message": "bucket_latency_ok"},
    )
    monkeypatch.setattr(
        strict_health,
        "_load_checkpoint_payload",
        lambda *_: (
            _make_payload(datetime.now(timezone.utc)),
            "checkpoint_integrity_ok",
        ),
    )
    monkeypatch.setattr(
        strict_health,
        "_check_storage_write",
        lambda *_: {"ok": True, "message": "storage_write_ok"},
    )
    monkeypatch.setattr(
        strict_health,
        "_check_critical_errors",
        lambda: {"ok": True, "message": "critical_errors_ok"},
    )
    monkeypatch.setattr(
        strict_health,
        "_check_resources",
        lambda: {"ok": False, "message": "resources_threshold_exceeded"},
    )
    monkeypatch.setattr(
        strict_health,
        "_check_paused_flag",
        lambda: {"ok": True, "message": "paused_flag_clear"},
    )

    with caplog.at_level("CRITICAL"):
        ok, diagnostics = asyncio.run(strict_health.is_healthy_strict())

    assert ok is False
    assert "resources_threshold_exceeded" in diagnostics["failures"]
    assert any(
        "strict_healthcheck_failed" in record.message for record in caplog.records
    )


def test_is_healthy_strict_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Español: Función test_is_healthy_strict_success del módulo tests/monitoring/test_strict_health.py.

    English: Function test_is_healthy_strict_success defined in tests/monitoring/test_strict_health.py.
    """
    monkeypatch.setattr(
        strict_health, "_get_checkpoint_manager", lambda: (object(), None)
    )
    monkeypatch.setattr(strict_health, "_build_s3_client", lambda: object())
    monkeypatch.setattr(
        strict_health,
        "_check_bucket_latency",
        lambda *_: {"ok": True, "message": "bucket_latency_ok"},
    )
    monkeypatch.setattr(
        strict_health,
        "_load_checkpoint_payload",
        lambda *_: (
            _make_payload(datetime.now(timezone.utc)),
            "checkpoint_integrity_ok",
        ),
    )
    monkeypatch.setattr(
        strict_health,
        "_check_storage_write",
        lambda *_: {"ok": True, "message": "storage_write_ok"},
    )
    monkeypatch.setattr(
        strict_health,
        "_check_critical_errors",
        lambda: {"ok": True, "message": "critical_errors_ok"},
    )
    monkeypatch.setattr(
        strict_health,
        "_check_resources",
        lambda: {"ok": True, "message": "resources_ok"},
    )
    monkeypatch.setattr(
        strict_health,
        "_check_paused_flag",
        lambda: {"ok": True, "message": "paused_flag_clear"},
    )

    ok, diagnostics = asyncio.run(strict_health.is_healthy_strict())

    assert ok is True
    assert diagnostics["healthy"] is True
