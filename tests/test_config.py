"""Pruebas de carga y validación de configuración YAML.

Tests for YAML configuration loading and validation.
"""

import pytest

from centinel.utils import config_loader

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
                "headers": {"User-Agent": "centinel"},
                "use_playwright": False,
                "playwright_stealth": True,
                "playwright_user_agent": "centinel",
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
    assert config["headers"]["User-Agent"] == "centinel"
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


def test_load_config_rejects_invalid_master_switch(tmp_path, monkeypatch):
    """Reject invalid master_switch literals with a clear message."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        yaml.safe_dump(
            {
                "master_switch": "true",
                "base_url": "https://example.test/api",
                "endpoints": {"nacional": "https://example.test/nacional"},
                "timeout": 9,
                "retries": 2,
                "headers": {"User-Agent": "centinel"},
                "use_playwright": False,
                "playwright_stealth": True,
                "playwright_user_agent": "centinel",
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
                "sources": [{"name": "custom", "department_code": "99", "level": "NAT", "scope": "NATIONAL"}],
                "logging": {"level": "INFO", "file": "centinel.log"},
                "blockchain": {"enabled": False, "network": "polygon-mumbai", "private_key": "0x..."},
                "alerts": {"critical_anomaly_types": ["FOO"]},
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
    # Minimal sibling YAMLs required by load_config.
    security_file = tmp_path / "security.yaml"
    advanced_file = tmp_path / "advanced.yaml"
    attack_file = tmp_path / "attack.yaml"
    security_file.write_text("monitor_connections: true\n", encoding="utf-8")
    advanced_file.write_text("enabled: true\n", encoding="utf-8")
    attack_file.write_text("enabled: true\n", encoding="utf-8")

    monkeypatch.setattr(config_loader, "CONFIG_PATH", config_file)
    monkeypatch.setattr(config_loader, "SECURITY_PATH", security_file)
    monkeypatch.setattr(config_loader, "ADVANCED_SECURITY_PATH", advanced_file)
    monkeypatch.setattr(config_loader, "ATTACK_PATH", attack_file)

    with pytest.raises(ValueError, match="master_switch"):
        config_loader.load_config()


def test_load_rules_config_rejects_string_enabled(tmp_path, monkeypatch):
    """Reject quoted booleans for binary flags in rules.yaml."""
    rules_file = tmp_path / "rules.yaml"
    rules_file.write_text(
        yaml.safe_dump(
            {
                "rules": {
                    "benford_first_digit": {
                        "rule_name": "benford_first_digit",
                        "threshold": 0.05,
                        "enabled": "true",
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(config_loader, "RULES_PATH", rules_file)

    with pytest.raises(ValueError, match="true/false"):
        config_loader.load_rules_config()
