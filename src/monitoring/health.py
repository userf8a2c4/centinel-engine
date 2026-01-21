"""Healthchecks y monitoreo externo para C.E.N.T.I.N.E.L.

English:
    External healthchecks and monitoring helpers.
"""

from __future__ import annotations

import logging
import os
import threading
from typing import Optional

import httpx
from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)

_scheduler: Optional[BackgroundScheduler] = None
_health_state: Optional["HealthcheckState"] = None


class HealthcheckClient:
    """Cliente para enviar pings a Healthchecks.io."""

    def __init__(self, uuid: str, timeout_seconds: float = 5.0) -> None:
        self._uuid = uuid
        self._timeout = timeout_seconds
        self._base_url = f"https://hc-ping.com/{uuid}"

    def ping(self) -> None:
        """Envia ping de éxito."""
        try:
            httpx.get(self._base_url, timeout=self._timeout)
            logger.debug("healthchecks_ping_ok uuid=%s", self._uuid)
        except httpx.HTTPError as exc:
            logger.warning("healthchecks_ping_failed uuid=%s error=%s", self._uuid, exc)

    def ping_fail(self) -> None:
        """Envia ping de falla."""
        try:
            httpx.post(f"{self._base_url}/fail", timeout=self._timeout)
            logger.warning("healthchecks_ping_fail uuid=%s", self._uuid)
        except httpx.HTTPError as exc:
            logger.error(
                "healthchecks_ping_fail_error uuid=%s error=%s", self._uuid, exc
            )


class HealthcheckState:
    """Mantiene estado de fallos consecutivos para scraping."""

    def __init__(self, client: Optional[HealthcheckClient], threshold: int = 3) -> None:
        self._client = client
        self._threshold = threshold
        self._failures = 0
        self._lock = threading.Lock()

    @classmethod
    def from_env(cls) -> "HealthcheckState":
        uuid = os.getenv("HEALTHCHECKS_UUID", "").strip()
        client = HealthcheckClient(uuid) if uuid else None
        return cls(client=client, threshold=3)

    def record_success(self) -> None:
        with self._lock:
            self._failures = 0

    def record_failure(self, *, critical: bool = False) -> None:
        with self._lock:
            self._failures += 1
            send_fail = critical or self._failures > self._threshold

        if send_fail and self._client:
            self._client.ping_fail()


def get_health_state() -> HealthcheckState:
    """Devuelve un estado global de healthchecks."""
    global _health_state
    if _health_state is None:
        _health_state = HealthcheckState.from_env()
    return _health_state


def reset_health_state() -> None:
    """Resetea el estado global para pruebas."""
    global _health_state
    _health_state = None


def _build_health_router():
    from fastapi import APIRouter

    router = APIRouter()

    @router.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return router


def start_healthchecks_scheduler() -> None:
    """Inicia el scheduler para pings periódicos de Healthchecks."""
    global _scheduler
    if _scheduler is not None:
        return

    state = get_health_state()
    if state._client is None:
        logger.info("healthchecks_disabled reason=missing_uuid")
        return

    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(state._client.ping, "interval", minutes=5, id="healthchecks")
    scheduler.start()
    _scheduler = scheduler
    logger.info("healthchecks_scheduler_started interval=5m")


def register_healthchecks(app) -> None:
    """Registra /health e inicia scheduler si aplica."""
    app.include_router(_build_health_router())
    start_healthchecks_scheduler()
