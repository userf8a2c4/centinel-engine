"""Configura el sistema de logging desde un archivo de configuración.

English:
    Sets up application logging based on a config file.
"""

import logging

from sentinel.utils.config_loader import load_config


def setup_logging() -> None:
    """Configura el logging global desde config/config.yaml.

    English:
        Sets up global logging from config/config.yaml.
    """
    try:
        config = load_config()
        log_config = config.get("logging", {})
        level_str = str(log_config.get("level", "INFO")).upper()
        log_file = log_config.get("file", "centinel.log")
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
