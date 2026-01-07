import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def configure_logging(logger_name: str, log_file: str | None = None, level: int | None = None) -> logging.Logger:
    log_path = log_file or os.getenv("LOG_FILE", "logs/sentinel.jsonl")
    log_level = level or getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO)

    logger = logging.getLogger(logger_name)
    logger.setLevel(log_level)
    logger.propagate = False

    if logger.handlers:
        return logger

    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter("%(message)s")

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(log_level)
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    return logger


def log_event(logger: logging.Logger, level: int, event: str, **fields: Any) -> None:
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": logging.getLevelName(level),
        "logger": logger.name,
        "event": event,
        **fields,
    }
    logger.log(level, json.dumps(payload, ensure_ascii=False))
