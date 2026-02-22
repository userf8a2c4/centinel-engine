"""Hostile scenario tests for Centinel resilience and security hardening.
Bilingual: Tests de escenarios hostiles para resiliencia y hardening de seguridad de Centinel.

Validates that the system behaves correctly under adversarial conditions:
- Sustained 429 responses trigger critical mode with 1800s delay.
- Hash chain corruption triggers critical mode.
- Empty proxy pool falls back to direct connection or raises alert.
- Rate limiter blocks burst requests exceeding capacity.

Valida que el sistema se comporta correctamente bajo condiciones adversas:
- Respuestas 429 sostenidas disparan modo critico con delay de 1800s.
- Corrupcion de hash chain dispara modo critico.
- Pool de proxies vacio hace fallback a conexion directa o alerta.
- Rate limiter bloquea requests en rafaga que exceden capacidad.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List
from unittest.mock import patch

import pytest

from centinel_engine.vital_signs import (
    check_vital_signs,
    update_status_after_scrape,
)
from centinel_engine.rate_limiter import (
    TokenBucketRateLimiter,
    reset_rate_limiter,
)
from centinel_engine.proxy_manager import (
    ProxyAndUAManager,
    _DEFAULT_USER_AGENTS,
)


# ---------------------------------------------------------------------------
# Fixtures / Fixtures de configuracion
# ---------------------------------------------------------------------------

@pytest.fixture()
def default_config() -> Dict[str, Any]:
    """Provide a default configuration for vital signs tests.
    Bilingual: Provee una configuracion por defecto para tests de vital signs.

    Returns:
        Configuration dictionary with standard thresholds.
    """
    return {
        "scrape_interval_seconds": 300,
        "consecutive_failures_conservative": 3,
        "consecutive_failures_critical": 5,
        "min_success_rate": 0.70,
        "max_avg_latency": 10.0,
        "success_history_window": 10,
        "critical_delay_seconds": 1800,
    }


@pytest.fixture(autouse=True)
def _reset_singletons() -> None:
    """Reset module-level singletons between tests.
    Bilingual: Resetea singletons a nivel de modulo entre tests.
    """
    reset_rate_limiter()


# ---------------------------------------------------------------------------
# Test 1: 50x consecutive 429s -> critical mode, delay 1800s /
# Test 1: 50x 429 consecutivos -> modo critico, delay 1800s
# ---------------------------------------------------------------------------

class TestConsecutive429sCritical:
    """Verify that 50 consecutive 429 responses trigger critical mode with 1800s delay.
    Bilingual: Verifica que 50 respuestas 429 consecutivas disparan modo critico con delay 1800s.
    """

    def test_50_consecutive_429s_triggers_critical(
        self, default_config: Dict[str, Any]
    ) -> None:
        """Simulate 50 consecutive 429 HTTP responses and verify critical mode.
        Bilingual: Simula 50 respuestas HTTP 429 consecutivas y verifica modo critico.

        Args:
            default_config: Test configuration fixture.
        """
        # Build up scrape status with 50 consecutive failures /
        # Construir estado de scrape con 50 fallas consecutivas
        scrape_status: Dict[str, Any] = {
            "consecutive_failures": 0,
            "success_history": [],
            "latency_history": [],
            "hash_chain_valid": True,
        }

        for i in range(50):
            scrape_status = update_status_after_scrape(
                scrape_status,
                success=False,
                latency=30.0,
                status_code=429,
                hash_chain_valid=True,
            )

        # Verify accumulated failures / Verificar fallas acumuladas
        assert scrape_status["consecutive_failures"] == 50
        assert scrape_status["last_status_code"] == 429

        # Check vital signs should produce critical mode /
        # Verificar que vital signs produce modo critico
        result: Dict[str, Any] = check_vital_signs(default_config, scrape_status)

        assert result["mode"] == "critical", (
            f"Expected critical mode after 50x 429, got {result['mode']}"
        )
        assert result["recommended_delay_seconds"] >= 1800, (
            f"Expected delay >= 1800s, got {result['recommended_delay_seconds']}"
        )
        assert result["alert_needed"] is True

    def test_progressive_degradation_to_critical(
        self, default_config: Dict[str, Any]
    ) -> None:
        """Verify progressive degradation: normal -> conservative -> critical.
        Bilingual: Verifica degradacion progresiva: normal -> conservative -> critical.

        Args:
            default_config: Test configuration fixture.
        """
        scrape_status: Dict[str, Any] = {
            "consecutive_failures": 0,
            "success_history": [],
            "latency_history": [],
            "hash_chain_valid": True,
        }

        # After 3 failures: should be conservative /
        # Despues de 3 fallas: deberia ser conservativo
        for _ in range(3):
            scrape_status = update_status_after_scrape(
                scrape_status, success=False, latency=15.0, status_code=429,
            )

        result = check_vital_signs(default_config, scrape_status)
        assert result["mode"] == "conservative"

        # After 5 failures: should be critical /
        # Despues de 5 fallas: deberia ser critico
        for _ in range(2):
            scrape_status = update_status_after_scrape(
                scrape_status, success=False, latency=15.0, status_code=429,
            )

        result = check_vital_signs(default_config, scrape_status)
        assert result["mode"] == "critical"
        assert result["recommended_delay_seconds"] >= 1800


# ---------------------------------------------------------------------------
# Test 2: Hash chain broken -> critical mode /
# Test 2: Hash chain rota -> modo critico
# ---------------------------------------------------------------------------

class TestHashChainBrokenCritical:
    """Verify that a broken hash chain immediately triggers critical mode.
    Bilingual: Verifica que una cadena de hashes rota dispara modo critico inmediatamente.
    """

    def test_hash_chain_broken_triggers_critical(
        self, default_config: Dict[str, Any]
    ) -> None:
        """Hash chain validity = False should always produce critical mode.
        Bilingual: Validez de hash chain = False siempre debe producir modo critico.

        Args:
            default_config: Test configuration fixture.
        """
        # Even with zero failures, broken hash chain = critical /
        # Incluso con cero fallas, hash chain rota = critico
        scrape_status: Dict[str, Any] = {
            "consecutive_failures": 0,
            "success_history": [True, True, True, True, True],
            "latency_history": [1.0, 1.5, 1.2, 0.9, 1.1],
            "hash_chain_valid": False,  # BROKEN / ROTA
        }

        result: Dict[str, Any] = check_vital_signs(default_config, scrape_status)

        assert result["mode"] == "critical", (
            f"Expected critical mode for broken hash chain, got {result['mode']}"
        )
        assert result["recommended_delay_seconds"] >= 1800
        assert result["alert_needed"] is True
        assert "hash_chain_broken" in result["metrics"]["critical_reasons"]

    def test_hash_chain_valid_no_critical(
        self, default_config: Dict[str, Any]
    ) -> None:
        """Valid hash chain with healthy metrics should remain normal.
        Bilingual: Hash chain valida con metricas sanas debe permanecer normal.

        Args:
            default_config: Test configuration fixture.
        """
        scrape_status: Dict[str, Any] = {
            "consecutive_failures": 0,
            "success_history": [True, True, True],
            "latency_history": [1.0, 1.5, 1.2],
            "hash_chain_valid": True,
        }

        result: Dict[str, Any] = check_vital_signs(default_config, scrape_status)
        assert result["mode"] == "normal"


# ---------------------------------------------------------------------------
# Test 3: Empty proxy pool -> fallback to direct or alert /
# Test 3: Pool de proxies vacio -> fallback a directo o alerta
# ---------------------------------------------------------------------------

class TestEmptyProxyPool:
    """Verify behavior when proxy pool is completely empty.
    Bilingual: Verifica comportamiento cuando el pool de proxies esta completamente vacio.
    """

    def test_empty_proxy_pool_returns_none_proxy(self) -> None:
        """With no proxies configured, get_proxy_and_ua returns None proxy dict.
        Bilingual: Sin proxies configurados, get_proxy_and_ua retorna None como proxy dict.
        """
        manager = ProxyAndUAManager(
            proxy_list=[],
            user_agents=_DEFAULT_USER_AGENTS,
        )

        proxy_dict, ua = manager.get_proxy_and_ua()

        # Should return None for proxy (direct connection) /
        # Deberia retornar None para proxy (conexion directa)
        assert proxy_dict is None
        assert isinstance(ua, str)
        assert len(ua) > 0

    def test_proxy_pool_with_entries_returns_proxy(self) -> None:
        """With proxies configured, should return a valid proxy dict.
        Bilingual: Con proxies configurados, debe retornar un proxy dict valido.
        """
        test_proxies: List[str] = ["http://proxy1:8080", "http://proxy2:8080"]
        manager = ProxyAndUAManager(
            proxy_list=test_proxies,
            user_agents=_DEFAULT_USER_AGENTS,
        )

        proxy_dict, ua = manager.get_proxy_and_ua()

        assert proxy_dict is not None
        assert "http" in proxy_dict
        assert "https" in proxy_dict
        assert isinstance(ua, str)

    def test_proxy_rotation_on_trigger_codes(self) -> None:
        """Verify proxy rotates when 429/403/5xx status is notified.
        Bilingual: Verifica que el proxy rota cuando se notifica status 429/403/5xx.
        """
        test_proxies: List[str] = [
            "http://proxy1:8080",
            "http://proxy2:8080",
            "http://proxy3:8080",
        ]
        manager = ProxyAndUAManager(
            proxy_list=test_proxies,
            user_agents=_DEFAULT_USER_AGENTS,
            rotation_interval=100,  # High interval to avoid time-based rotation
        )

        # Get initial proxy / Obtener proxy inicial
        proxy1, _ = manager.get_proxy_and_ua()
        initial_proxy_url: str = proxy1["http"]

        # Notify 429 to trigger rotation / Notificar 429 para disparar rotacion
        manager.notify_response_code(429)

        # Next proxy should be different / Siguiente proxy debe ser diferente
        proxy2, _ = manager.get_proxy_and_ua()
        assert proxy2["http"] != initial_proxy_url, (
            "Proxy should rotate after 429 status notification"
        )


# ---------------------------------------------------------------------------
# Test 4: Rate limiter blocks bursts > capacity /
# Test 4: Rate limiter bloquea bursts > capacidad
# ---------------------------------------------------------------------------

class TestRateLimiterBlocksBursts:
    """Verify that the rate limiter blocks burst requests exceeding capacity.
    Bilingual: Verifica que el rate limiter bloquea requests en rafaga que exceden capacidad.
    """

    def test_burst_within_capacity_succeeds(self) -> None:
        """Requests within burst capacity should succeed immediately.
        Bilingual: Requests dentro de capacidad de burst deben tener exito inmediatamente.
        """
        limiter = TokenBucketRateLimiter(capacity=3, refill_seconds=10.0)

        # 3 tokens available initially / 3 tokens disponibles inicialmente
        assert limiter.try_acquire() is True
        assert limiter.try_acquire() is True
        assert limiter.try_acquire() is True

    def test_burst_exceeding_capacity_blocked(self) -> None:
        """Fourth request after consuming 3 tokens should be blocked.
        Bilingual: Cuarto request despues de consumir 3 tokens debe ser bloqueado.
        """
        limiter = TokenBucketRateLimiter(capacity=3, refill_seconds=10.0)

        # Consume all 3 tokens / Consumir los 3 tokens
        assert limiter.try_acquire() is True
        assert limiter.try_acquire() is True
        assert limiter.try_acquire() is True

        # 4th should fail / El 4to debe fallar
        assert limiter.try_acquire() is False

    def test_wait_blocks_when_no_tokens(self) -> None:
        """wait() should block until a token is available via refill.
        Bilingual: wait() debe bloquear hasta que un token este disponible via reposicion.
        """
        # Use minimum refill for faster test / Usar refill minimo para test mas rapido
        limiter = TokenBucketRateLimiter(capacity=1, refill_seconds=8.0)

        # Consume the single token / Consumir el unico token
        waited_initial: float = limiter.wait()
        assert waited_initial == 0.0  # First token available immediately

        # Next wait should block / Siguiente wait debe bloquear
        start: float = time.monotonic()
        waited: float = limiter.wait()
        elapsed: float = time.monotonic() - start

        # Should have waited approximately refill_seconds /
        # Deberia haber esperado aproximadamente refill_seconds
        assert elapsed >= 7.0, (
            f"Expected wait of ~8s, only waited {elapsed:.2f}s"
        )

    def test_ethical_minimum_enforced(self) -> None:
        """Refill rate below 8 seconds should be clamped to 8 seconds.
        Bilingual: Tasa de reposicion por debajo de 8 segundos debe fijarse en 8 segundos.
        """
        limiter = TokenBucketRateLimiter(capacity=3, refill_seconds=1.0)
        # Should enforce minimum 8s / Deberia forzar minimo 8s
        assert limiter.refill_seconds >= 8.0

    def test_rapid_burst_blocked_beyond_capacity(self) -> None:
        """Rapid-fire try_acquire calls beyond capacity all fail.
        Bilingual: Llamadas rapidas try_acquire mas alla de capacidad todas fallan.
        """
        limiter = TokenBucketRateLimiter(capacity=3, refill_seconds=10.0)

        # Exhaust all tokens / Agotar todos los tokens
        results: List[bool] = [limiter.try_acquire() for _ in range(6)]

        # First 3 should succeed, remaining 3 should fail /
        # Los primeros 3 deben tener exito, los 3 restantes deben fallar
        assert results[:3] == [True, True, True]
        assert results[3:] == [False, False, False]


# ---------------------------------------------------------------------------
# Test: User-Agent pool validation /
# Test: Validacion del pool de User-Agents
# ---------------------------------------------------------------------------

class TestUserAgentPool:
    """Validate the User-Agent pool meets minimum requirements.
    Bilingual: Valida que el pool de User-Agents cumple requisitos minimos.
    """

    def test_minimum_50_user_agents(self) -> None:
        """Built-in pool should contain at least 50 User-Agent strings.
        Bilingual: El pool integrado debe contener al menos 50 cadenas User-Agent.
        """
        assert len(_DEFAULT_USER_AGENTS) >= 50, (
            f"Expected >= 50 User-Agents, got {len(_DEFAULT_USER_AGENTS)}"
        )

    def test_all_user_agents_are_non_empty(self) -> None:
        """All User-Agent strings should be non-empty.
        Bilingual: Todas las cadenas User-Agent deben ser no vacias.
        """
        for i, ua in enumerate(_DEFAULT_USER_AGENTS):
            assert isinstance(ua, str) and len(ua.strip()) > 10, (
                f"User-Agent at index {i} is empty or too short: {ua!r}"
            )

    def test_random_ua_selection(self) -> None:
        """Multiple calls should return varying User-Agents.
        Bilingual: Multiples llamadas deben retornar User-Agents variados.
        """
        manager = ProxyAndUAManager(proxy_list=[], user_agents=_DEFAULT_USER_AGENTS)
        uas_seen: set = set()
        for _ in range(20):
            _, ua = manager.get_proxy_and_ua()
            uas_seen.add(ua)

        # With 50+ UAs, 20 samples should produce at least 5 unique /
        # Con 50+ UAs, 20 muestras deben producir al menos 5 unicos
        assert len(uas_seen) >= 5, (
            f"Expected varied UA selection, got only {len(uas_seen)} unique out of 20"
        )
