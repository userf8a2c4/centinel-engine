"""Centralized YAML configuration loader with defaults and logging.
Bilingual: Cargador centralizado de configuracion YAML con defaults y logging.

Provides a single entry point for loading any YAML configuration file used by
the Centinel engine, applying sensible defaults and emitting structured logs.

Provee un punto de entrada unico para cargar cualquier archivo de configuracion
YAML usado por el motor Centinel, aplicando defaults razonables y emitiendo logs
estructurados.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

logger = logging.getLogger(__name__)

# Base directory for configuration files / Directorio base para archivos de configuracion
_CONFIG_BASE_DIR: Path = Path(
    os.getenv("CENTINEL_CONFIG_DIR", "config/prod")
)


def load_config(
    path: str,
    *,
    defaults: Optional[Dict[str, Any]] = None,
    required: bool = False,
) -> Dict[str, Any]:
    """Load a YAML configuration file and merge with optional defaults.
    Bilingual: Carga un archivo de configuracion YAML y lo fusiona con defaults opcionales.

    Resolves the path relative to the project root. If the file does not exist
    and ``required`` is False, returns the defaults dict (or empty dict).
    Always uses ``yaml.safe_load`` to prevent arbitrary code execution.

    Args:
        path: Relative or absolute path to the YAML file
              (e.g. ``"config/prod/proxies.yaml"``).
        defaults: Default values to merge under the loaded config.
                  Loaded values take precedence over defaults.
        required: If True, raise FileNotFoundError when file is missing.

    Returns:
        Merged configuration dictionary. Never returns None.

    Raises:
        FileNotFoundError: When ``required=True`` and the file does not exist.
        ValueError: When the YAML file contains syntax errors or is not a mapping.
    """
    defaults = defaults or {}
    resolved: Path = Path(path)

    # Try absolute path first, then relative to project root /
    # Intentar ruta absoluta primero, luego relativa a raiz del proyecto
    if not resolved.is_absolute():
        resolved = Path.cwd() / resolved

    if not resolved.exists():
        if required:
            raise FileNotFoundError(
                f"Configuration file not found / Archivo de configuracion no encontrado: {resolved}"
            )
        logger.info(
            "Config file not found, using defaults / "
            "Archivo de config no encontrado, usando defaults: %s",
            resolved,
        )
        return dict(defaults)

    try:
        raw_content = resolved.read_text(encoding="utf-8")
        payload = yaml.safe_load(raw_content)
    except yaml.YAMLError as exc:
        raise ValueError(
            f"YAML syntax error in / Error de sintaxis YAML en {resolved}: {exc}"
        ) from exc

    if payload is None:
        # Empty YAML file / Archivo YAML vacio
        logger.warning(
            "Config file is empty, using defaults / "
            "Archivo de config vacio, usando defaults: %s",
            resolved,
        )
        return dict(defaults)

    if not isinstance(payload, dict):
        raise ValueError(
            f"Config file must be a YAML mapping / "
            f"Archivo de config debe ser un mapa YAML: {resolved}"
        )

    # Merge: defaults as base, loaded values override /
    # Fusion: defaults como base, valores cargados sobreescriben
    merged: Dict[str, Any] = {**defaults, **payload}

    logger.info(
        "Configuration loaded successfully / Configuracion cargada exitosamente: %s (%d keys)",
        resolved,
        len(merged),
    )
    return merged


def get_config_path(filename: str) -> Path:
    """Resolve a configuration filename to its full path under the config base directory.
    Bilingual: Resuelve un nombre de archivo de configuracion a su ruta completa bajo el directorio base.

    Args:
        filename: Configuration filename (e.g. ``"proxies.yaml"``).

    Returns:
        Full resolved Path to the configuration file.
    """
    return Path.cwd() / _CONFIG_BASE_DIR / filename


def load_prod_config(filename: str, *, defaults: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Convenience loader for config/prod/ files.
    Bilingual: Cargador de conveniencia para archivos en config/prod/.

    Args:
        filename: File name within config/prod/ (e.g. ``"proxies.yaml"``).
        defaults: Optional default values.

    Returns:
        Merged configuration dictionary.
    """
    path = get_config_path(filename)
    return load_config(str(path), defaults=defaults)
