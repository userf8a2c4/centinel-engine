"""Tests for centinel_engine.rate_limiter (client-side token-bucket rate limiting).

Bilingual: Pruebas para centinel_engine.rate_limiter (rate-limiting del lado
cliente con token-bucket).
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any, Dict

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from centinel_engine.rate_limiter import (  # noqa: E402
    TokenBucketRateLimiter,
    get_rate_limiter,
    reset_rate_limiter,
)


# ---------------------------------------------------------------------------
# Fixtures / Fixtures de prueba
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_singleton() -> None:
    """Reset the global singleton before each test / Reiniciar singleton antes de cada test."""
    reset_rate_limiter()
    yield  # type: ignore[misc]
    reset_rate_limiter()


# ---------------------------------------------------------------------------
# Test 1: Construction and defaults / Construccion y valores por defecto
# ---------------------------------------------------------------------------


class TestConstruction:
    """Tests for rate limiter construction / Pruebas de construccion del limitador."""

    def test_default_parameters(self) -> None:
        """Default limiter has expected configuration.

        Bilingual: Limitador por defecto tiene configuracion esperada.
        """
        rl = TokenBucketRateLimiter()
        stats = rl.stats
        assert stats["rate_interval"] == 10.0
        assert stats["burst"] == 3
        assert stats["min_interval"] == 8.0
        assert stats["max_interval"] == 12.0

    def test_custom_parameters(self) -> None:
        """Custom parameters are respected.

        Bilingual: Parametros personalizados se respetan.
        """
        rl = TokenBucketRateLimiter(rate_interval=5.0, burst=2, min_interval=3.0, max_interval=7.0)
        stats = rl.stats
        assert stats["rate_interval"] == 5.0
        assert stats["burst"] == 2
        assert stats["min_interval"] == 3.0
        assert stats["max_interval"] == 7.0

    def test_invalid_rate_interval_raises(self) -> None:
        """Non-positive rate_interval raises ValueError.

        Bilingual: rate_interval no positivo lanza ValueError.
        """
        with pytest.raises(ValueError, match="rate_interval must be positive"):
            TokenBucketRateLimiter(rate_interval=0)

    def test_invalid_burst_raises(self) -> None:
        """Burst < 1 raises ValueError.

        Bilingual: Burst < 1 lanza ValueError.
        """
        with pytest.raises(ValueError, match="burst must be >= 1"):
            TokenBucketRateLimiter(burst=0)

    def test_invalid_min_interval_raises(self) -> None:
        """Negative min_interval raises ValueError.

        Bilingual: min_interval negativo lanza ValueError.
        """
        with pytest.raises(ValueError, match="min_interval must be >= 0"):
            TokenBucketRateLimiter(min_interval=-1)


# ---------------------------------------------------------------------------
# Test 2: Token consumption / Consumo de tokens
# ---------------------------------------------------------------------------


class TestTokenConsumption:
    """Tests for token bucket behavior / Pruebas del comportamiento del token-bucket."""

    def test_first_wait_is_instant(self) -> None:
        """First call to wait() returns near-zero delay (bucket starts full).

        Bilingual: Primera llamada a wait() retorna delay cercano a cero (bucket inicia lleno).
        """
        rl = TokenBucketRateLimiter(rate_interval=1.0, burst=3, min_interval=0.0, max_interval=5.0)
        waited = rl.wait()
        assert waited < 0.5  # should be nearly instant / deberia ser casi instantaneo

    def test_burst_allows_multiple_fast_requests(self) -> None:
        """Burst capacity allows several requests without waiting.

        Bilingual: Capacidad de burst permite varias requests sin esperar.
        """
        rl = TokenBucketRateLimiter(rate_interval=1.0, burst=3, min_interval=0.0, max_interval=5.0)
        total_wait = 0.0
        for _ in range(3):
            total_wait += rl.wait()
        # All 3 should be fast / Las 3 deberian ser rapidas
        assert total_wait < 1.0

    def test_tokens_deplete_after_burst(self) -> None:
        """After burst is exhausted, wait() blocks for token refill.

        Bilingual: Despues de agotar el burst, wait() bloquea para relleno de token.
        """
        rl = TokenBucketRateLimiter(rate_interval=0.5, burst=1, min_interval=0.0, max_interval=2.0)
        rl.wait()  # consume the only token / consumir el unico token
        start = time.monotonic()
        rl.wait()  # must wait for refill / debe esperar relleno
        elapsed = time.monotonic() - start
        assert elapsed >= 0.3  # should wait ~0.5s / deberia esperar ~0.5s


# ---------------------------------------------------------------------------
# Test 3: Minimum interval enforcement / Aplicacion de intervalo minimo
# ---------------------------------------------------------------------------


class TestMinimumInterval:
    """Tests for minimum inter-request interval / Pruebas de intervalo minimo entre requests."""

    def test_min_interval_enforced(self) -> None:
        """Consecutive requests respect minimum interval spacing.

        Bilingual: Requests consecutivos respetan espaciado de intervalo minimo.
        """
        rl = TokenBucketRateLimiter(rate_interval=0.1, burst=10, min_interval=0.5, max_interval=5.0)
        rl.wait()
        start = time.monotonic()
        rl.wait()
        elapsed = time.monotonic() - start
        assert elapsed >= 0.4  # should enforce ~0.5s gap / deberia aplicar ~0.5s de gap


# ---------------------------------------------------------------------------
# Test 4: Stats tracking / Seguimiento de estadisticas
# ---------------------------------------------------------------------------


class TestStats:
    """Tests for statistics tracking / Pruebas de seguimiento de estadisticas."""

    def test_stats_increment(self) -> None:
        """Stats track total waits correctly.

        Bilingual: Estadisticas rastrean total de esperas correctamente.
        """
        rl = TokenBucketRateLimiter(rate_interval=1.0, burst=5, min_interval=0.0, max_interval=5.0)
        rl.wait()
        rl.wait()
        stats = rl.stats
        assert stats["total_waits"] == 2

    def test_tokens_available_decreases(self) -> None:
        """Tokens available decreases after consumption.

        Bilingual: Tokens disponibles disminuyen despues de consumo.
        """
        rl = TokenBucketRateLimiter(rate_interval=100.0, burst=3, min_interval=0.0, max_interval=200.0)
        initial = rl.tokens_available
        rl.wait()
        after = rl.tokens_available
        assert after < initial


# ---------------------------------------------------------------------------
# Test 5: Singleton / Singleton
# ---------------------------------------------------------------------------


class TestSingleton:
    """Tests for the global singleton accessor / Pruebas del accessor singleton global."""

    def test_singleton_returns_same_instance(self) -> None:
        """get_rate_limiter() returns the same instance on repeated calls.

        Bilingual: get_rate_limiter() retorna la misma instancia en llamadas repetidas.
        """
        a = get_rate_limiter()
        b = get_rate_limiter()
        assert a is b

    def test_reset_creates_new_instance(self) -> None:
        """reset_rate_limiter() allows creation of a new singleton.

        Bilingual: reset_rate_limiter() permite creacion de un nuevo singleton.
        """
        a = get_rate_limiter()
        reset_rate_limiter()
        b = get_rate_limiter()
        assert a is not b
