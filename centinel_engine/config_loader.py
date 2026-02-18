"""Centralized YAML configuration loader for deterministic Centinel environments.

Bilingual: Cargador centralizado de configuración YAML para entornos
Centinel determinísticos.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict

import yaml

logger = logging.getLogger(__name__)


def load_config(file_name: str, env: str = "prod") -> Dict[str, Any]:
    """Load a YAML config file from ``config/<env>/``.

    Bilingual: Carga un archivo YAML desde ``config/<env>/``.

    Args:
        file_name: YAML file name with ``.yaml`` or ``.yml`` extension.
        env: Environment folder under ``config`` (for example: ``prod`` or ``dev``).

    Returns:
        Parsed YAML mapping as a dictionary.

    Raises:
        ValueError: If extension is invalid, file is missing, YAML is invalid,
            or payload is not a mapping.
    """
    if not file_name.endswith((".yaml", ".yml")):
        raise ValueError("Config file must end with .yaml or .yml")

    config_path = Path("config") / env / file_name

    try:
        raw_content = config_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        logger.error(
            "config_not_found | archivo de configuracion no encontrado: %s",
            config_path,
        )
        raise ValueError(f"Config file not found: {config_path}") from exc
    except OSError as exc:
        logger.error(
            "config_read_error | error leyendo archivo de configuracion: %s error=%s",
            config_path,
            exc,
        )
        raise ValueError(f"Unable to read config file: {config_path}") from exc

    try:
        loaded: Any = yaml.safe_load(raw_content)
    except yaml.YAMLError as exc:
        logger.error(
            "config_yaml_invalid | yaml invalido en archivo: %s error=%s",
            config_path,
            exc,
        )
        raise ValueError(f"Invalid YAML in config file: {config_path}") from exc

    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise ValueError(f"Invalid config format in {config_path}: expected mapping/dict")

    return loaded
