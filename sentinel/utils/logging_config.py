import logging
from pathlib import Path

import yaml


def setup_logging(config_path: str = "config.yaml") -> None:
    """Configura logging global desde config.yaml."""
    try:
        config_file = Path(config_path)
        with config_file.open("r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

        log_config = config.get("logging", {})
        level_str = str(log_config.get("level", "INFO")).upper()
        log_file = log_config.get("file", "sentinel.log")
        log_level = getattr(logging, level_str, logging.INFO)

        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
            handlers=[
                logging.FileHandler(log_file, encoding="utf-8"),
                logging.StreamHandler(),
            ],
        )
        logging.info(
            "Logging inicializado - nivel: %s, archivo: %s",
            level_str,
            log_file,
        )
    except Exception as e:  # noqa: BLE001
        print(f"Error al configurar logging: {e}")
        logging.basicConfig(level=logging.INFO)
