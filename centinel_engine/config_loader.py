"""Central YAML configuration loader for Centinel Engine.

Bilingual: Cargador centralizado de configuración YAML para Centinel Engine.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


def load_config(file_name: str, env: str = "prod") -> dict[str, Any]:
    """Load a YAML config map from `config/<env>/<file_name>`.

    Bilingual: Carga un mapa YAML desde `config/<env>/<file_name>`.

    Args:
        file_name: Target YAML filename ending in `.yaml` or `.yml`.
        env: Environment folder under `config`.

    Returns:
        dict[str, Any]: Parsed configuration mapping.

    Raises:
        ValueError: If extension, path, YAML content, or schema is invalid.
    """
    if not file_name.endswith((".yaml", ".yml")):
        raise ValueError("Config file must end with .yaml or .yml")

    config_path = Path("config") / env / file_name
    try:
        payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Config file not found: {config_path}") from exc
    except OSError as exc:
        raise ValueError(f"Unable to read config file: {config_path}") from exc
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML in config file: {config_path}") from exc

    if payload is None:
        logger.info("config_loader_empty | archivo vacio: %s", config_path)
        return {}
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid config format in {config_path}: expected mapping/dict")
    return payload
