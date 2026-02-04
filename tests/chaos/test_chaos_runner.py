"""Chaos testing unit tests for CNE recovery scenarios.

Español:
Estas pruebas validan que el mecanismo de resiliencia se recupera ante
rate-limits 429 y mantiene la consistencia de datos durante la auditoría.

English:
These tests validate that the resilience mechanism recovers from 429 rate
limits and maintains data consistency during the audit.
"""

import logging

import requests
import responses

from scripts.chaos_test import (
    ChaosLevelConfig,
    ChaosMetrics,
    build_polling_payload,
    fetch_polling_json,
)


def _build_level_config() -> ChaosLevelConfig:
    """Español: Construye un nivel mínimo para pruebas rápidas.

    English: Build a minimal level for fast tests.
    """

    return ChaosLevelConfig(
        name="test",
        duration_seconds=1.0,
        request_interval_seconds=0.0,
        failure_probability=1.0,
        timeout_seconds=0.5,
        max_attempts=3,
        backoff_seconds=0.0,
        watchdog_inactivity_seconds=5.0,
        scenarios={},
    )


def test_fetch_recovers_after_429() -> None:
    """Español: Verifica recuperación tras un 429 antes de éxito.

    English: Verify recovery after a 429 before success.
    """

    level = _build_level_config()
    metrics = ChaosMetrics()
    logger = logging.getLogger("tests.chaos.429")
    url = "https://cne.example/api/polling/national.json"
    payload = build_polling_payload("national", 2)

    with responses.RequestsMock(assert_all_requests_are_fired=False) as mock:
        mock.add(responses.GET, url, status=429, json={"error": "rate limit"})
        mock.add(responses.GET, url, status=200, json=payload)
        session = requests.Session()
        result = fetch_polling_json(session, url, level, metrics, logger)

    assert result["data"]["scope"] == "national"
    assert metrics.failures.get("rate_limit_429") == 1
