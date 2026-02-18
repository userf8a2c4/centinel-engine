"""Integration-oriented tests for scheduler guardrails.

Bilingual: Pruebas orientadas a integración para las barreras del scheduler.
"""

from __future__ import annotations

import time
from typing import Any, Callable

from centinel_engine import proxy_manager
from centinel_engine.proxy_manager import ProxyAndUAManager
from centinel_engine.rate_limiter import TokenBucketRateLimiter
from centinel_engine.vital_signs import check_vital_signs


class _DummyProxyRotator:
    """Small deterministic proxy rotator for tests.

    Bilingual: Rotador determinístico pequeño de proxies para pruebas.
    """

    def __init__(self) -> None:
        self.mode = "round_robin"
        self.rotation_every_n = 1
        self._requests_since_rotation = 0
        self._items = ["http://proxy-a:8080", "http://proxy-b:8080"]
        self._index = -1

    def get_proxy_for_request(self) -> str:
        """Return next proxy URL in deterministic order.

        Bilingual: Retorna la siguiente URL de proxy en orden determinístico.

        Returns:
            Proxy URL string.
        """
        self._requests_since_rotation += 1
        if self._requests_since_rotation >= self.rotation_every_n:
            self._requests_since_rotation = 0
            self._index = (self._index + 1) % len(self._items)
        return self._items[self._index]


def _scheduler_loop_backup_hook(scrape_ok: bool, backup_hook: Callable[[], dict[str, Any]]) -> None:
    """Run backup hook on success path and always again in finalizer.

    Bilingual: Ejecuta el hook de backup en ruta de éxito y siempre otra vez
    en el finalizador.

    Args:
        scrape_ok: Simulated scrape success state.
        backup_hook: Backup function to execute.
    """
    try:
        if scrape_ok:
            backup_hook()
    finally:
        # Fail-safe backup regardless of scrape result /
        # Respaldo fail-safe independientemente del resultado
        backup_hook()


def test_rate_limiter_blocks_burst() -> None:
    """Rate limiter must block burst traffic after token depletion.

    Bilingual: El rate limiter debe bloquear tráfico en ráfaga tras agotar tokens.
    """
    limiter = TokenBucketRateLimiter(rate_interval=0.12, burst=1, min_interval=0.0, max_interval=1.0)

    start = time.monotonic()
    for _ in range(5):
        limiter.wait()
    elapsed = time.monotonic() - start

    assert elapsed >= 0.35


def test_proxy_rotation_on_429(monkeypatch) -> None:
    """429 handling should force proxy rotation and reselect User-Agent.

    Bilingual: El manejo de 429 debe forzar rotación de proxy y reselección de User-Agent.
    """
    ua_values = ["UA-A", "UA-B"]
    index = {"value": 0}

    def _det_choice(pool: list[str]) -> str:
        """Return deterministic alternating UA values.

        Bilingual: Retorna valores UA alternados de forma determinística.

        Args:
            pool: Candidate User-Agent pool.

        Returns:
            Selected User-Agent string.
        """
        current = ua_values[index["value"] % len(ua_values)]
        index["value"] += 1
        return current if current in pool else pool[0]

    monkeypatch.setattr(proxy_manager.secrets, "choice", _det_choice)

    manager = ProxyAndUAManager(proxy_rotator=_DummyProxyRotator(), rotation_every_n=1, ua_pool=list(ua_values))
    first_proxy, first_ua = manager.rotate_proxy_and_ua()

    assert manager.notify_response(429) is True
    second_proxy, second_ua = manager.rotate_proxy_and_ua(force_proxy_rotation=True)

    assert first_proxy != second_proxy
    assert first_ua != second_ua


def test_backup_called_after_scrape() -> None:
    """Backup hook should run after successful scrape and again in finalizer.

    Bilingual: El hook de backup debe correr tras scrape exitoso y otra vez en finalizador.
    """
    calls: list[int] = []

    def _backup_stub() -> dict[str, Any]:
        """Track backup hook invocations in deterministic way.

        Bilingual: Registra invocaciones del hook de backup de forma determinística.

        Returns:
            Simulated backup metadata.
        """
        calls.append(1)
        return {"local": True}

    _scheduler_loop_backup_hook(scrape_ok=True, backup_hook=_backup_stub)

    assert len(calls) == 2


def test_vital_signs_triggers_conservative() -> None:
    """Four consecutive failures should trigger conservative mode delay.

    Bilingual: Cuatro fallos consecutivos deben activar delay en modo conservador.
    """
    config = {
        "scrape_interval_seconds": 300,
        "consecutive_failures_conservative": 3,
        "consecutive_failures_critical": 5,
    }
    status = {
        "consecutive_failures": 4,
        "success_history": [False, False, False, False],
        "latency_history": [1.0, 1.1, 1.2, 1.3],
        "hash_chain_valid": True,
    }

    vital_state = check_vital_signs(config, status)

    assert vital_state["mode"] == "conservative"
    assert int(vital_state["recommended_delay_seconds"]) >= 600
