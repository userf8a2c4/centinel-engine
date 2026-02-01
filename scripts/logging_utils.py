"""Utilidades de logging estructurado para scripts de Centinel.

Structured logging helpers for Centinel scripts.
"""

import json
import logging
import logging.handlers
import os
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SENSITIVE_KEYS = {
    "votes",
    "votos",
    "total_votes",
    "votos_totales",
    "payload",
    "raw",
    "raw_payload",
    "personal_data",
    "datos_personales",
    "dni",
    "documento",
    "cedula",
    "acta",
    "actas",
    "resultados",
}


def _hash_value(value: Any) -> str:
    """/** Hashea valores sensibles para trazabilidad. / Hash sensitive values for traceability. **/"""
    try:
        encoded = json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8")
    except TypeError:
        encoded = str(value).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _redact_sensitive_fields(payload: Any) -> Any:
    """/** Redacta claves sensibles en estructuras anidadas. / Redact sensitive keys in nested structures. **/"""
    if isinstance(payload, dict):
        sanitized: dict[str, Any] = {}
        for key, value in payload.items():
            if str(key).lower() in SENSITIVE_KEYS:
                sanitized[key] = f"hash:{_hash_value(value)}"
            else:
                sanitized[key] = _redact_sensitive_fields(value)
        return sanitized
    if isinstance(payload, list):
        return [_redact_sensitive_fields(item) for item in payload]
    return payload


def configure_logging(
    logger_name: str, log_file: str | None = None, level: int | None = None
) -> logging.Logger:
    """/** Configura logging seguro con rotación y salida JSONL. / Configure secure logging with rotation and JSONL output. **/"""
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

    file_handler = logging.handlers.RotatingFileHandler(
        log_path, maxBytes=5_000_000, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(log_level)
    stream_handler.setFormatter(formatter)

    # Seguridad: usar handlers rotativos para evitar leaks en archivos grandes. / Security: rotate logs to avoid large leaks.
    logging.basicConfig(
        level=log_level,
        handlers=[file_handler, stream_handler],
        format="%(message)s",
        force=True,
    )
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    return logger


def log_event(logger: logging.Logger, level: int, event: str, **fields: Any) -> None:
    """/** Registra un evento JSON con datos saneados. / Log a JSON event with sanitized data. **/"""
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": logging.getLevelName(level),
        "logger": logger.name,
        "event": event,
        **fields,
    }
    # Seguridad: evitar registrar datos sensibles en claro. / Security: avoid logging sensitive values in clear text.
    sanitized = _redact_sensitive_fields(payload)
    logger.log(level, json.dumps(sanitized, ensure_ascii=False))
