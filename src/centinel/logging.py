"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `src/centinel/logging.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - setup_logging
  - bind_context

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `src/centinel/logging.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - setup_logging
  - bind_context

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
"""

# Logging Module
# AUTO-DOC-INDEX
#
# ES: Índice rápido
#   1) Propósito del módulo
#   2) Componentes principales
#   3) Puntos de extensión
#
# EN: Quick index
#   1) Module purpose
#   2) Main components
#   3) Extension points
#
# Secciones / Sections:
#   - Configuración / Configuration
#   - Lógica principal / Core logic
#   - Integraciones / Integrations



from __future__ import annotations

import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Any, Optional

import structlog


def setup_logging(log_level: str, storage_path: Path) -> structlog.BoundLogger:
    """Configura structlog y handlers de consola/archivo.

    English: Configure structlog and console/file handlers.
    """
    log_dir = storage_path / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    file_handler = TimedRotatingFileHandler(
        log_dir / "centinel.log",
        when="midnight",
        backupCount=30,
        encoding="utf-8",
    )
    console_handler = logging.StreamHandler()

    logging.basicConfig(
        level=log_level.upper(),
        handlers=[file_handler, console_handler],
        format="%(message)s",
    )

    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level.upper()),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    return structlog.get_logger()


def bind_context(
    logger: structlog.BoundLogger,
    snapshot_id: Optional[str] = None,
    source_url: Optional[str] = None,
    hash_value: Optional[str] = None,
) -> structlog.BoundLogger:
    """Adjunta contexto estándar al logger.

    English: Bind standard context to the logger.
    """
    context: dict[str, Any] = {}
    if snapshot_id:
        context["snapshot_id"] = snapshot_id
    if source_url:
        context["source_url"] = source_url
    if hash_value:
        context["hash"] = hash_value
    return logger.bind(**context)
