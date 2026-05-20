"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `src/monitoring/alerts.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - AlertConfig
  - AlertManager
  - get_default_alert_manager
  - dispatch_alert
  - resolve_latest_checkpoint_hash
  - _parse_retry_after
  - _env_int
  - _env_float
  - _sleep_backoff

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `src/monitoring/alerts.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - AlertConfig
  - AlertManager
  - get_default_alert_manager
  - dispatch_alert
  - resolve_latest_checkpoint_hash
  - _parse_retry_after
  - _env_int
  - _env_float
  - _sleep_backoff

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
"""

# Alerts Module
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

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)


ALERT_LEVELS = {
    "INFO": 10,
    "WARNING": 20,
    "CRITICAL": 30,
    "PANIC": 40,
}

DEFAULT_MIN_LEVEL = "WARNING"
DEFAULT_RATE_LIMIT_SECONDS = 1.0
DEFAULT_MAX_RETRIES = 4
DEFAULT_REQUEST_TIMEOUT = 10.0

@dataclass(frozen=True)
class AlertConfig:
    """Español: Clase AlertConfig del módulo src/monitoring/alerts.py.

    English: AlertConfig class defined in src/monitoring/alerts.py.
    """

    min_level: str = DEFAULT_MIN_LEVEL
    dashboard_url: str = ""
    rate_limit_seconds: float = DEFAULT_RATE_LIMIT_SECONDS
    max_retries: int = DEFAULT_MAX_RETRIES
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT
    hash_dir: str = "hashes"

    @classmethod
    def from_env(cls) -> "AlertConfig":
        """Español: Función from_env del módulo src/monitoring/alerts.py.

        English: Function from_env defined in src/monitoring/alerts.py.
        """
        return cls(
            min_level=os.getenv("ALERT_MIN_LEVEL", DEFAULT_MIN_LEVEL).strip().upper(),
            dashboard_url=os.getenv("CENTINEL_DASHBOARD_URL", "").strip(),
            rate_limit_seconds=_env_float("ALERT_RATE_LIMIT_SECONDS", DEFAULT_RATE_LIMIT_SECONDS),
            max_retries=_env_int("ALERT_MAX_RETRIES", DEFAULT_MAX_RETRIES),
            request_timeout=_env_float("ALERT_REQUEST_TIMEOUT", DEFAULT_REQUEST_TIMEOUT),
            hash_dir=os.getenv("CENTINEL_HASH_DIR", "hashes").strip() or "hashes",
        )


class AlertManager:
    """Gestor de alertas externas."""

    def __init__(self, config: AlertConfig) -> None:
        """Español: Función __init__ del módulo src/monitoring/alerts.py.

        English: Function __init__ defined in src/monitoring/alerts.py.
        """
        self._config = config
        self._lock = asyncio.Lock()
        self._last_sent_at = 0.0

    @property
    def config(self) -> AlertConfig:
        """Español: Función config del módulo src/monitoring/alerts.py.

        English: Function config defined in src/monitoring/alerts.py.
        """
        return self._config

    def is_configured(self) -> bool:
        """Español: Función is_configured del módulo src/monitoring/alerts.py.

        English: Function is_configured defined in src/monitoring/alerts.py.
        """
        return bool(self._config.dashboard_url)

    def should_send(self, level: str) -> bool:
        """Español: Función should_send del módulo src/monitoring/alerts.py.

        English: Function should_send defined in src/monitoring/alerts.py.
        """
        normalized = level.strip().upper()
        minimum = self._config.min_level or DEFAULT_MIN_LEVEL
        return ALERT_LEVELS.get(normalized, 0) >= ALERT_LEVELS.get(minimum, 20)

    async def send(self, level: str, message: str, context: dict | None = None) -> bool:
        """Español: Función asíncrona send del módulo src/monitoring/alerts.py.

        English: Async function send defined in src/monitoring/alerts.py.
        """
        normalized = level.strip().upper()
        if normalized not in ALERT_LEVELS:
            logger.warning("alert_level_invalid level=%s", level)
            return False
        if not self.is_configured():
            logger.info("alert_not_configured level=%s", normalized)
            return False
        if not self.should_send(normalized):
            logger.debug("alert_skipped level=%s min=%s", normalized, self._config.min_level)
            return False

        payload = self._build_payload(normalized, message, context or {})
        await self._rate_limit()

        logger.info("alert_sent level=%s", normalized)
        return True

    async def _rate_limit(self) -> None:
        """Español: Función asíncrona _rate_limit del módulo src/monitoring/alerts.py.

        English: Async function _rate_limit defined in src/monitoring/alerts.py.
        """
        async with self._lock:
            now = time.monotonic()
            delta = now - self._last_sent_at
            wait = self._config.rate_limit_seconds - delta
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_sent_at = time.monotonic()

    def _build_payload(self, level: str, message: str, context: dict[str, Any]) -> str:
        """Español: Función _build_payload del módulo src/monitoring/alerts.py.

        English: Function _build_payload defined in src/monitoring/alerts.py.
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        dashboard = context.get("dashboard_url") or self._config.dashboard_url
        checkpoint_hash = context.get("checkpoint_hash") or resolve_latest_checkpoint_hash(
            self._config.hash_dir
        )
        base = (
            f"[{level}] {timestamp} - {message}\n"
            f"Contexto: {json.dumps(context, indent=2, ensure_ascii=False)}"
        )
        if dashboard:
            base += f"\nDashboard: {dashboard}"
        if checkpoint_hash:
            base += f"\nCheckpoint hash: {checkpoint_hash}"
        return base


_DEFAULT_MANAGER: AlertManager | None = None


def get_default_alert_manager() -> AlertManager:
    """Español: Función get_default_alert_manager del módulo src/monitoring/alerts.py.

    English: Function get_default_alert_manager defined in src/monitoring/alerts.py.
    """
    global _DEFAULT_MANAGER
    if _DEFAULT_MANAGER is None:
        _DEFAULT_MANAGER = AlertManager(AlertConfig.from_env())
    return _DEFAULT_MANAGER


def dispatch_alert(level: str, message: str, context: dict | None = None) -> bool:
    """Envía una alerta desde contextos sin bucle async."""
    manager = get_default_alert_manager()
    if not manager.is_configured() or not manager.should_send(level):
        return False
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(manager.send(level, message, context=context))
        return True
    else:
        loop.create_task(manager.send(level, message, context=context))
        return True


def resolve_latest_checkpoint_hash(hash_dir: str) -> str | None:
    """Español: Función resolve_latest_checkpoint_hash del módulo src/monitoring/alerts.py.

    English: Function resolve_latest_checkpoint_hash defined in src/monitoring/alerts.py.
    """
    path = Path(hash_dir)
    if not path.exists():
        return None
    hash_files = sorted(
        path.glob("*.sha256"),
        key=lambda entry: entry.stat().st_mtime,
        reverse=True,
    )
    if not hash_files:
        return None
    content = hash_files[0].read_text(encoding="utf-8").strip()
    if not content:
        return None
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        return content.splitlines()[-1] if content else None
    if isinstance(payload, dict):
        return payload.get("chained_hash") or payload.get("hash")
    return content.splitlines()[-1] if content else None


def _parse_retry_after(response: httpx.Response) -> float:
    """Español: Función _parse_retry_after del módulo src/monitoring/alerts.py.

    English: Function _parse_retry_after defined in src/monitoring/alerts.py.
    """
    try:
        payload = response.json()
    except (ValueError, json.JSONDecodeError):
        return 2.0
    if isinstance(payload, dict):
        retry = payload.get("parameters", {}).get("retry_after")
        try:
            return float(retry)
        except (TypeError, ValueError):
            return 2.0
    return 2.0


def _env_int(name: str, default: int) -> int:
    """Español: Función _env_int del módulo src/monitoring/alerts.py.

    English: Function _env_int defined in src/monitoring/alerts.py.
    """
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning("alert_env_int_invalid name=%s value=%s", name, raw)
        return default


def _env_float(name: str, default: float) -> float:
    """Español: Función _env_float del módulo src/monitoring/alerts.py.

    English: Function _env_float defined in src/monitoring/alerts.py.
    """
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        logger.warning("alert_env_float_invalid name=%s value=%s", name, raw)
        return default


async def _sleep_backoff(attempt: int, base: float = 1.0) -> None:
    """Español: Función asíncrona _sleep_backoff del módulo src/monitoring/alerts.py.

    English: Async function _sleep_backoff defined in src/monitoring/alerts.py.
    """
    await asyncio.sleep(base * (2 ** (attempt - 1)))
