"""Pruebas de configuración para el módulo Centinel.

Tests for the Centinel configuration module.
"""

import json
from pathlib import Path

import pytest

from centinel.config import load_config


def test_load_config_validates_and_loads(monkeypatch, tmp_path):
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
