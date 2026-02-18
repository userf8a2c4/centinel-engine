"""Minimal critical tests for an integrated resilient core loop.

Pruebas mínimas críticas para un loop principal resiliente integrado.
"""

from __future__ import annotations

import hashlib
from typing import Any
from unittest.mock import MagicMock

import pytest


def _run_core_loop_once(
    *,
    scrape_request: MagicMock,
    proxy_manager: MagicMock,
    rate_limiter: MagicMock,
    secure_backup: MagicMock,
    vital_signs: MagicMock,
    state: dict[str, Any],
) -> dict[str, Any]:
    """Run one loop iteration with fail-safe backup in finally.

    Ejecuta una iteración del loop con backup fail-safe en finally.
    """
    error: Exception | None = None
    content_hash: str | None = None

    try:
        rate_limiter.wait()
        proxy, ua = proxy_manager.get_proxy_and_ua()
        response = scrape_request(proxy=proxy, ua=ua)
        status_code = int(response.status_code)

        if status_code in {429, 403}:
            state["consecutive_failures"] = int(state.get("consecutive_failures", 0)) + 1
            proxy_manager.mark_proxy_bad(proxy)
            proxy_manager.rotate_proxy_and_ua(force_proxy_rotation=True)
        else:
            state["consecutive_failures"] = 0

        if status_code == 200:
            payload = str(response.text).encode("utf-8")
            content_hash = hashlib.sha256(payload).hexdigest()
            state["content_hash"] = content_hash

        vital_state = vital_signs.check(state=state, status_code=status_code)
        return {"hash": content_hash, "error": None, "vital_state": vital_state}
    except Exception as exc:  # noqa: BLE001
        error = exc
        return {"hash": None, "error": exc, "vital_state": vital_signs.check(state=state, status_code=None)}
    finally:
        secure_backup.backup_partial(state=state, error=error)


def test_normal_flow() -> None:
    """Successful scrape should generate hash, call backup, and avoid errors.

    Un scrape exitoso debe generar hash, llamar backup y no producir error.
    """
    state: dict[str, Any] = {"consecutive_failures": 0}

    response = MagicMock()
    response.status_code = 200
    response.text = '{"ok": true}'

    scrape_request = MagicMock(return_value=response)
    proxy_manager = MagicMock()
    proxy_manager.get_proxy_and_ua.return_value = ({"https": "http://proxy-a"}, "UA-A")
    rate_limiter = MagicMock()
    secure_backup = MagicMock()
    vital_signs = MagicMock()
    vital_signs.check.return_value = {"mode": "normal", "recommended_delay_seconds": 60}

    result = _run_core_loop_once(
        scrape_request=scrape_request,
        proxy_manager=proxy_manager,
        rate_limiter=rate_limiter,
        secure_backup=secure_backup,
        vital_signs=vital_signs,
        state=state,
    )

    assert result["hash"] is not None
    assert state["content_hash"] == result["hash"]
    assert result["error"] is None
    secure_backup.backup_partial.assert_called_once()


def test_consecutive_failures() -> None:
    """Four 429 responses should switch to conservative with >=600s delay.

    Cuatro respuestas 429 deben activar modo conservative con delay >=600s.
    """
    state: dict[str, Any] = {"consecutive_failures": 0}

    responses = []
    for _ in range(4):
        r = MagicMock()
        r.status_code = 429
        r.text = "rate_limited"
        responses.append(r)

    scrape_request = MagicMock(side_effect=responses)
    proxy_manager = MagicMock()
    proxy_manager.get_proxy_and_ua.return_value = ({"https": "http://proxy-a"}, "UA-A")
    rate_limiter = MagicMock()
    secure_backup = MagicMock()

    vital_signs = MagicMock()

    def _vital_check(*, state: dict[str, Any], status_code: int | None) -> dict[str, Any]:
        failures = int(state.get("consecutive_failures", 0))
        if failures >= 4 and status_code == 429:
            return {"mode": "conservative", "recommended_delay_seconds": 600}
        return {"mode": "normal", "recommended_delay_seconds": 60}

    vital_signs.check.side_effect = _vital_check

    last_result: dict[str, Any] = {}
    for _ in range(4):
        last_result = _run_core_loop_once(
            scrape_request=scrape_request,
            proxy_manager=proxy_manager,
            rate_limiter=rate_limiter,
            secure_backup=secure_backup,
            vital_signs=vital_signs,
            state=state,
        )

    assert last_result["vital_state"]["mode"] == "conservative"
    assert int(last_result["vital_state"]["recommended_delay_seconds"]) >= 600


def test_proxy_rotation() -> None:
    """A 403 response should rotate proxy and UA and keep loop alive.

    Una respuesta 403 debe rotar proxy y UA sin romper el loop.
    """
    state: dict[str, Any] = {"consecutive_failures": 0}

    response = MagicMock()
    response.status_code = 403
    response.text = "blocked"

    scrape_request = MagicMock(return_value=response)
    proxy_manager = MagicMock()
    proxy_manager.get_proxy_and_ua.return_value = ({"https": "http://proxy-a"}, "UA-A")
    proxy_manager.rotate_proxy_and_ua.return_value = ({"https": "http://proxy-b"}, "UA-B")

    rate_limiter = MagicMock()
    secure_backup = MagicMock()
    vital_signs = MagicMock()
    vital_signs.check.return_value = {"mode": "conservative", "recommended_delay_seconds": 300}

    result = _run_core_loop_once(
        scrape_request=scrape_request,
        proxy_manager=proxy_manager,
        rate_limiter=rate_limiter,
        secure_backup=secure_backup,
        vital_signs=vital_signs,
        state=state,
    )

    assert result["error"] is None
    proxy_manager.rotate_proxy_and_ua.assert_called_once_with(force_proxy_rotation=True)


def test_backup_on_failure() -> None:
    """If scrape fails, partial backup must be called from finally.

    Si el scrape falla, el backup parcial debe llamarse desde finally.
    """
    state: dict[str, Any] = {"consecutive_failures": 0}

    scrape_request = MagicMock(side_effect=RuntimeError("scrape failed"))
    proxy_manager = MagicMock()
    proxy_manager.get_proxy_and_ua.return_value = ({"https": "http://proxy-a"}, "UA-A")

    rate_limiter = MagicMock()
    secure_backup = MagicMock()
    vital_signs = MagicMock()
    vital_signs.check.return_value = {"mode": "critical", "recommended_delay_seconds": 900}

    result = _run_core_loop_once(
        scrape_request=scrape_request,
        proxy_manager=proxy_manager,
        rate_limiter=rate_limiter,
        secure_backup=secure_backup,
        vital_signs=vital_signs,
        state=state,
    )

    assert isinstance(result["error"], RuntimeError)
    secure_backup.backup_partial.assert_called_once()
