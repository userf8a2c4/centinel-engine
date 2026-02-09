"""Carga y valida la configuración centralizada de C.E.N.T.I.N.E.L.

English:
    Loads and validates the centralized C.E.N.T.I.N.E.L. configuration.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

CONFIG_PATH = Path("config") / "config.yaml"

REQUIRED_TOP_LEVEL_KEYS = [
    "master_switch",
    "base_url",
    "endpoints",
    "timeout",
    "retries",
    "headers",
    "use_playwright",
    "playwright_stealth",
    "playwright_user_agent",
    "playwright_viewport",
    "playwright_locale",
    "playwright_timezone",
    "backoff_base_seconds",
    "backoff_max_seconds",
    "candidate_count",
    "required_keys",
    "field_map",
    "sources",
    "logging",
    "blockchain",
    "alerts",
    "arbitrum",
    "rules",
]

REQUIRED_NESTED_KEYS = {
    "logging": ["level", "file"],
    "blockchain": ["enabled", "network", "private_key"],
    "alerts": ["critical_anomaly_types", "telegram", "x"],
    "alerts.telegram": ["enabled", "bot_token", "chat_id", "template"],
    "alerts.x": [
        "enabled",
        "api_key",
        "api_secret",
        "access_token",
        "access_token_secret",
    ],
    "arbitrum": [
        "enabled",
        "rpc_url",
        "private_key",
        "contract_address",
        "interval_minutes",
        "batch_size",
    ],
    "rules": ["global_enabled"],
}


def load_config() -> dict[str, Any]:
    """Carga la configuración desde config/config.yaml y valida sus claves.

    Raises:
        FileNotFoundError: Si config/config.yaml no existe.
        KeyError: Si falta alguna clave requerida en la configuración.
        yaml.YAMLError: Si hay errores de sintaxis en el YAML.

    English:
        Load configuration from config/config.yaml and validate required keys.

    Raises:
        FileNotFoundError: If config/config.yaml does not exist.
        KeyError: If any required key is missing from configuration.
        yaml.YAMLError: When YAML syntax errors are detected.
    """
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            "Falta config/config.yaml. Centraliza toda la configuración en esa ruta."
        )

    with CONFIG_PATH.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}

    missing_keys: list[str] = []
    for key in REQUIRED_TOP_LEVEL_KEYS:
        if key not in config:
            missing_keys.append(key)

    for section_key, section_keys in REQUIRED_NESTED_KEYS.items():
        section = config
        for part in section_key.split("."):
            if not isinstance(section, dict) or part not in section:
                missing_keys.append(section_key)
                section = None
                break
            section = section[part]
        if section is None:
            continue
        for nested_key in section_keys:
            if not isinstance(section, dict) or nested_key not in section:
                missing_keys.append(f"{section_key}.{nested_key}")

    if missing_keys:
        missing = ", ".join(sorted(set(missing_keys)))
        raise KeyError(
            "Faltan claves requeridas en config/config.yaml: "
            f"{missing}. Revisa la configuración centralizada."
        )

    logging.getLogger(__name__).debug(
        "Configuración cargada desde %s", CONFIG_PATH.as_posix()
    )
    return config
