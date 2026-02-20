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
import random
import threading
import time
from collections import deque
from typing import Any, Deque, Optional

from centinel_engine.config_loader import load_config

logger = logging.getLogger(__name__)

DEFAULT_RATE_INTERVAL: float = 10.0
DEFAULT_BURST: int = 3
DEFAULT_MIN_INTERVAL: float = 8.0
DEFAULT_MAX_INTERVAL: float = 12.0
DEFAULT_MAX_REQUESTS_PER_HOUR: int = 180
DEFAULT_BACKOFF_JITTER_MIN: float = 0.6
DEFAULT_BACKOFF_JITTER_MAX: float = 1.8
DEFAULT_CONSERVATIVE_MIN_DELAY_SECONDS: float = 900.0
DEFAULT_429_WINDOW_SECONDS: float = 300.0
DEFAULT_429_THRESHOLD: int = 3


class TokenBucketRateLimiter:
    """Throttle requests using a thread-safe token bucket.

    Bilingual: Limita solicitudes usando un token-bucket thread-safe.

    Args:
        rate_interval: Seconds to refill one token.
        burst: Maximum token capacity.
        min_interval: Minimum spacing between requests in seconds.
        max_interval: Maximum enforced wait in seconds.
        max_requests_per_hour: Hard legal/ethical upper limit.
        conservative_min_delay_seconds: Minimum delay while in conservative mode.

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
        max_requests_per_hour: int = DEFAULT_MAX_REQUESTS_PER_HOUR,
        conservative_min_delay_seconds: float = DEFAULT_CONSERVATIVE_MIN_DELAY_SECONDS,
    ) -> None:
        self._validate_limits(rate_interval, burst, min_interval, max_interval, max_requests_per_hour)
        self.rate_interval = float(rate_interval)
        self.burst = int(burst)
        self.min_interval = float(min_interval)
        self.max_interval = float(max_interval)
        self.max_requests_per_hour = int(max_requests_per_hour)
        self.conservative_min_delay_seconds = float(conservative_min_delay_seconds)

        self._tokens = float(self.burst)
        self._last_refill = time.monotonic()
        self._last_request = 0.0
        self._lock = threading.Lock()
        self._total_wait = 0.0
        self._total_waits = 0
        self._consecutive_failures = 0
        self._recent_429_timestamps: Deque[float] = deque()
        self._request_timestamps: Deque[float] = deque()
        self._conservative_mode_until = 0.0

    @staticmethod
    def _validate_limits(
        rate_interval: float,
        burst: int,
        min_interval: float,
        max_interval: float,
        max_requests_per_hour: int,
    ) -> None:
        """Validate limiter configuration values.

        Bilingual: Valida valores de configuración del limitador.

        Args:
            rate_interval: Seconds per token refill.
            burst: Maximum token count.
            min_interval: Minimum spacing between calls.
            max_interval: Maximum allowed sleep window.
            max_requests_per_hour: Hard cap per rolling hour.

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
        if max_requests_per_hour < 1:
            raise ValueError("max_requests_per_hour must be >= 1")

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

    def _enforce_hourly_limit_wait(self, now_wall: float) -> float:
        """Return extra wait needed to honor the per-hour request cap.

        Bilingual: Retorna espera extra necesaria para respetar el límite por hora.

        Args:
            now_wall: Current wall-clock timestamp.

        Returns:
            float: Additional wait seconds to maintain cap.

        Raises:
            None.
        """
        window_start = now_wall - 3600.0
        while self._request_timestamps and self._request_timestamps[0] < window_start:
            self._request_timestamps.popleft()
        if len(self._request_timestamps) < self.max_requests_per_hour:
            return 0.0
        oldest_within_window = self._request_timestamps[0]
        return max(0.0, (oldest_within_window + 3600.0) - now_wall)

    def _compute_adaptive_backoff_delay(self) -> float:
        """Compute adaptive backoff with exponential jitter.

        Bilingual: Calcula backoff adaptativo con jitter exponencial.

        Args:
            None.

        Returns:
            float: Delay derived from failures and jitter.

        Raises:
            None.
        """
        if self._consecutive_failures <= 0:
            return 0.0
        base = max(3600.0 / float(self.max_requests_per_hour), self.min_interval)
        jitter = random.uniform(DEFAULT_BACKOFF_JITTER_MIN, DEFAULT_BACKOFF_JITTER_MAX)
        return base * (2 ** self._consecutive_failures) * jitter

    def _is_conservative_active(self, now_wall: float) -> bool:
        """Check whether conservative mode is active.

        Bilingual: Verifica si el modo conservador está activo.

        Args:
            now_wall: Current wall-clock timestamp.

        Returns:
            bool: True when conservative mode still applies.

        Raises:
            None.
        """
        return now_wall < self._conservative_mode_until

    def wait(self) -> float:
        """Block until next request is allowed and consume one token.

        Bilingual: Bloquea hasta permitir la siguiente solicitud y consume un token,
        aplicando jitter más amplio y sleep aleatorio sutil para romper patrones de timing.

        Args:
            None.

        Returns:
            float: Seconds waited for the call, including adaptive and random delays.

        Raises:
            None.
        """
        total_waited = 0.0
        with self._lock:
            while True:
                now_mono = time.monotonic()
                now_wall = time.time()
                self._refill_tokens(now_mono)
                core_wait = self._compute_wait(now_mono)
                hourly_wait = self._enforce_hourly_limit_wait(now_wall)
                adaptive_wait = self._compute_adaptive_backoff_delay()
                conservative_wait = self.conservative_min_delay_seconds if self._is_conservative_active(now_wall) else 0.0

                wait_seconds = max(core_wait, hourly_wait, adaptive_wait, conservative_wait)
                # Wider jitter + small random sleep to disrupt timing fingerprinting / # Jitter más amplio + sleep random sutil para romper fingerprinting por timing
                random_sleep: float = random.uniform(0.0, 3.0)
                time.sleep(random_sleep)
                total_waited += random_sleep
                if wait_seconds <= 0:
                    break
                # English: sleep in bounded chunks so long waits can adapt quickly. / Español: dormir en bloques para adaptar esperas largas.
                sleep_chunk = min(wait_seconds, 60.0)
                time.sleep(sleep_chunk)
                total_waited += sleep_chunk

            now_mono = time.monotonic()
            now_wall = time.time()
            self._refill_tokens(now_mono)
            self._tokens = max(0.0, self._tokens - 1.0)
            self._last_request = now_mono
            self._request_timestamps.append(now_wall)
            self._total_wait += total_waited
            self._total_waits += 1
            return total_waited

    def notify_response(self, status_code: Optional[int], *, success: bool) -> None:
        """Update adaptive state from upstream response outcomes.

        Bilingual: Actualiza estado adaptativo con el resultado de respuesta.

        Args:
            status_code: Optional HTTP response status code.
            success: Whether request is considered successful.

        Returns:
            None.

        Raises:
            None.
        """
        with self._lock:
            if success:
                self._consecutive_failures = 0
            else:
                self._consecutive_failures += 1

            now_wall = time.time()
            if status_code == 429:
                self._recent_429_timestamps.append(now_wall)
            window_start = now_wall - DEFAULT_429_WINDOW_SECONDS
            while self._recent_429_timestamps and self._recent_429_timestamps[0] < window_start:
                self._recent_429_timestamps.popleft()

            if len(self._recent_429_timestamps) > DEFAULT_429_THRESHOLD:
                # English: force immediate conservative mode under repeated 429 bursts. / Español: forzar modo conservador inmediato ante ráfagas 429.
                self._conservative_mode_until = max(
                    self._conservative_mode_until,
                    now_wall + self.conservative_min_delay_seconds,
                )
                logger.warning(
                    "rate_limiter_forced_conservative | 429_burst=%s window_seconds=%s",
                    len(self._recent_429_timestamps),
                    int(DEFAULT_429_WINDOW_SECONDS),
                )

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
                "max_requests_per_hour": self.max_requests_per_hour,
                "conservative_min_delay_seconds": self.conservative_min_delay_seconds,
                "tokens": self._tokens,
                "consecutive_failures": self._consecutive_failures,
                "recent_429_count": len(self._recent_429_timestamps),
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


def _load_core_limits(env: str = "prod") -> dict[str, Any]:
    """Load core legal/ethical limits from shared production config.

    Bilingual: Carga límites legales/éticos desde configuración productiva compartida.

    Args:
        env: Configuration environment folder.

    Returns:
        dict[str, Any]: Mapping with governance limits.

    Raises:
        None.
    """
    try:
        return load_config("rules_core.yaml", env=env)
    except Exception as exc:  # noqa: BLE001
        logger.warning("rate_limiter_core_limits_fallback | usando defaults: %s", exc)
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
            core_limits = _load_core_limits(env)
            max_requests_per_hour = int(
                config.get(
                    "max_requests_per_hour",
                    core_limits.get("MAX_REQUESTS_PER_HOUR", DEFAULT_MAX_REQUESTS_PER_HOUR),
                )
            )
            _rate_limiter_singleton = TokenBucketRateLimiter(
                rate_interval=float(config.get("rate_interval", config.get("rate_interval_seconds", DEFAULT_RATE_INTERVAL))),
                burst=int(config.get("burst", config.get("capacity", DEFAULT_BURST))),
                min_interval=float(config.get("min_interval", config.get("min_interval_seconds", DEFAULT_MIN_INTERVAL))),
                max_interval=float(config.get("max_interval", config.get("max_interval_seconds", DEFAULT_MAX_INTERVAL))),
                max_requests_per_hour=max_requests_per_hour,
                conservative_min_delay_seconds=float(
                    config.get("conservative_min_delay_seconds", DEFAULT_CONSERVATIVE_MIN_DELAY_SECONDS)
                ),
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
