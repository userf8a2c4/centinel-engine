#!/usr/bin/env python3
"""Bootstrap initial configuration files for Centinel.

This helper copies template files into command_center if they do not exist and
validates minimal configuration requirements.
"""

import argparse
import logging
import shutil
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

COMMAND_CENTER_DIR = Path("command_center")
CONFIG_TEMPLATE_PATH = COMMAND_CENTER_DIR / "config.yaml.example"
CONFIG_PATH = COMMAND_CENTER_DIR / "config.yaml"
ENV_TEMPLATE_PATH = COMMAND_CENTER_DIR / ".env.example"
ENV_PATH = COMMAND_CENTER_DIR / ".env"

REQUIRED_CONFIG_KEYS = ("base_url", "endpoints")


def _copy_if_missing(source_path: Path, destination_path: Path) -> bool:
    if destination_path.exists():
        logger.info("File already exists: %s", destination_path)
        return False
    if not source_path.exists():
        raise FileNotFoundError(f"Missing template: {source_path}")
    shutil.copyfile(source_path, destination_path)
    logger.info("Created: %s", destination_path)
    return True


def _load_config(config_path: Path) -> dict[str, Any]:
    if not config_path.exists():
        logger.warning("Config file not found: %s", config_path)
        return {}
    return yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}


def _validate_config(config: dict[str, Any]) -> list[str]:
    missing_keys = [key for key in REQUIRED_CONFIG_KEYS if key not in config]
    return missing_keys


def bootstrap_config(force: bool = False) -> int:
    COMMAND_CENTER_DIR.mkdir(parents=True, exist_ok=True)

    created_any = False
    if force and CONFIG_PATH.exists():
        CONFIG_PATH.unlink()
    if force and ENV_PATH.exists():
        ENV_PATH.unlink()

    created_any |= _copy_if_missing(CONFIG_TEMPLATE_PATH, CONFIG_PATH)
    created_any |= _copy_if_missing(ENV_TEMPLATE_PATH, ENV_PATH)

    config = _load_config(CONFIG_PATH)
    missing_keys = _validate_config(config)
    if missing_keys:
        logger.warning("Missing required config keys: %s", ", ".join(missing_keys))
        return 2

    if created_any:
        logger.info("Bootstrap complete. Review command_center/config.yaml.")
    else:
        logger.info("Bootstrap complete. No changes required.")
    return 0


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(description="Bootstrap Centinel configuration")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing config/env files",
    )
    args = parser.parse_args()
    return bootstrap_config(force=args.force)


if __name__ == "__main__":
    raise SystemExit(main())
