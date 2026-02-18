"""Client-side rate limiter using a token-bucket algorithm for ethical CNE scraping.

Ensures Centinel never exceeds a configurable request rate, complementing
server-side protections (Cloudflare, PR #397) with a strict local governor.
The default configuration allows 1 request every 8-12 seconds with a burst of 3.

Bilingual: Limitador de tasa del lado cliente usando algoritmo token-bucket para
scraping etico del CNE. Garantiza que Centinel nunca exceda una tasa de requests
configurable, complementando protecciones del lado servidor (Cloudflare, PR #397)
con un gobernador local estricto. La configuracion por defecto permite 1 request
cada 8-12 segundos con un burst de 3.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Optional

logger = logging.getLogger(__name__)

# Default rate-limit parameters / Parametros de rate-limit por defecto
DEFAULT_RATE_INTERVAL: float = 10.0  # seconds between tokens / segundos entre tokens
DEFAULT_BURST: int = 3  # max burst size / tamano maximo de burst
DEFAULT_MIN_INTERVAL: float = 8.0  # minimum wait between requests / espera minima entre requests
DEFAULT_MAX_INTERVAL: float = 12.0  # maximum wait between requests / espera maxima entre requests


class TokenBucketRateLimiter:
    """Thread-safe token-bucket rate limiter for HTTP request throttling.

    Implements a classic token-bucket algorithm where tokens accumulate at a
    fixed rate up to a configurable burst capacity. Each call to ``wait()``
    consumes one token, blocking the caller until a token is available.

    Bilingual: Limitador de tasa token-bucket thread-safe para throttling de
    requests HTTP. Implementa un algoritmo clasico de token-bucket donde los
    tokens se acumulan a una tasa fija hasta una capacidad de burst configurable.
    Cada llamada a ``wait()`` consume un token, bloqueando al llamador hasta que
    un token este disponible.

    Args:
        rate_interval: Seconds between token generation (default: 10.0).
        burst: Maximum number of tokens in the bucket (default: 3).
        min_interval: Hard minimum seconds between any two requests (default: 8.0).
        max_interval: Soft upper bound for inter-request delay (default: 12.0).
    """

    def __init__(
        self,
        *,
        rate_interval: float = DEFAULT_RATE_INTERVAL,
        burst: int = DEFAULT_BURST,
        min_interval: float = DEFAULT_MIN_INTERVAL,
        max_interval: float = DEFAULT_MAX_INTERVAL,
    ) -> None:
        if rate_interval <= 0:
            raise ValueError("rate_interval must be positive")
        if burst < 1:
            raise ValueError("burst must be >= 1")
        if min_interval < 0:
            raise ValueError("min_interval must be >= 0")

        self._rate_interval: float = rate_interval
        self._burst: int = burst
        self._min_interval: float = min_interval
        self._max_interval: float = max_interval

        # Start with full bucket / Iniciar con bucket lleno
        self._tokens: float = float(burst)
        self._last_refill: float = time.monotonic()
        self._last_request: float = 0.0
        self._lock: threading.Lock = threading.Lock()

        # Counters for observability / Contadores para observabilidad
        self._total_waits: int = 0
        self._total_wait_seconds: float = 0.0

        logger.info(
            "Rate limiter initialized | Limitador de tasa inicializado: "
            "interval=%.1fs, burst=%d, min=%.1fs, max=%.1fs",
            rate_interval,
            burst,
            min_interval,
            max_interval,
        )

    def _refill(self, now: float) -> None:
        """Refill tokens based on elapsed time since last refill.

        Bilingual: Rellenar tokens basado en tiempo transcurrido desde ultimo relleno.
        """
        elapsed = now - self._last_refill
        new_tokens = elapsed / self._rate_interval
        self._tokens = min(self._tokens + new_tokens, float(self._burst))
        self._last_refill = now

    def wait(self) -> float:
        """Block until a token is available, then consume it and return wait time.

        Enforces both the token-bucket rate and the hard minimum inter-request
        interval to guarantee ethical request pacing.

        Bilingual: Bloquea hasta que un token este disponible, lo consume y
        retorna el tiempo de espera. Aplica tanto la tasa del token-bucket como
        el intervalo minimo entre requests para garantizar ritmo etico de requests.

        Returns:
            The number of seconds the caller was blocked (0.0 if a token was
            immediately available and the minimum interval had elapsed).
        """
        total_waited = 0.0

        with self._lock:
            now = time.monotonic()
            self._refill(now)

            # Enforce hard minimum interval / Aplicar intervalo minimo estricto
            if self._last_request > 0:
                since_last = now - self._last_request
                if since_last < self._min_interval:
                    gap = self._min_interval - since_last
                    # Release lock while sleeping / Liberar lock mientras espera
                    self._lock.release()
                    try:
                        time.sleep(gap)
                        total_waited += gap
                    finally:
                        self._lock.acquire()
                    now = time.monotonic()
                    self._refill(now)

            # Wait for token availability / Esperar disponibilidad de token
            while self._tokens < 1.0:
                deficit = 1.0 - self._tokens
                sleep_time = deficit * self._rate_interval
                # Cap sleep to max_interval / Limitar espera a max_interval
                sleep_time = min(sleep_time, self._max_interval)
                self._lock.release()
                try:
                    time.sleep(sleep_time)
                    total_waited += sleep_time
                finally:
                    self._lock.acquire()
                now = time.monotonic()
                self._refill(now)

            # Consume one token / Consumir un token
            self._tokens -= 1.0
            self._last_request = time.monotonic()

            # Update counters / Actualizar contadores
            self._total_waits += 1
            self._total_wait_seconds += total_waited

        if total_waited > 0:
            logger.debug(
                "Rate limiter waited %.2fs | Limitador espero %.2fs " "(tokens_remaining=%.1f)",
                total_waited,
                total_waited,
                self._tokens,
            )

        return total_waited

    @property
    def tokens_available(self) -> float:
        """Current number of tokens available (approximate).

        Bilingual: Numero actual de tokens disponibles (aproximado).
        """
        with self._lock:
            self._refill(time.monotonic())
            return self._tokens

    @property
    def stats(self) -> dict[str, float | int]:
        """Return rate limiter statistics for monitoring.

        Bilingual: Retorna estadisticas del limitador de tasa para monitoreo.
        """
        with self._lock:
            return {
                "total_waits": self._total_waits,
                "total_wait_seconds": round(self._total_wait_seconds, 3),
                "tokens_available": round(self._tokens, 2),
                "rate_interval": self._rate_interval,
                "burst": self._burst,
                "min_interval": self._min_interval,
                "max_interval": self._max_interval,
            }


# ---------------------------------------------------------------------------
# Module-level singleton / Singleton a nivel de modulo
# ---------------------------------------------------------------------------

_RATE_LIMITER: Optional[TokenBucketRateLimiter] = None
_SINGLETON_LOCK: threading.Lock = threading.Lock()


def get_rate_limiter(
    *,
    rate_interval: float = DEFAULT_RATE_INTERVAL,
    burst: int = DEFAULT_BURST,
    min_interval: float = DEFAULT_MIN_INTERVAL,
    max_interval: float = DEFAULT_MAX_INTERVAL,
) -> TokenBucketRateLimiter:
    """Return the global rate limiter instance, creating it on first call.

    Thread-safe singleton accessor. Subsequent calls return the existing
    instance regardless of parameters.

    Bilingual: Retorna la instancia global del limitador de tasa, creandola en
    la primera llamada. Accessor singleton thread-safe. Llamadas subsecuentes
    retornan la instancia existente independientemente de los parametros.
    """
    global _RATE_LIMITER
    if _RATE_LIMITER is not None:
        return _RATE_LIMITER
    with _SINGLETON_LOCK:
        if _RATE_LIMITER is not None:
            return _RATE_LIMITER
        _RATE_LIMITER = TokenBucketRateLimiter(
            rate_interval=rate_interval,
            burst=burst,
            min_interval=min_interval,
            max_interval=max_interval,
        )
        return _RATE_LIMITER


def reset_rate_limiter() -> None:
    """Reset the global singleton (mainly for testing).

    Bilingual: Reinicia el singleton global (principalmente para testing).
    """
    global _RATE_LIMITER
    with _SINGLETON_LOCK:
        _RATE_LIMITER = None
