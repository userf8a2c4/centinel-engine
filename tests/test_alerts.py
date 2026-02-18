"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `tests/test_alerts.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - test_parse_retry_after_reads_retry_param
  - test_parse_retry_after_defaults_on_invalid_json

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `tests/test_alerts.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - test_parse_retry_after_reads_retry_param
  - test_parse_retry_after_defaults_on_invalid_json

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
"""

import httpx

from monitoring.alerts import _parse_retry_after


def test_parse_retry_after_reads_retry_param() -> None:
    """Español: Verifica lectura de retry_after en payload válido.

    English: Ensure retry_after is parsed from a valid payload.
    """
    response = httpx.Response(429, json={"parameters": {"retry_after": "3"}})

    assert _parse_retry_after(response) == 3.0


def test_parse_retry_after_defaults_on_invalid_json() -> None:
    """Español: Usa default si la respuesta no es JSON válido.

    English: Use default value when response JSON is invalid.
    """
    response = httpx.Response(429, content=b"not-json")

    assert _parse_retry_after(response) == 2.0
