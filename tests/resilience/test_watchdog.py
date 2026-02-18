"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `tests/resilience/test_watchdog.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - test_watchdog_heartbeat_miss_triggers_failure_and_recovery_log
  - test_watchdog_grace_period_and_action_trigger
  - test_watchdog_handle_failure_invokes_restart_hooks

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `tests/resilience/test_watchdog.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - test_watchdog_heartbeat_miss_triggers_failure_and_recovery_log
  - test_watchdog_grace_period_and_action_trigger
  - test_watchdog_handle_failure_invokes_restart_hooks

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import logging
import pytest

from scripts import watchdog


def test_watchdog_heartbeat_miss_triggers_failure_and_recovery_log(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Español: Simula heartbeat perdido y valida registro de recuperación.

    English: Simulate a missed heartbeat and validate recovery logging.
    """
    config = watchdog.WatchdogConfig(
        heartbeat_timeout=1,
        heartbeat_path=str(tmp_path / "data" / "heartbeat.json"),
        state_path=str(tmp_path / "data" / "watchdog_state.json"),
    )
    heartbeat_path = Path(config.heartbeat_path)
    heartbeat_path.parent.mkdir(parents=True, exist_ok=True)
    heartbeat_path.write_text("{}", encoding="utf-8")

    stale_time = datetime.now(timezone.utc) - timedelta(minutes=5)
    timestamp = stale_time.timestamp()
    heartbeat_path.touch()
    Path(config.heartbeat_path).utime((timestamp, timestamp))

    ok, reason = watchdog._check_heartbeat(config)
    assert ok is False
    assert "heartbeat_stale" in reason

    state: dict[str, object] = {"failures": {}}
    logger = logging.getLogger("centinel.watchdog.test")

    with caplog.at_level(logging.INFO):
        watchdog._record_failures({"heartbeat": reason}, state, logger)
        watchdog._record_failures({}, state, logger)

    assert "watchdog_recovered" in caplog.text


def test_watchdog_grace_period_and_action_trigger(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Español: Verifica respeto de grace_period y disparo posterior.

    English: Verify grace period is respected before action trigger.
    """
    config = watchdog.WatchdogConfig(failure_grace_minutes=2, action_cooldown_minutes=5)
    now = datetime(2029, 11, 30, 12, 0, tzinfo=timezone.utc)

    state = {
        "failures": {
            "heartbeat": {
                "first_seen": (now - timedelta(minutes=1)).isoformat(),
                "last_seen": (now - timedelta(minutes=1)).isoformat(),
                "reason": "heartbeat_stale",
            }
        },
        "last_action": None,
    }

    monkeypatch.setattr(watchdog, "_utcnow", lambda: now)
    should_act, reasons = watchdog._should_act(state, config)
    assert should_act is False
    assert reasons == []

    later = now + timedelta(minutes=3)
    monkeypatch.setattr(watchdog, "_utcnow", lambda: later)
    should_act, reasons = watchdog._should_act(state, config)
    assert should_act is True
    assert reasons


def test_watchdog_handle_failure_invokes_restart_hooks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Español: Confirma reinicio/alerta cuando fallas acumuladas superan el umbral.

    English: Confirm restart/alert is invoked when accumulated failures cross the threshold.
    """
    config = watchdog.WatchdogConfig(alert_urls=["https://alert.local"], aggressive_restart=False)
    calls = {"alert": 0, "terminate": 0, "start": 0}

    def fake_alerts(*_args, **_kwargs) -> None:
        calls["alert"] += 1

    def fake_terminate(*_args, **_kwargs) -> bool:
        calls["terminate"] += 1
        return True

    def fake_start(*_args, **_kwargs) -> None:
        calls["start"] += 1

    monkeypatch.setattr(watchdog, "_send_alerts", fake_alerts)
    monkeypatch.setattr(watchdog, "_terminate_pipeline", fake_terminate)
    monkeypatch.setattr(watchdog, "_start_pipeline", fake_start)

    logger = logging.getLogger("centinel.watchdog.test")
    watchdog._handle_failure(config, ["heartbeat:stale"], logger)

    assert calls["alert"] == 1
    assert calls["terminate"] == 1
    assert calls["start"] == 1
