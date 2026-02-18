"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `centinel_engine/rate_limiter.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - TokenBucketRateLimiter
  - _load_rate_limiter_config
  - get_rate_limiter
  - reset_rate_limiter

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `centinel_engine/rate_limiter.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - TokenBucketRateLimiter
  - _load_rate_limiter_config
  - get_rate_limiter
  - reset_rate_limiter

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Optional

from centinel_engine.config_loader import load_config

logger = logging.getLogger(__name__)

DEFAULT_RATE_INTERVAL: float = 10.0
DEFAULT_BURST: int = 3
DEFAULT_MIN_INTERVAL: float = 8.0
DEFAULT_MAX_INTERVAL: float = 12.0


class TokenBucketRateLimiter:
    """Throttle requests using a thread-safe token bucket.

    Bilingual: Limita solicitudes usando un token-bucket thread-safe.

    Args:
        rate_interval: Seconds to refill one token.
        burst: Maximum token capacity.
        min_interval: Minimum spacing between requests in seconds.
        max_interval: Maximum enforced wait in seconds.

    Returns:
        None: Class constructor.

    Raises:
        ValueError: If any provided threshold is invalid.
    """

    def __init__(
        self,
        rate_interval: float = DEFAULT_RATE_INTERVAL,
        burst: int = DEFAULT_BURST,
        min_interval: float = DEFAULT_MIN_INTERVAL,
        max_interval: float = DEFAULT_MAX_INTERVAL,
    ) -> None:
        self._validate_limits(rate_interval, burst, min_interval, max_interval)
        self.rate_interval = float(rate_interval)
        self.burst = int(burst)
        self.min_interval = float(min_interval)
        self.max_interval = float(max_interval)

        self._tokens = float(self.burst)
        self._last_refill = time.monotonic()
        self._last_request = 0.0
        self._lock = threading.Lock()
        self._total_wait = 0.0
        self._total_waits = 0

    @staticmethod
    def _validate_limits(rate_interval: float, burst: int, min_interval: float, max_interval: float) -> None:
        """Validate limiter configuration values.

        Bilingual: Valida valores de configuración del limitador.

        Args:
            rate_interval: Seconds per token refill.
            burst: Maximum token count.
            min_interval: Minimum spacing between calls.
            max_interval: Maximum allowed sleep window.

        Returns:
            None: Validation helper.

        Raises:
            ValueError: If configuration is inconsistent.
        """
        if rate_interval <= 0:
            raise ValueError("rate_interval must be positive")
        if burst < 1:
            raise ValueError("burst must be >= 1")
        if min_interval < 0:
            raise ValueError("min_interval must be >= 0")
        if max_interval <= 0:
            raise ValueError("max_interval must be positive")
        if min_interval > max_interval:
            raise ValueError("min_interval must be <= max_interval")

    def _refill_tokens(self, now: float) -> None:
        """Refill tokens according to elapsed monotonic time.

        Bilingual: Rellena tokens según tiempo monotónico transcurrido.

        Args:
            now: Current monotonic timestamp.

        Returns:
            None: Internal state update.

        Raises:
            None.
        """
        elapsed = now - self._last_refill
        if elapsed <= 0:
            return
        added_tokens = elapsed / self.rate_interval
        self._tokens = min(float(self.burst), self._tokens + added_tokens)
        self._last_refill = now

    def _compute_wait(self, now: float) -> float:
        """Compute required blocking time for the next request.

        Bilingual: Calcula el tiempo de bloqueo requerido para la siguiente solicitud.

        Args:
            now: Current monotonic timestamp.

        Returns:
            float: Sleep duration in seconds.

        Raises:
            None.
        """
        token_wait = 0.0
        if self._tokens < 1.0:
            token_wait = (1.0 - self._tokens) * self.rate_interval

        min_gap_wait = max(0.0, self.min_interval - (now - self._last_request))
        desired_wait = max(token_wait, min_gap_wait)
        return min(desired_wait, self.max_interval)

    def wait(self) -> float:
        """Block until next request is allowed and consume one token.

        Bilingual: Bloquea hasta permitir la siguiente solicitud y consume un token.

        Args:
            None.

        Returns:
            float: Seconds waited for the call.

        Raises:
            None.
        """
        with self._lock:
            now = time.monotonic()
            self._refill_tokens(now)
            wait_seconds = self._compute_wait(now)

            if wait_seconds > 0:
                time.sleep(wait_seconds)
                now = time.monotonic()
                self._refill_tokens(now)

            self._tokens = max(0.0, self._tokens - 1.0)
            self._last_request = now
            self._total_wait += wait_seconds
            self._total_waits += 1
            return wait_seconds

    @property
    def stats(self) -> dict[str, Any]:
        """Expose lightweight runtime metrics.

        Bilingual: Expone métricas operativas simples en tiempo real.

        Args:
            None.

        Returns:
            dict[str, Any]: Current limiter configuration and counters.

        Raises:
            None.
        """
        with self._lock:
            return {
                "rate_interval": self.rate_interval,
                "burst": self.burst,
                "min_interval": self.min_interval,
                "max_interval": self.max_interval,
                "tokens": self._tokens,
                "total_wait_seconds": self._total_wait,
                "total_waits": self._total_waits,
            }

    @property
    def tokens_available(self) -> float:
        """Return current token availability snapshot.

        Bilingual: Retorna el snapshot actual de tokens disponibles.

        Args:
            None.

        Returns:
            float: Available tokens in bucket.

        Raises:
            None.
        """
        with self._lock:
            return self._tokens


_rate_limiter_singleton: Optional[TokenBucketRateLimiter] = None
_rate_limiter_lock = threading.Lock()


def _load_rate_limiter_config(env: str = "prod") -> dict[str, Any]:
    """Load rate limiter config with safe fallback.

    Bilingual: Carga configuración de rate limiter con fallback seguro.

    Args:
        env: Configuration environment folder.

    Returns:
        dict[str, Any]: Parsed limiter configuration.

    Raises:
        None.
    """
    try:
        return load_config("rate_limiter.yaml", env=env)
    except Exception as exc:  # noqa: BLE001
        logger.warning("rate_limiter_config_fallback | usando defaults: %s", exc)
        return {}


def get_rate_limiter(env: str = "prod") -> TokenBucketRateLimiter:
    """Return singleton limiter instance.

    Bilingual: Retorna la instancia singleton del limitador.

    Args:
        env: Configuration environment folder.

    Returns:
        TokenBucketRateLimiter: Shared limiter instance.

    Raises:
        None.
    """
    global _rate_limiter_singleton
    with _rate_limiter_lock:
        if _rate_limiter_singleton is None:
            config = _load_rate_limiter_config(env)
            _rate_limiter_singleton = TokenBucketRateLimiter(
                rate_interval=float(config.get("rate_interval", DEFAULT_RATE_INTERVAL)),
                burst=int(config.get("burst", DEFAULT_BURST)),
                min_interval=float(config.get("min_interval", DEFAULT_MIN_INTERVAL)),
                max_interval=float(config.get("max_interval", DEFAULT_MAX_INTERVAL)),
            )
        return _rate_limiter_singleton


def reset_rate_limiter() -> None:
    """Reset singleton limiter instance for tests and controlled reload.

    Bilingual: Reinicia la instancia singleton para pruebas y recarga controlada.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    global _rate_limiter_singleton
    with _rate_limiter_lock:
        _rate_limiter_singleton = None
