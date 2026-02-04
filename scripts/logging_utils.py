"""Utilidades de logging estructurado para scripts de Centinel.

Structured logging helpers for Centinel scripts.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Iterable
import yaml

SENSITIVE_FIELDS = {
    "votos",
    "votes",
    "total_votes",
    "registered_voters",
    "valid_votes",
    "null_votes",
    "blank_votes",
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
    "candidato",
    "candidate",
    "nombre",
    "name",
}

SUSPICIOUS_STRING_PATTERNS = (
    re.compile(r"0x[a-fA-F0-9]{16,}"),
    re.compile(r"[A-Za-z0-9+/]{24,}={0,2}"),
)
LARGE_NUMBER_PATTERN = re.compile(r"(?<![T\d:-])\d{4,}(?![\d:-])")


def _hash_value(value: Any) -> str:
    """/** Hashea valores sensibles para trazabilidad. / Hash sensitive values for traceability. **/"""
    try:
        encoded = json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8")
    except TypeError:
        encoded = str(value).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _is_suspicious_string(value: str) -> bool:
    """/** Detecta patrones sospechosos en strings. / Detect suspicious string patterns. **/"""
    return any(pattern.search(value) for pattern in SUSPICIOUS_STRING_PATTERNS)


def _scrub_value(value: Any) -> Any:
    """/** Redacta valores sensibles y números grandes. / Redact sensitive values and large numbers. **/"""
    if isinstance(value, (int, float)):
        if abs(value) >= 1000:
            return {"hash": _hash_value(value)}
        return value
    if isinstance(value, str) and _is_suspicious_string(value):
        return f"hash:{_hash_value(value)}"
    return value


def _scrub_fields(fields: dict[str, Any]) -> dict[str, Any]:
    """/** Sanitiza campos sensibles en eventos. / Sanitize sensitive fields in events. **/"""
    sanitized: dict[str, Any] = {}
    for key, value in fields.items():
        normalized_key = key.lower()
        if normalized_key in SENSITIVE_FIELDS or any(
            token in normalized_key for token in ("secret", "key", "token")
        ):
            # Seguridad: evita exposición de datos sensibles. / Security: avoid exposure of sensitive data.
            sanitized[key] = {"hash": _hash_value(value)}
        else:
            sanitized[key] = _scrub_value(value)
    return sanitized


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


class SensitiveDataFilter(logging.Filter):
    """/** Filtro seguro para redacción de secretos. / Secure filter to redact secrets. **/"""

    def __init__(self, sensitive_values: Iterable[str]) -> None:
        """Español: Función __init__ del módulo scripts/logging_utils.py.

        English: Function __init__ defined in scripts/logging_utils.py.
        """
        super().__init__()
        self._sensitive_values = [value for value in sensitive_values if value]

    def filter(self, record: logging.LogRecord) -> bool:
        """Español: Función filter del módulo scripts/logging_utils.py.

        English: Function filter defined in scripts/logging_utils.py.
        """
        message = str(record.getMessage())
        for value in self._sensitive_values:
            if value and value in message:
                # Seguridad: evita exposición de datos sensibles. / Security: avoid exposure of sensitive data.
                message = message.replace(value, "[REDACTED]")
        record.msg = message
        record.args = ()
        return True


class SanitizingFilter(logging.Filter):
    """/** Filtro para scrub de números grandes y strings sospechosas. / Filter to scrub large numbers and suspicious strings. **/"""

    def filter(self, record: logging.LogRecord) -> bool:
        """Español: Función filter del módulo scripts/logging_utils.py.

        English: Function filter defined in scripts/logging_utils.py.
        """
        message = str(record.getMessage())
        message = LARGE_NUMBER_PATTERN.sub("[REDACTED_NUM]", message)
        for pattern in SUSPICIOUS_STRING_PATTERNS:
            message = pattern.sub("[REDACTED_STR]", message)
        record.msg = message
        record.args = ()
        return True


def _load_security_settings() -> dict[str, Any]:
    """/** Carga configuración de seguridad desde rules.yaml. / Load security settings from rules.yaml. **/"""
    rules_path = Path("command_center") / "rules.yaml"
    if not rules_path.exists():
        return {}
    try:
        parsed = yaml.safe_load(rules_path.read_text(encoding="utf-8")) or {}
        if isinstance(parsed, dict):
            return (
                parsed.get("security", {})
                if isinstance(parsed.get("security"), dict)
                else {}
            )
    except Exception:
        return {}
    return {}


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
    sensitive_values = [os.getenv(key, "") for key in SENSITIVE_ENV_KEYS]
    redact_filter = SensitiveDataFilter(sensitive_values)
    security_settings = _load_security_settings()
    log_sensitive = bool(security_settings.get("log_sensitive", False))

    file_handler = RotatingFileHandler(
        log_path, maxBytes=10_000_000, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    file_handler.addFilter(redact_filter)
    if not log_sensitive:
        file_handler.addFilter(SanitizingFilter())

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(log_level)
    stream_handler.setFormatter(formatter)
    stream_handler.addFilter(redact_filter)
    if not log_sensitive:
        stream_handler.addFilter(SanitizingFilter())

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
    safe_fields = _scrub_fields(fields)
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": logging.getLevelName(level),
        "logger": logger.name,
        "event": event,
        **safe_fields,
    }
    # Seguridad: evitar registrar datos sensibles en claro. / Security: avoid logging sensitive values in clear text.
    sanitized = _redact_sensitive_fields(payload)
    logger.log(level, json.dumps(sanitized, ensure_ascii=False))
