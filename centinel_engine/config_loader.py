"""YAML configuration loader with deterministic defaults and audit logging.

Bilingual: Cargador de configuración YAML con valores por defecto
 determinísticos y logging auditable.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

logger = logging.getLogger(__name__)


def load_config(path: str, defaults: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Load YAML config from disk with safe defaults and structured logs.

    Bilingual: Carga configuración YAML desde disco con defaults seguros y logs estructurados.

    Args:
        path: Relative or absolute YAML path.
        defaults: Optional fallback dictionary when file is missing/empty.

    Returns:
        Dictionary with loaded values merged on top of defaults.

    Raises:
        ValueError: If YAML payload is not a dictionary.
    """
    config_path = Path(path)
    base_defaults: Dict[str, Any] = dict(defaults or {})

    if not config_path.exists():
        logger.warning(
            "config_file_missing_using_defaults | archivo de configuracion ausente, usando defaults: path=%s",
            config_path,
        )
        return base_defaults

    raw_content = config_path.read_text(encoding="utf-8")
    loaded = yaml.safe_load(raw_content)

    if loaded is None:
        logger.info("config_file_empty | archivo de configuracion vacio: path=%s", config_path)
        return base_defaults

    if not isinstance(loaded, dict):
        raise ValueError(f"Invalid config format at {config_path}: expected mapping/dict")

    merged: Dict[str, Any] = {**base_defaults, **loaded}
    logger.info(
        "config_loaded | configuracion cargada: path=%s keys=%s",
        config_path,
        sorted(merged.keys()),
    )
    return merged
