"""Pruebas de carga y validación de configuración YAML.

Tests for YAML configuration loading and validation.
"""

import pytest

from sentinel.utils import config_loader

yaml = pytest.importorskip("yaml")


def test_load_config_reads_yaml(tmp_path, monkeypatch):
    """Español: Función test_load_config_reads_yaml del módulo tests/test_config.py.

    English: Function test_load_config_reads_yaml defined in tests/test_config.py.
    """
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        yaml.safe_dump(
            {
                "master_switch": "ON",
                "base_url": "https://example.test/api",
                "endpoints": {"nacional": "https://example.test/nacional"},
                "timeout": 9,
                "retries": 2,
                "headers": {"User-Agent": "sentinel"},
                "use_playwright": False,
                "playwright_stealth": True,
                "playwright_user_agent": "sentinel",
                "playwright_viewport": {"width": 1, "height": 1},
                "playwright_locale": "es-HN",
                "playwright_timezone": "UTC",
                "backoff_base_seconds": 2,
                "backoff_max_seconds": 10,
                "candidate_count": 5,
                "required_keys": ["foo"],
                "field_map": {
                    "totals": {"total_votes": ["totales.votos"]},
                    "candidate_roots": ["resultados"],
                },
                "sources": [
                    {
                        "name": "custom",
                        "department_code": "99",
                        "level": "NAT",
                        "scope": "NATIONAL",
                    }
                ],
                "logging": {"level": "INFO", "file": "centinel.log"},
                "blockchain": {
                    "enabled": False,
                    "network": "polygon-mumbai",
                    "private_key": "0x...",
                },
                "alerts": {
                    "critical_anomaly_types": ["FOO"],
                },
                "arbitrum": {
                    "enabled": False,
                    "network": "Arbitrum One",
                    "rpc_url": "https://arb1.arbitrum.io/rpc",
                    "private_key": "0x...",
                    "contract_address": "0x...",
                    "interval_minutes": 15,
                    "batch_size": 19,
                    "auto_anchor_snapshots": True,
                },
                "rules": {"global_enabled": True},
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(config_loader, "CONFIG_PATH", config_file)

    config = config_loader.load_config()

    assert config["base_url"] == "https://example.test/api"
    assert config["timeout"] == 9
    assert config["retries"] == 2
    assert config["headers"]["User-Agent"] == "sentinel"
    assert config["candidate_count"] == 5
    assert config["required_keys"] == ["foo"]
    assert config["sources"][0]["department_code"] == "99"


def test_load_config_missing_key_raises(tmp_path, monkeypatch):
    """Español: Función test_load_config_missing_key_raises del módulo tests/test_config.py.

    English: Function test_load_config_missing_key_raises defined in tests/test_config.py.
    """
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.safe_dump({"base_url": "https://example.test"}))

    monkeypatch.setattr(config_loader, "CONFIG_PATH", config_file)

    with pytest.raises(KeyError):
        config_loader.load_config()
