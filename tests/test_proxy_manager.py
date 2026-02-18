"""Tests for centinel_engine.proxy_manager (User-Agent pool and proxy rotation).

Bilingual: Pruebas para centinel_engine.proxy_manager (pool de User-Agents y
rotacion de proxies).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from centinel_engine.proxy_manager import (  # noqa: E402
    DEFAULT_ROTATION_EVERY_N,
    ROTATION_TRIGGER_CODES,
    USER_AGENT_POOL,
    ProxyAndUAManager,
    get_proxy_ua_manager,
    reset_proxy_ua_manager,
)


# ---------------------------------------------------------------------------
# Fixtures / Fixtures de prueba
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_singleton() -> None:
    """Reset the global singleton before each test / Reiniciar singleton antes de cada test."""
    reset_proxy_ua_manager()
    yield  # type: ignore[misc]
    reset_proxy_ua_manager()


class MockProxyRotator:
    """Mock proxy rotator for testing / Rotador de proxy mock para testing."""

    def __init__(self) -> None:
        self.mode: str = "round_robin"
        self.rotation_every_n: int = 5
        self._requests_since_rotation: int = 0
        self._proxy_index: int = 0
        self._proxies: List[str] = [
            "http://proxy1:8080",
            "http://proxy2:8080",
            "http://proxy3:8080",
        ]
        self.proxy_timeout_seconds: int = 15

    def get_proxy_for_request(self) -> Optional[str]:
        """Return next proxy / Retorna siguiente proxy."""
        if not self._proxies:
            return None
        proxy = self._proxies[self._proxy_index % len(self._proxies)]
        self._proxy_index += 1
        return proxy


# ---------------------------------------------------------------------------
# Test 1: User-Agent pool / Pool de User-Agents
# ---------------------------------------------------------------------------


class TestUserAgentPool:
    """Tests for the User-Agent pool / Pruebas del pool de User-Agents."""

    def test_pool_has_at_least_50_entries(self) -> None:
        """UA pool contains >= 50 real User-Agent strings.

        Bilingual: Pool de UA contiene >= 50 cadenas User-Agent reales.
        """
        assert len(USER_AGENT_POOL) >= 50

    def test_all_entries_are_strings(self) -> None:
        """All pool entries are non-empty strings.

        Bilingual: Todas las entradas del pool son cadenas no vacias.
        """
        for ua in USER_AGENT_POOL:
            assert isinstance(ua, str)
            assert len(ua) > 10

    def test_entries_look_like_real_uas(self) -> None:
        """Pool entries contain Mozilla/ prefix typical of real browsers.

        Bilingual: Entradas del pool contienen prefijo Mozilla/ tipico de navegadores reales.
        """
        mozilla_count = sum(1 for ua in USER_AGENT_POOL if ua.startswith("Mozilla/5.0"))
        assert mozilla_count == len(USER_AGENT_POOL)

    def test_pool_has_variety(self) -> None:
        """Pool contains multiple browser families (Chrome, Firefox, Safari, Edge).

        Bilingual: Pool contiene multiples familias de navegadores (Chrome, Firefox, Safari, Edge).
        """
        has_chrome = any("Chrome/" in ua and "Edg/" not in ua and "OPR/" not in ua for ua in USER_AGENT_POOL)
        has_firefox = any("Firefox/" in ua for ua in USER_AGENT_POOL)
        has_safari = any("Safari/" in ua and "Chrome/" not in ua for ua in USER_AGENT_POOL)
        has_edge = any("Edg/" in ua for ua in USER_AGENT_POOL)
        assert has_chrome
        assert has_firefox
        assert has_safari
        assert has_edge


# ---------------------------------------------------------------------------
# Test 2: UA rotation / Rotacion de UA
# ---------------------------------------------------------------------------


class TestUARotation:
    """Tests for User-Agent rotation / Pruebas de rotacion de User-Agent."""

    def test_different_ua_each_call(self) -> None:
        """Multiple calls return different UAs (with high probability).

        Bilingual: Multiples llamadas retornan UAs diferentes (con alta probabilidad).
        """
        mgr = ProxyAndUAManager(rotation_every_n=100)
        uas = set()
        for _ in range(20):
            _, ua = mgr.rotate_proxy_and_ua()
            uas.add(ua)
        # With 50+ UAs, 20 calls should produce multiple unique ones /
        # Con 50+ UAs, 20 llamadas deberian producir multiples unicos
        assert len(uas) > 5

    def test_ua_is_from_pool(self) -> None:
        """Returned UA is always from the pool.

        Bilingual: UA retornado siempre es del pool.
        """
        mgr = ProxyAndUAManager(rotation_every_n=100)
        for _ in range(10):
            _, ua = mgr.rotate_proxy_and_ua()
            assert ua in USER_AGENT_POOL


# ---------------------------------------------------------------------------
# Test 3: Proxy rotation / Rotacion de proxy
# ---------------------------------------------------------------------------


class TestProxyRotation:
    """Tests for proxy rotation behavior / Pruebas de comportamiento de rotacion de proxy."""

    def test_no_proxy_in_direct_mode(self) -> None:
        """Without a proxy rotator, proxy_url is always None.

        Bilingual: Sin rotador de proxy, proxy_url siempre es None.
        """
        mgr = ProxyAndUAManager()
        proxy, ua = mgr.rotate_proxy_and_ua()
        assert proxy is None
        assert isinstance(ua, str)

    def test_proxy_returned_when_rotator_present(self) -> None:
        """With a proxy rotator, proxy_url is returned.

        Bilingual: Con rotador de proxy, se retorna proxy_url.
        """
        mock = MockProxyRotator()
        mgr = ProxyAndUAManager(proxy_rotator=mock, rotation_every_n=100)
        proxy, ua = mgr.rotate_proxy_and_ua()
        assert proxy is not None
        assert proxy.startswith("http://")

    def test_forced_rotation(self) -> None:
        """force_proxy_rotation=True triggers immediate rotation.

        Bilingual: force_proxy_rotation=True activa rotacion inmediata.
        """
        mock = MockProxyRotator()
        mgr = ProxyAndUAManager(proxy_rotator=mock, rotation_every_n=1000)
        mgr.rotate_proxy_and_ua(force_proxy_rotation=True)
        assert mgr.stats["total_rotations"] >= 1


# ---------------------------------------------------------------------------
# Test 4: Status code notification / Notificacion de codigo de estado
# ---------------------------------------------------------------------------


class TestStatusNotification:
    """Tests for hostile status code handling / Pruebas de manejo de codigos hostiles."""

    def test_429_triggers_rotation(self) -> None:
        """HTTP 429 triggers forced rotation.

        Bilingual: HTTP 429 activa rotacion forzada.
        """
        mgr = ProxyAndUAManager()
        result = mgr.notify_response(429)
        assert result is True

    def test_403_triggers_rotation(self) -> None:
        """HTTP 403 triggers forced rotation.

        Bilingual: HTTP 403 activa rotacion forzada.
        """
        mgr = ProxyAndUAManager()
        result = mgr.notify_response(403)
        assert result is True

    def test_200_does_not_trigger(self) -> None:
        """HTTP 200 does not trigger rotation.

        Bilingual: HTTP 200 no activa rotacion.
        """
        mgr = ProxyAndUAManager()
        result = mgr.notify_response(200)
        assert result is False

    def test_rotation_trigger_codes_constant(self) -> None:
        """ROTATION_TRIGGER_CODES contains expected codes.

        Bilingual: ROTATION_TRIGGER_CODES contiene codigos esperados.
        """
        assert 429 in ROTATION_TRIGGER_CODES
        assert 403 in ROTATION_TRIGGER_CODES
        assert 200 not in ROTATION_TRIGGER_CODES


# ---------------------------------------------------------------------------
# Test 5: Statistics / Estadisticas
# ---------------------------------------------------------------------------


class TestManagerStats:
    """Tests for manager statistics / Pruebas de estadisticas del gestor."""

    def test_stats_track_requests(self) -> None:
        """Stats count total requests correctly.

        Bilingual: Estadisticas cuentan total de requests correctamente.
        """
        mgr = ProxyAndUAManager()
        mgr.rotate_proxy_and_ua()
        mgr.rotate_proxy_and_ua()
        mgr.rotate_proxy_and_ua()
        assert mgr.stats["total_requests"] == 3

    def test_stats_include_pool_size(self) -> None:
        """Stats report the UA pool size.

        Bilingual: Estadisticas reportan tamano del pool de UA.
        """
        mgr = ProxyAndUAManager()
        assert mgr.stats["ua_pool_size"] >= 50


# ---------------------------------------------------------------------------
# Test 6: Singleton / Singleton
# ---------------------------------------------------------------------------


class TestSingleton:
    """Tests for the global singleton accessor / Pruebas del accessor singleton global."""

    def test_singleton_returns_same_instance(self) -> None:
        """get_proxy_ua_manager() returns the same instance.

        Bilingual: get_proxy_ua_manager() retorna la misma instancia.
        """
        a = get_proxy_ua_manager()
        b = get_proxy_ua_manager()
        assert a is b

    def test_reset_creates_new_instance(self) -> None:
        """reset_proxy_ua_manager() allows creation of a new instance.

        Bilingual: reset_proxy_ua_manager() permite creacion de una nueva instancia.
        """
        a = get_proxy_ua_manager()
        reset_proxy_ua_manager()
        b = get_proxy_ua_manager()
        assert a is not b
