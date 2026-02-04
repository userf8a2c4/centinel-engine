"""Shared fixtures for resilience tests."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from centinel.downloader import load_retry_config


@pytest.fixture()
def retry_config_path(tmp_path: Path) -> Path:
    """Español: Crea un YAML temporal de reintentos para pruebas.

    English: Create a temporary retry YAML configuration for tests.
    """
    payload = {
        "default": {
            "max_attempts": 3,
            "backoff_base": 1.0,
            "backoff_multiplier": 2.0,
            "max_delay": 5.0,
            "jitter": {"min": 0.1, "max": 0.2},
        },
        "per_status": {
            "429": {
                "max_attempts": 3,
                "backoff_base": 1.0,
                "backoff_multiplier": 2.0,
                "max_delay": 5.0,
                "jitter": {"min": 0.1, "max": 0.2},
            },
            "503": {
                "max_attempts": 3,
                "backoff_base": 1.0,
                "backoff_multiplier": 2.0,
                "max_delay": 5.0,
                "jitter": {"min": 0.1, "max": 0.2},
            },
        },
        "per_exception": {
            "ReadTimeout": {
                "max_attempts": 2,
                "backoff_base": 1.0,
                "backoff_multiplier": 2.0,
                "max_delay": 5.0,
                "jitter": 0.1,
            }
        },
        "timeout_seconds": 1.0,
        "log_payload_bytes": 200,
        "failed_requests_path": str(tmp_path / "failed_requests.jsonl"),
    }
    config_path = tmp_path / "retry_config.yaml"
    config_path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    return config_path


@pytest.fixture()
def retry_config(retry_config_path: Path):
    """Español: Carga la configuración de reintentos desde YAML temporal.

    English: Load retry configuration from the temporary YAML file.
    """
    return load_retry_config(retry_config_path)


@pytest.fixture()
def sample_headers() -> dict[str, str]:
    """Español: Entrega headers persistentes para pruebas de reintento.

    English: Provide persistent headers for retry tests.
    """
    return {
        "User-Agent": "Centinel-Test/1.0",
        "Accept-Language": "es-HN,es;q=0.9,en;q=0.8",
        "Referer": "https://cne.hn/",
        "Accept": "application/json",
    }
