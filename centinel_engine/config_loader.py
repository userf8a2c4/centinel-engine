# Config Loader Module
# AUTO-DOC-INDEX
#
# ES: Índice rápido
#   1) Propósito del módulo
#   2) Componentes principales
#   3) Puntos de extensión
#
# EN: Quick index
#   1) Module purpose
#   2) Main components
#   3) Extension points
#
# Secciones / Sections:
#   - Configuración / Configuration
#   - Lógica principal / Core logic
#   - Integraciones / Integrations

"""YAML configuration loader with deterministic defaults and audit logging.

Bilingual: Cargador centralizado de configuración YAML para entornos
Centinel determinísticos.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


def load_config(file_name: str, env: str = "prod") -> dict[str, Any]:
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
    logger.info(
        "config_loader_start | iniciando carga de configuracion: env=%s file_name=%s",
        env,
        file_name,
    )
    if not file_name.endswith((".yaml", ".yml")):
        logger.error(
            "config_loader_invalid_extension | extension invalida: file_name=%s",
            file_name,
        )
        raise ValueError("Config file must end with .yaml or .yml")

    config_path = Path(f"config/{env}/{file_name}")
    logger.debug(
        "config_loader_path_resolved | ruta de configuracion resuelta: %s",
        config_path,
    )

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

    logger.info(
        "config_loader_yaml_parse_start | iniciando parseo yaml: %s",
        config_path,
    )
    try:
        loaded: Any = yaml.load(raw_content, Loader=yaml.SafeLoader)
    except yaml.YAMLError as exc:
        logger.error(
            "config_yaml_invalid | yaml invalido en archivo: %s error=%s",
            config_path,
            exc,
        )
        raise ValueError(f"Invalid YAML in config file: {config_path}") from exc

    if loaded is None:
        logger.info(
            "config_loader_empty_payload | archivo yaml vacio, devolviendo dict vacio: %s",
            config_path,
        )
        return {}
    if not isinstance(loaded, dict):
        logger.error(
            "config_loader_invalid_payload | payload no es mapping: %s",
            config_path,
        )
        raise ValueError(f"Invalid config format in {config_path}: expected mapping/dict")

    logger.info(
        "config_loader_success | configuracion cargada correctamente: %s",
        config_path,
    )
    return loaded
