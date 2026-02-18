"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `tests/load_tests.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - polling_json_payloads
  - mesa_entries
  - test_polling_load_with_100k_payloads
  - test_mesa_processing_time_limit
  - bloque_main

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `tests/load_tests.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - polling_json_payloads
  - mesa_entries
  - test_polling_load_with_100k_payloads
  - test_mesa_processing_time_limit
  - bloque_main

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
"""

from __future__ import annotations

import json
import time

import pytest

from centinel.core.rules.common import (
    extract_mesa_code,
    extract_mesa_vote_breakdown,
    extract_mesas,
)


@pytest.fixture(scope="session")
def polling_json_payloads() -> list[str]:
    """Return 100k mocked polling JSON payloads. (Devuelve 100k JSONs de sondeo simulados.)"""
    payload = json.dumps(
        {
            "meta": {"porcentaje_escrutado": 12.5},
            "mesas": [
                {
                    "codigo": "M-000",
                    "totals": {
                        "validos": 90,
                        "blancos": 5,
                        "nulos": 5,
                        "total": 100,
                        "inscritos": 120,
                    },
                }
            ],
        }
    )
    # Replicate a compact payload to simulate 100k polls. (Replicar un payload compacto para simular 100k sondeos.)
    return [payload] * 100_000


@pytest.fixture()
def mesa_entries() -> list[dict]:
    """Provide mesas to validate per-table processing limits. (Provee mesas para validar límites por mesa.)"""
    mesas: list[dict] = []
    for idx in range(1_000):
        mesas.append(
            {
                "codigo": f"M-{idx:04d}",
                "totals": {
                    "validos": 300,
                    "blancos": 10,
                    "nulos": 5,
                    "total": 315,
                    "inscritos": 450,
                },
            }
        )
    return mesas


def test_polling_load_with_100k_payloads(polling_json_payloads: list[str]) -> None:
    """Simulate 100k polling JSONs and count mesas. (Simula 100k JSONs de sondeo y cuenta mesas.)"""
    mesa_count = 0
    for payload in polling_json_payloads:
        data = json.loads(payload)
        mesas = extract_mesas(data)
        mesa_count += len(mesas)
    # Ensure we processed every mocked payload. (Asegura que se procesó cada payload simulado.)
    assert mesa_count == 100_000


def test_mesa_processing_time_limit(mesa_entries: list[dict]) -> None:
    """Measure processing time per mesa under a conservative limit. (Mide el tiempo por mesa bajo un límite conservador.)"""
    start = time.perf_counter()
    for mesa in mesa_entries:
        _ = extract_mesa_code(mesa)
        _ = extract_mesa_vote_breakdown(mesa)
    elapsed = time.perf_counter() - start
    per_mesa = elapsed / len(mesa_entries)
    # Keep a generous cap to avoid flaky CI results. (Mantén un límite amplio para evitar resultados inestables en CI.)
    assert per_mesa <= 0.004


if __name__ == "__main__":
    # Manual invocation helper. (Ayuda para ejecución manual.)
    raise SystemExit(pytest.main([__file__]))
