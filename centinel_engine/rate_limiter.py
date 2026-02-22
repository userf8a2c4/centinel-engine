"""Token-bucket rate limiter for ethical, throttled CNE requests.
Bilingual: Rate limiter de token-bucket para solicitudes eticas y reguladas al CNE.

Implements a strict client-side rate limiter to ensure respectful access to
public CNE servers. Default: max 3 burst tokens, replenished at 1 token every
10 seconds (configurable, minimum 8 seconds).

Implementa un rate limiter estricto del lado del cliente para asegurar acceso
respetuoso a servidores publicos del CNE. Default: max 3 tokens de burst,
reposicion de 1 token cada 10 segundos (configurable, minimo 8 segundos).
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Optional

logger = logging.getLogger(__name__)

# Minimum refill interval enforced for ethical scraping /
# Intervalo minimo de reposicion forzado para scraping etico
_MINIMUM_REFILL_SECONDS: float = 8.0


class TokenBucketRateLimiter:
    """Thread-safe token-bucket rate limiter with ethical minimum constraints.
    Bilingual: Rate limiter de token-bucket thread-safe con restricciones eticas minimas.

    Tokens are consumed on each request. When no tokens are available, the
    ``wait()`` method blocks until a token is replenished.  This guarantees
    that the CNE server is never overwhelmed by burst traffic.

    Los tokens se consumen en cada solicitud. Cuando no hay tokens disponibles,
    el metodo ``wait()`` bloquea hasta que un token se reponga. Esto garantiza
    que el servidor del CNE nunca sea abrumado por trafico en rafaga.
    """

    def __init__(
        self,
        capacity: int = 3,
        refill_seconds: float = 10.0,
    ) -> None:
        """Initialize the rate limiter.
        Bilingual: Inicializa el rate limiter.

        Args:
            capacity: Maximum number of tokens (burst capacity).
                      Capacidad maxima de tokens (capacidad de burst).
            refill_seconds: Seconds between token refills (minimum 8s enforced).
                            Segundos entre reposiciones de token (minimo 8s forzado).

        Raises:
            ValueError: If capacity < 1 or refill_seconds < minimum.
        """
        if capacity < 1:
            raise ValueError(
                f"Capacity must be >= 1 / Capacidad debe ser >= 1: {capacity}"
            )
        # Enforce ethical minimum refill rate /
        # Forzar tasa minima etica de reposicion
        effective_refill: float = max(refill_seconds, _MINIMUM_REFILL_SECONDS)
        if refill_seconds < _MINIMUM_REFILL_SECONDS:
            logger.warning(
                "Refill rate %.1fs below ethical minimum %.1fs, enforcing minimum / "
                "Tasa de reposicion %.1fs por debajo del minimo etico %.1fs, forzando minimo",
                refill_seconds,
                _MINIMUM_REFILL_SECONDS,
                refill_seconds,
                _MINIMUM_REFILL_SECONDS,
            )

        self._capacity: int = capacity
        self._refill_seconds: float = effective_refill
        self._tokens: float = float(capacity)
        self._last_refill: float = time.monotonic()
        self._lock: threading.Lock = threading.Lock()

        logger.info(
            "RateLimiter initialized: capacity=%d, refill_seconds=%.1f / "
            "RateLimiter inicializado: capacidad=%d, segundos_reposicion=%.1f",
            capacity,
            effective_refill,
            capacity,
            effective_refill,
        )

    @property
    def capacity(self) -> int:
        """Maximum token capacity.
        Bilingual: Capacidad maxima de tokens.

        Returns:
            Integer capacity.
        """
        return self._capacity

    @property
    def refill_seconds(self) -> float:
        """Seconds between token refills.
        Bilingual: Segundos entre reposiciones de token.

        Returns:
            Refill interval in seconds.
        """
        return self._refill_seconds

    @property
    def available_tokens(self) -> float:
        """Current number of available tokens (approximate, for monitoring).
        Bilingual: Numero actual de tokens disponibles (aproximado, para monitoreo).

        Returns:
            Float representing available tokens.
        """
        with self._lock:
            self._refill()
            return self._tokens

    def _refill(self) -> None:
        """Replenish tokens based on elapsed time since last refill.
        Bilingual: Repone tokens basado en tiempo transcurrido desde ultima reposicion.

        Must be called while holding ``self._lock``.
        Debe llamarse mientras se mantiene ``self._lock``.
        """
        now: float = time.monotonic()
        elapsed: float = now - self._last_refill
        # Calculate new tokens to add / Calcular nuevos tokens a agregar
        new_tokens: float = elapsed / self._refill_seconds
        if new_tokens > 0:
            self._tokens = min(self._capacity, self._tokens + new_tokens)
            self._last_refill = now

    def try_acquire(self) -> bool:
        """Try to acquire a token without blocking.
        Bilingual: Intenta adquirir un token sin bloquear.

        Returns:
            True if a token was acquired, False otherwise.
        """
        with self._lock:
            self._refill()
            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return True
            return False

    def wait(self) -> float:
        """Block until a token is available, then consume it.
        Bilingual: Bloquea hasta que un token este disponible, luego lo consume.

        This is the primary method to call before each CNE request.
        Este es el metodo principal a llamar antes de cada solicitud al CNE.

        Returns:
            Number of seconds waited (0.0 if a token was immediately available).
        """
        waited: float = 0.0
        while True:
            with self._lock:
                self._refill()
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    if waited > 0:
                        logger.debug(
                            "RateLimiter: token acquired after %.2fs wait / "
                            "RateLimiter: token adquirido tras %.2fs de espera",
                            waited,
                            waited,
                        )
                    return waited
                # Calculate time until next token / Calcular tiempo hasta proximo token
                deficit: float = 1.0 - self._tokens
                sleep_time: float = deficit * self._refill_seconds

            # Sleep outside the lock / Dormir fuera del lock
            time.sleep(sleep_time)
            waited += sleep_time


# ---------------------------------------------------------------------------
# Module-level singleton / Singleton a nivel de modulo
# ---------------------------------------------------------------------------
_RATE_LIMITER: Optional[TokenBucketRateLimiter] = None
_SINGLETON_LOCK: threading.Lock = threading.Lock()


def get_rate_limiter(
    capacity: int = 3,
    refill_seconds: float = 10.0,
) -> TokenBucketRateLimiter:
    """Return the global rate limiter singleton, creating it if needed.
    Bilingual: Retorna el singleton global del rate limiter, creandolo si es necesario.

    Args:
        capacity: Maximum burst tokens (only used on first call).
        refill_seconds: Seconds between refills (only used on first call).

    Returns:
        The global TokenBucketRateLimiter instance.
    """
    global _RATE_LIMITER
    if _RATE_LIMITER is not None:
        return _RATE_LIMITER
    with _SINGLETON_LOCK:
        if _RATE_LIMITER is None:
            _RATE_LIMITER = TokenBucketRateLimiter(
                capacity=capacity,
                refill_seconds=refill_seconds,
            )
    return _RATE_LIMITER


def reset_rate_limiter() -> None:
    """Reset the global singleton (for testing only).
    Bilingual: Resetea el singleton global (solo para testing).
    """
    global _RATE_LIMITER
    with _SINGLETON_LOCK:
        _RATE_LIMITER = None
