"""Configuration loader for the abstraction layer."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml

DEFAULT_CONFIG_PATH = Path("config") / "default.yaml"
COUNTRIES_PATH = Path("config") / "countries"


def load_config(country_code: str = "HN") -> Dict[str, Any]:
    """Load and merge default + country config.

    Args:
        country_code: ISO code for the country config to load.

    Returns:
        Merged configuration dictionary.
    """
    with DEFAULT_CONFIG_PATH.open("r", encoding="utf-8") as handle:
        base = yaml.safe_load(handle) or {}

    country_path = COUNTRIES_PATH / f"{country_code.lower()}.yaml"
    if not country_path.exists():
        country_path = COUNTRIES_PATH / f"{country_code.upper()}.yaml"
    if country_path.exists():
        with country_path.open("r", encoding="utf-8") as handle:
            overlay = yaml.safe_load(handle) or {}
    else:
        overlay = {}

    return _deep_merge(base, overlay)


def _deep_merge(base: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
    """Deep-merge nested dictionaries."""
    merged = dict(base)
    for key, value in overlay.items():
        if (
            key in merged
            and isinstance(merged[key], dict)
            and isinstance(value, dict)
        ):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged
