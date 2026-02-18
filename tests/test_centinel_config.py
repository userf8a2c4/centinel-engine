"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `tests/test_centinel_config.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - test_load_config_validates_and_loads
  - test_load_config_rejects_short_interval
  - test_load_config_rejects_missing_storage_path

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `tests/test_centinel_config.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - test_load_config_validates_and_loads
  - test_load_config_rejects_short_interval
  - test_load_config_rejects_missing_storage_path

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
"""

import json
from pathlib import Path

import pytest

from centinel.config import load_config


def test_load_config_validates_and_loads(monkeypatch, tmp_path):
    """Español: Función test_load_config_validates_and_loads del módulo tests/test_centinel_config.py.

    English: Function test_load_config_validates_and_loads defined in tests/test_centinel_config.py.
    """
    sources = [
        {
            "url": "https://example.com/data",
            "type": "actas",
            "interval_seconds": 120,
            "auth_headers": {"Authorization": "Bearer token"},
        }
    ]

    monkeypatch.setenv("SOURCES", json.dumps(sources))
    monkeypatch.setenv("STORAGE_PATH", str(tmp_path))
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("ARBITRUM_RPC_URL", "https://arb.example.com")
    monkeypatch.setenv("IPFS_GATEWAY_URL", "https://ipfs.example.com")

    settings = load_config()

    assert settings.SOURCES[0].url == "https://example.com/data"
    assert settings.SOURCES[0].interval_seconds == 120
    assert settings.STORAGE_PATH == Path(tmp_path)
    assert settings.LOG_LEVEL == "DEBUG"


def test_load_config_rejects_short_interval(monkeypatch, tmp_path):
    """Español: Función test_load_config_rejects_short_interval del módulo tests/test_centinel_config.py.

    English: Function test_load_config_rejects_short_interval defined in tests/test_centinel_config.py.
    """
    sources = [
        {
            "url": "https://example.com/data",
            "type": "actas",
            "interval_seconds": 30,
        }
    ]

    monkeypatch.setenv("SOURCES", json.dumps(sources))
    monkeypatch.setenv("STORAGE_PATH", str(tmp_path))
    monkeypatch.setenv("ARBITRUM_RPC_URL", "https://arb.example.com")
    monkeypatch.setenv("IPFS_GATEWAY_URL", "https://ipfs.example.com")

    with pytest.raises(ValueError):
        load_config()


def test_load_config_rejects_missing_storage_path(monkeypatch, tmp_path):
    """Español: Función test_load_config_rejects_missing_storage_path del módulo tests/test_centinel_config.py.

    English: Function test_load_config_rejects_missing_storage_path defined in tests/test_centinel_config.py.
    """
    sources = [
        {
            "url": "https://example.com/data",
            "type": "actas",
            "interval_seconds": 120,
        }
    ]

    missing = tmp_path / "missing"
    monkeypatch.setenv("SOURCES", json.dumps(sources))
    monkeypatch.setenv("STORAGE_PATH", str(missing))
    monkeypatch.setenv("ARBITRUM_RPC_URL", "https://arb.example.com")
    monkeypatch.setenv("IPFS_GATEWAY_URL", "https://ipfs.example.com")

    with pytest.raises(ValueError):
        load_config()
