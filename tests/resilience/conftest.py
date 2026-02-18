"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `tests/resilience/conftest.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - mock_responses
  - retry_config_path
  - retry_config
  - watchdog_config_path
  - proxies_config_path
  - sample_headers

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `tests/resilience/conftest.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - mock_responses
  - retry_config_path
  - retry_config
  - watchdog_config_path
  - proxies_config_path
  - sample_headers

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import responses
import yaml

from centinel.downloader import load_retry_config


@pytest.fixture()
def mock_responses():
    """Español: Provee un mock de HTTP con la librería responses, sin red real.

    English: Provide an HTTP mock using the responses library with no real network.
    """
    with responses.RequestsMock(assert_all_requests_are_fired=False) as mock:
        yield mock


@pytest.fixture()
def retry_config_path(tmp_path: Path) -> Path:
    """Español: Crea un YAML temporal de reintentos para pruebas resilientes.

    English: Create a temporary retry YAML configuration for resilience tests.
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
            },
            "JSONDecodeError": {
                "max_attempts": 3,
                "backoff_base": 1.0,
                "backoff_multiplier": 2.0,
                "max_delay": 5.0,
                "jitter": 0.1,
            },
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
def watchdog_config_path(tmp_path: Path) -> Path:
    """Español: Genera un watchdog.yaml temporal para escenarios controlados.

    English: Generate a temporary watchdog.yaml for controlled scenarios.
    """
    payload = {
        "check_interval_minutes": 3,
        "max_inactivity_minutes": 30,
        "heartbeat_timeout": 1,
        "failure_grace_minutes": 2,
        "action_cooldown_minutes": 5,
        "data_dir": str(tmp_path / "data"),
        "heartbeat_path": str(tmp_path / "data" / "heartbeat.json"),
        "state_path": str(tmp_path / "data" / "watchdog_state.json"),
        "log_path": str(tmp_path / "logs" / "centinel.log"),
        "lock_files": [str(tmp_path / "data" / "temp" / "pipeline.lock")],
    }
    config_path = tmp_path / "watchdog.yaml"
    config_path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    return config_path


@pytest.fixture()
def proxies_config_path(tmp_path: Path) -> Path:
    """Español: Construye un proxies.yaml temporal para pruebas de rotación.

    English: Build a temporary proxies.yaml for rotation tests.
    """
    payload = {
        "mode": "rotate",
        "rotation_strategy": "round_robin",
        "rotation_every_n": 1,
        "proxy_timeout_seconds": 5.0,
        "test_url": "https://cne.hn/health",
        "proxies": [
            "http://proxy-1.local:8080",
            "http://proxy-2.local:8080",
        ],
    }
    config_path = tmp_path / "proxies.yaml"
    config_path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    return config_path


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
