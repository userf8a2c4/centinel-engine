"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `centinel_engine/config_loader.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - load_config

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `centinel_engine/config_loader.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - load_config

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

def _is_safe_env_name(env: str) -> bool:
    return env.replace("-", "").replace("_", "").isalnum()


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

    if not _is_safe_env_name(env):
        raise ValueError("Invalid environment name")

    config_root = Path("config").resolve()
    config_path = (config_root / env / file_name).resolve()
    if config_root not in config_path.parents:
        raise ValueError("Config path escapes config root")
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
