"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `tests/chaos/test_chaos_runner.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - _build_level_config
  - test_fetch_recovers_after_429

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `tests/chaos/test_chaos_runner.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - _build_level_config
  - test_fetch_recovers_after_429

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
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
