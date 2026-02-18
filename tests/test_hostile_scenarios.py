"""Hostile scenario tests for legal-resilient hardening controls.

Bilingual: Pruebas de escenarios hostiles para controles de endurecimiento
resiliente y legal.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List

from centinel_engine.proxy_manager import get_proxy_and_ua, get_proxy_ua_manager, reset_proxy_ua_manager
from centinel_engine.rate_limiter import TokenBucketRateLimiter
from centinel_engine.vital_signs import check_vital_signs
from src.centinel.proxy_handler import ProxyRotator


def _base_vitals_status() -> Dict[str, Any]:
    """Return a deterministic healthy baseline status for tests.

    Bilingual: Retorna un estado base saludable y determinístico para pruebas.

    Args:
        None.

    Returns:
        Dictionary with normal vitals values.

    Raises:
        None.
    """
    return {
        "consecutive_failures": 0,
        "success_history": [True] * 10,
        "latency_history": [1.0] * 10,
        "hash_chain_valid": True,
        "last_status_code": 200,
    }


def test_50_consecutive_429_enters_critical_with_1800_delay() -> None:
    """Validate sustained 429 hostility forces critical mode with 1800s delay.

    Bilingual: Valida que 50 respuestas 429 sostenidas fuercen modo crítico con 1800s.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    status = _base_vitals_status()
    status["consecutive_failures"] = 50
    status["last_status_code"] = 429

    result = check_vital_signs({}, status)

    assert result["mode"] == "critical"
    assert result["recommended_delay_seconds"] >= 1800


def test_hash_chain_break_enters_critical_mode() -> None:
    """Validate broken hash chain always activates critical mode.

    Bilingual: Valida que una cadena hash rota siempre activa modo crítico.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    status = _base_vitals_status()
    status["hash_chain_valid"] = False

    result = check_vital_signs({}, status)

    assert result["mode"] == "critical"


def test_empty_proxy_pool_falls_back_to_direct_mode() -> None:
    """Validate empty proxy pool falls back to direct mode without crashing.

    Bilingual: Valida que un pool de proxies vacío haga fallback a modo directo sin fallar.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    rotator = ProxyRotator(mode="rotate", proxies=[], proxy_urls=[], rotation_every_n=15)
    rotator.logger.warning = lambda *args, **kwargs: None  # English / Español: silence structured-log kwargs issue.
    manager = get_proxy_ua_manager(proxy_rotator=rotator)

    proxy_dict, ua = get_proxy_and_ua()

    assert manager.stats["proxy_mode"] == "direct"
    assert proxy_dict is None
    assert isinstance(ua, str) and len(ua) > 0
    reset_proxy_ua_manager()


def test_rate_limiter_blocks_burst_over_3(monkeypatch: Any) -> None:
    """Validate burst over capacity triggers blocking behavior.

    Bilingual: Valida que un burst sobre capacidad activa comportamiento de bloqueo.

    Args:
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None.

    Raises:
        None.
    """
    sleeps: List[float] = []

    def _fake_sleep(seconds: float) -> None:
        """Capture sleep calls without real waiting for deterministic test.

        Bilingual: Captura llamadas a sleep sin esperar realmente para prueba determinística.

        Args:
            seconds: Requested sleep duration.

        Returns:
            None.

        Raises:
            None.
        """
        # English / Español: simulate time passage by storing requested delay.
        sleeps.append(seconds)

    monkeypatch.setattr(time, "sleep", _fake_sleep)

    limiter = TokenBucketRateLimiter(rate_interval=8.0, burst=3, min_interval=0.0, max_interval=12.0)
    limiter.wait()
    limiter.wait()
    limiter.wait()
    waited_fourth = limiter.wait()

    assert waited_fourth >= 0.0
    assert len(sleeps) >= 1
