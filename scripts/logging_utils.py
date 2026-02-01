"""Utilidades de logging estructurado para scripts de Centinel.

Structured logging helpers for Centinel scripts.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Iterable

SENSITIVE_FIELDS = {
    "votos",
    "votes",
    "nombre",
    "name",
    "candidato",
    "candidate",
    "partido",
    "party",
    "private_key",
    "secret",
}
SENSITIVE_ENV_KEYS = ("ARBITRUM_PRIVATE_KEY", "SECRET_ENCRYPTION_KEY")


def _hash_value(value: Any) -> str:
    """Función segura para hashear valores sensibles / Secure function for hashing sensitive values."""
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def _scrub_fields(fields: dict[str, Any]) -> dict[str, Any]:
    """Función segura para sanitizar campos sensibles / Secure function for sanitizing sensitive fields."""
    sanitized: dict[str, Any] = {}
    for key, value in fields.items():
        normalized_key = key.lower()
        if normalized_key in SENSITIVE_FIELDS or any(
            token in normalized_key for token in ("secret", "key", "token")
        ):
            # Seguridad: Evita exposición de datos sensibles / Security: Avoid exposure of sensitive data.
            sanitized[key] = {"hash": _hash_value(value)}
        else:
            sanitized[key] = value
    return sanitized


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


def configure_logging(
    logger_name: str, log_file: str | None = None, level: int | None = None
) -> logging.Logger:
    """Configura un logger con salida a archivo JSONL y consola.

    Configure a logger with JSONL file output and console output.
    """
    log_path = log_file or os.getenv("LOG_FILE", "logs/centinel.jsonl")
    log_level = level or getattr(
        logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO
    )

    logger = logging.getLogger(logger_name)
    logger.setLevel(log_level)
    logger.propagate = False

    if logger.handlers:
        return logger

    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter("%(message)s")
    sensitive_values = [os.getenv(key, "") for key in SENSITIVE_ENV_KEYS]
    redact_filter = SensitiveDataFilter(sensitive_values)

    file_handler = RotatingFileHandler(
        log_path, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    file_handler.addFilter(redact_filter)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(log_level)
    stream_handler.setFormatter(formatter)
    stream_handler.addFilter(redact_filter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    return logger


def log_event(logger: logging.Logger, level: int, event: str, **fields: Any) -> None:
    """Registra un evento estructurado con un payload JSON.

    Log a structured event with a JSON payload.
    """
    safe_fields = _scrub_fields(fields)
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": logging.getLevelName(level),
        "logger": logger.name,
        "event": event,
        **safe_fields,
    }
    logger.log(level, json.dumps(payload, ensure_ascii=False))
