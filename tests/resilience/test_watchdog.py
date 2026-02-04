"""Watchdog resilience tests for heartbeat and restart logic."""

from __future__ import annotations

import logging
import os
from datetime import timedelta

import pytest

from scripts import watchdog


def test_watchdog_heartbeat_stale_detection(tmp_path) -> None:
    """Español: Detecta heartbeat vencido usando mtime y timeout configurado.

    English: Detect stale heartbeat using file mtime and configured timeout.
    """
    heartbeat = tmp_path / "heartbeat.json"
    heartbeat.write_text("{}", encoding="utf-8")

    stale_time = watchdog._utcnow() - timedelta(minutes=5)
    os.utime(heartbeat, (stale_time.timestamp(), stale_time.timestamp()))

    config = watchdog.WatchdogConfig(
        heartbeat_path=str(heartbeat),
        heartbeat_timeout=1,
    )

    ok, message = watchdog._check_heartbeat(config)

    assert ok is False
    assert "heartbeat_stale" in message


def test_watchdog_respects_grace_period_before_action() -> None:
    """Español: Respeta el grace_period antes de ejecutar acciones.

    English: Respect the grace period before taking action.
    """
    now = watchdog._utcnow()
    config = watchdog.WatchdogConfig(failure_grace_minutes=5, action_cooldown_minutes=1)
    state = {
        "failures": {
            "heartbeat": {
                "first_seen": now.isoformat(),
                "last_seen": now.isoformat(),
                "reason": "heartbeat_missing",
            }
        },
        "last_action": None,
        "log_state": {},
    }

    should_act, reasons = watchdog._should_act(state, config)
    assert should_act is False
    assert reasons == []

    past = (now - timedelta(minutes=6)).isoformat()
    state["failures"]["heartbeat"]["first_seen"] = past
    should_act, reasons = watchdog._should_act(state, config)
    assert should_act is True
    assert reasons


def test_watchdog_handle_failure_triggers_restart_and_logs(monkeypatch) -> None:
    """Español: Confirma reinicio automático y logging crítico ante fallas.

    English: Confirm automatic restart and critical logging on failures.
    """
    actions: dict[str, int] = {"alerts": 0, "terminate": 0, "start": 0}

    def fake_send_alerts(*_args, **_kwargs):
        actions["alerts"] += 1

    def fake_terminate(*_args, **_kwargs):
        actions["terminate"] += 1
        return True

    def fake_start(*_args, **_kwargs):
        actions["start"] += 1

    logged: list[tuple[int, str]] = []

    def fake_log_event(_logger, level, event, **_fields):
        logged.append((level, event))

    monkeypatch.setattr(watchdog, "_send_alerts", fake_send_alerts)
    monkeypatch.setattr(watchdog, "_terminate_pipeline", fake_terminate)
    monkeypatch.setattr(watchdog, "_start_pipeline", fake_start)
    monkeypatch.setattr(watchdog, "log_event", fake_log_event)

    logger = logging.getLogger("centinel.watchdog")
    config = watchdog.WatchdogConfig(aggressive_restart=False)

    watchdog._handle_failure(config, ["heartbeat:missing"], logger)

    assert actions == {"alerts": 1, "terminate": 1, "start": 1}
    assert logged == [(logging.CRITICAL, "watchdog_failure")]


def test_watchdog_record_failures_logs_recovery(caplog) -> None:
    """Español: Registra recuperación cuando falla desaparece del estado.

    English: Log recovery when a failure disappears from tracked state.
    """
    logger = logging.getLogger("centinel.watchdog")
    state = {"failures": {}, "last_action": None, "log_state": {}}

    with caplog.at_level(logging.INFO):
        watchdog._record_failures({"snapshot": "missing"}, state, logger)
        watchdog._record_failures({}, state, logger)

    assert any("watchdog_recovered" in record.message for record in caplog.records)
