"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `tests/resilience/test_circuit_breaker.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - test_circuit_breaker_transitions_logs_and_cooldown_recovery
  - test_circuit_breaker_half_open_failure_reopens
  - test_low_profile_interval_and_jitter_for_polling

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `tests/resilience/test_circuit_breaker.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - test_circuit_breaker_transitions_logs_and_cooldown_recovery
  - test_circuit_breaker_half_open_failure_reopens
  - test_low_profile_interval_and_jitter_for_polling

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import random

from scripts.circuit_breaker import CircuitBreaker
from scripts.run_pipeline import (
    resolve_poll_interval_seconds,
    resolve_poll_jitter_factor,
)


def test_circuit_breaker_transitions_logs_and_cooldown_recovery() -> None:
    """Español: Valida transición CLOSED→OPEN→HALF_OPEN, alertas y cooldown.

    English: Validate CLOSED→OPEN→HALF_OPEN transitions, alert gating, and cooldown.
    """
    now = datetime(2029, 11, 30, 12, 0, tzinfo=timezone.utc)
    breaker = CircuitBreaker(
        failure_threshold=2,
        failure_window_seconds=60,
        open_timeout_seconds=120,
        half_open_after_seconds=30,
        success_threshold=1,
        open_log_interval_seconds=15,
    )

    assert breaker.state == "CLOSED"
    assert breaker.record_failure(now) is False
    assert breaker.record_failure(now + timedelta(seconds=1)) is True
    assert breaker.state == "OPEN"

    # The breaker opened at now + 1s, so _next_log_at == now + 1s.
    # Pass a time >= _next_log_at to trigger the first log.
    assert breaker.should_log_open_wait(now + timedelta(seconds=1)) is True
    assert breaker.should_log_open_wait(now + timedelta(seconds=5)) is False
    assert breaker.consume_open_alert() is True
    assert breaker.consume_open_alert() is False

    assert breaker.allow_request(now + timedelta(seconds=10)) is False
    # Breaker opened at now + 1s; half_open_after = 30s → target = now + 31s
    assert breaker.seconds_until_half_open(now + timedelta(seconds=10)) == 21.0
    assert breaker.allow_request(now + timedelta(seconds=31)) is True
    assert breaker.state == "HALF_OPEN"

    assert breaker.record_success(now + timedelta(seconds=32)) is True
    assert breaker.state == "CLOSED"


def test_circuit_breaker_half_open_failure_reopens() -> None:
    """Español: Asegura que una falla en HALF_OPEN regresa a OPEN.

    English: Ensure a HALF_OPEN failure returns the breaker to OPEN.
    """
    now = datetime(2029, 11, 30, 12, 0, tzinfo=timezone.utc)
    breaker = CircuitBreaker(
        failure_threshold=1,
        failure_window_seconds=60,
        open_timeout_seconds=120,
        half_open_after_seconds=30,
        success_threshold=2,
    )

    breaker.record_failure(now)
    assert breaker.state == "OPEN"
    assert breaker.allow_request(now + timedelta(seconds=31)) is True
    assert breaker.state == "HALF_OPEN"

    assert breaker.record_failure(now + timedelta(seconds=32)) is True
    assert breaker.state == "OPEN"


def test_low_profile_interval_and_jitter_for_polling() -> None:
    """Español: Comprueba que low-profile aumenta intervalo y aplica jitter acotado.

    English: Ensure low-profile increases polling interval and applies bounded jitter.
    """
    config = {
        "poll_interval_minutes": 30,
        "low_profile": {
            "enabled": True,
            "base_interval_minutes": 120,
            "jitter_percent": 20,
        },
    }

    interval = resolve_poll_interval_seconds(config)
    assert interval >= 120 * 60

    rng = random.Random(42)
    jitter_factor = resolve_poll_jitter_factor(config, rng)
    assert 0.8 <= jitter_factor <= 1.2
