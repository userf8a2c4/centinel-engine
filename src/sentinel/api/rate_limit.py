"""Rate limiting in-memory para la API pública."""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Deque, DefaultDict


class RateLimitExceeded(Exception):
    """Se excedió el límite de requests."""


@dataclass(frozen=True)
class RateLimitConfig:
    """Configura límites y ventana temporal para el rate limiter.

    Guarda el máximo de solicitudes permitidas y la duración de la ventana
    deslizante en segundos.

    English:
        Configure limits and time window for the rate limiter.

        Stores the maximum allowed requests and the sliding window duration in
        seconds.
    """
    limit: int
    window_seconds: int


class RateLimiter:
    """Rate limiter simple basado en ventana deslizante en memoria."""

    def __init__(self, config: RateLimitConfig) -> None:
        """Inicializa el rate limiter con configuración inmutable.

        Prepara el lock y los buckets por clave para registro de marcas de tiempo.

        English:
            Initialize the rate limiter with immutable configuration.

            Prepares the lock and per-key buckets for timestamp tracking.
        """
        self._config = config
        self._lock = threading.Lock()
        self._buckets: DefaultDict[str, Deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        """Evalúa si una clave puede realizar una nueva solicitud.

        Limpia marcas antiguas fuera de la ventana y decide si se supera el
        límite configurado.

        English:
            Evaluate whether a key can perform a new request.

            Removes expired timestamps and decides if the configured limit is
            exceeded.
        """
        now = time.monotonic()
        with self._lock:
            bucket = self._buckets[key]
            while bucket and now - bucket[0] > self._config.window_seconds:
                bucket.popleft()
            if len(bucket) >= self._config.limit:
                return False
            bucket.append(now)
            return True


def rate_limit_dependency(limit: int, window_seconds: int) -> RateLimiter:
    """Crea un RateLimiter para inyección de dependencias en FastAPI.

    English:
        Create a RateLimiter for FastAPI dependency injection.
    """
    return RateLimiter(RateLimitConfig(limit=limit, window_seconds=window_seconds))
