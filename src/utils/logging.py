"""Logging helpers for the abstraction layer."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional


def configure_logging(level: str = "INFO", logfile: Optional[str] = None) -> None:
    """Configure a standard logging format.

    Args:
        level: Logging level string.
        logfile: Optional file path for logs.
    """
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if logfile:
        log_path = Path(logfile)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_path, encoding="utf-8"))

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=handlers,
    )
