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
    limit: int
    window_seconds: int


class RateLimiter:
    """Rate limiter simple basado en ventana deslizante en memoria."""

    def __init__(self, config: RateLimitConfig) -> None:
        self._config = config
        self._lock = threading.Lock()
        self._buckets: DefaultDict[str, Deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
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
    return RateLimiter(RateLimitConfig(limit=limit, window_seconds=window_seconds))
