"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `tests/test_centinel_schemas.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - test_validate_actas_normalizes
  - test_validate_actas_migrates_fields
  - test_validate_resultados_rejects_invalid_counts
  - test_validate_rejects_invalid_json_bytes

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `tests/test_centinel_schemas.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - test_validate_actas_normalizes
  - test_validate_actas_migrates_fields
  - test_validate_resultados_rejects_invalid_counts
  - test_validate_rejects_invalid_json_bytes

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
"""

import pytest

from centinel.schemas import validate_and_normalize


def test_validate_actas_normalizes():
    """Español: Función test_validate_actas_normalizes del módulo tests/test_centinel_schemas.py.

    English: Function test_validate_actas_normalizes defined in tests/test_centinel_schemas.py.
    """
    payload = {
        "acta_id": "A1",
        "junta_receptora": "JR",
        "departamento": "Dept",
        "municipio": "Mun",
        "centro_votacion": "Centro",
        "timestamp": "2024-01-01T00:00:00Z",
        "votos_totales": 100,
    }

    normalized = validate_and_normalize(payload, "actas")

    assert normalized["acta_id"] == "A1"
    assert normalized["votos_totales"] == 100


def test_validate_actas_migrates_fields():
    """Español: Función test_validate_actas_migrates_fields del módulo tests/test_centinel_schemas.py.

    English: Function test_validate_actas_migrates_fields defined in tests/test_centinel_schemas.py.
    """
    payload = {
        "id_acta": "A2",
        "jr": "JR2",
        "departamento": "Dept",
        "municipio": "Mun",
        "cv": "Centro",
        "ts": "2024-01-01T00:00:00Z",
        "votos_totales": 50,
    }

    normalized = validate_and_normalize(payload, "actas")

    assert normalized["acta_id"] == "A2"
    assert normalized["junta_receptora"] == "JR2"


def test_validate_resultados_rejects_invalid_counts():
    """Español: Función test_validate_resultados_rejects_invalid_counts del módulo tests/test_centinel_schemas.py.

    English: Function test_validate_resultados_rejects_invalid_counts defined in tests/test_centinel_schemas.py.
    """
    payload = {
        "acta_id": "A3",
        "partido": "Partido",
        "candidato": "Cand",
        "votos": 5,
        "total_mesas": 1,
        "mesas_contabilizadas": 2,
    }

    with pytest.raises(ValueError):
        validate_and_normalize(payload, "resultados")


def test_validate_rejects_invalid_json_bytes():
    """Español: Función test_validate_rejects_invalid_json_bytes del módulo tests/test_centinel_schemas.py.

    English: Function test_validate_rejects_invalid_json_bytes defined in tests/test_centinel_schemas.py.
    """
    with pytest.raises(ValueError):
        validate_and_normalize(b"not-json", "actas")
