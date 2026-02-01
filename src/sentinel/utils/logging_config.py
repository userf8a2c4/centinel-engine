"""Configura el sistema de logging desde un archivo de configuración.

English:
    Sets up application logging based on a config file.
"""

from __future__ import annotations

import logging
import logging.handlers

from sentinel.utils.config_loader import load_config

SENSITIVE_KEYS = {"votes", "votos", "payload", "personal_data", "dni", "cedula"}


def _redact_sensitive_fields(data: dict) -> dict:
    """/** Redacta claves sensibles en logs. / Redact sensitive keys in logs. **/"""
    sanitized: dict[str, object] = {}
    for key, value in data.items():
        if str(key).lower() in SENSITIVE_KEYS:
            sanitized[key] = "[REDACTED]"
        else:
            sanitized[key] = value
    return sanitized


class SensitiveLogFilter(logging.Filter):
    """/** Filtro de logging para datos sensibles. / Logging filter for sensitive data. **/"""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.args, dict):
            record.args = _redact_sensitive_fields(record.args)
        return True


def setup_logging() -> None:
    """/** Configura el logging global desde config/config.yaml. / Sets up global logging from config/config.yaml. **/"""
    try:
        config = load_config()
        log_config = config.get("logging", {})
        level_str = str(log_config.get("level", "INFO")).upper()
        log_file = log_config.get("file", "centinel.log")
        log_level = getattr(logging, level_str, logging.INFO)

        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=5_000_000, backupCount=5, encoding="utf-8"
        )
        file_handler.addFilter(SensitiveLogFilter())
        stream_handler = logging.StreamHandler()
        stream_handler.addFilter(SensitiveLogFilter())

        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
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
