"""Configura el sistema de logging desde un archivo de configuración.

English:
    Sets up application logging based on a config file.
"""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Iterable

from sentinel.utils.config_loader import load_config

SENSITIVE_ENV_KEYS = ("ARBITRUM_PRIVATE_KEY", "SECRET_ENCRYPTION_KEY")


class SensitiveDataFilter(logging.Filter):
    """Filtro seguro para redacción de secretos / Secure filter to redact secrets."""

    def __init__(self, sensitive_values: Iterable[str]) -> None:
        super().__init__()
        self._sensitive_values = [value for value in sensitive_values if value]

    def filter(self, record: logging.LogRecord) -> bool:
        message = str(record.getMessage())
        for value in self._sensitive_values:
            if value and value in message:
                # Seguridad: Evita exposición de datos sensibles / Security: Avoid exposure of sensitive data.
                message = message.replace(value, "[REDACTED]")
        record.msg = message
        record.args = ()
        return True


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

        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
        )
        sensitive_values = [os.getenv(key, "") for key in SENSITIVE_ENV_KEYS]
        redact_filter = SensitiveDataFilter(sensitive_values)

        file_handler = RotatingFileHandler(
            log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        file_handler.addFilter(redact_filter)

        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        stream_handler.addFilter(redact_filter)

        logging.basicConfig(
            level=log_level,
            handlers=[file_handler, stream_handler],
        )
        logging.info(
            "Logging inicializado - nivel: %s, archivo: %s",
            level_str,
            log_file,
        )
    except Exception as e:  # noqa: BLE001
        print(f"Error al configurar logging: {e}")
        logging.basicConfig(level=logging.INFO)
