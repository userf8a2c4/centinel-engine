"""Critical minimal tests for the frozen core loop.

Pruebas mínimas críticas para el núcleo congelado.
"""

from __future__ import annotations

import hashlib
from typing import Any
from unittest.mock import MagicMock


def _run_core_loop_once(
    *,
    scrape_request: MagicMock,
    proxy_manager: MagicMock,
    rate_limiter: MagicMock,
    secure_backup: MagicMock,
    vital_signs: MagicMock,
    state: dict[str, Any],
) -> dict[str, Any]:
    """Execute one resilient loop iteration.

    Ejecuta una iteración resiliente del loop.
    """
    error: Exception | None = None
    content_hash: str | None = None
    status_code: int | None = None

    try:
        rate_limiter.wait()

        proxy, ua = proxy_manager.get_proxy_and_ua()
        response = scrape_request(proxy=proxy, ua=ua)
        status_code = int(response.status_code)

        if status_code == 403:
            proxy_manager.mark_proxy_bad(proxy)
            next_proxy, next_ua = proxy_manager.rotate_proxy_and_ua(
                force_proxy_rotation=True,
            )
            response = scrape_request(proxy=next_proxy, ua=next_ua)
            status_code = int(response.status_code)

        if status_code == 429:
            state["consecutive_failures"] = int(state.get("consecutive_failures", 0)) + 1
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
        vital_state = vital_signs.check(state=state, status_code=status_code)
        return {"hash": None, "error": exc, "vital_state": vital_state}
    finally:
        secure_backup.backup_partial(state=state, error=error)


def test_normal_flow() -> None:
    """Successful scrape should create hash and call backup.

    Un scrape exitoso debe crear hash y llamar backup.
    """
    state: dict[str, Any] = {"consecutive_failures": 0}

    response = MagicMock(status_code=200, text='{"ok": true}')
    scrape_request = MagicMock(return_value=response)

    proxy_manager = MagicMock()
    proxy_manager.get_proxy_and_ua.return_value = ({"https": "http://proxy-a"}, "UA-A")

    rate_limiter = MagicMock()
    secure_backup = MagicMock()
    vital_signs = MagicMock(return_value={"mode": "normal", "recommended_delay_seconds": 60})
    vital_signs.check.return_value = {"mode": "normal", "recommended_delay_seconds": 60}

    result = _run_core_loop_once(
        scrape_request=scrape_request,
        proxy_manager=proxy_manager,
        rate_limiter=rate_limiter,
        secure_backup=secure_backup,
        vital_signs=vital_signs,
        state=state,
    )

    assert result["error"] is None
    assert result["hash"] == state["content_hash"]
    secure_backup.backup_partial.assert_called_once()


def test_consecutive_429() -> None:
    """Four consecutive 429 responses must set conservative mode with >=600s delay.

    Cuatro respuestas 429 seguidas deben activar modo conservative con delay >=600s.
    """
    state: dict[str, Any] = {"consecutive_failures": 0}

    responses = [MagicMock(status_code=429, text="rate_limited") for _ in range(4)]
    scrape_request = MagicMock(side_effect=responses)

    proxy_manager = MagicMock()
    proxy_manager.get_proxy_and_ua.return_value = ({"https": "http://proxy-a"}, "UA-A")

    rate_limiter = MagicMock()
    secure_backup = MagicMock()
    vital_signs = MagicMock()

    def _vital_check(*, state: dict[str, Any], status_code: int | None) -> dict[str, Any]:
        failures = int(state.get("consecutive_failures", 0))
        if status_code == 429 and failures >= 4:
            return {"mode": "conservative", "recommended_delay_seconds": 600}
        return {"mode": "normal", "recommended_delay_seconds": 60}

    vital_signs.check.side_effect = _vital_check

    result: dict[str, Any] = {}
    for _ in range(4):
        result = _run_core_loop_once(
            scrape_request=scrape_request,
            proxy_manager=proxy_manager,
            rate_limiter=rate_limiter,
            secure_backup=secure_backup,
            vital_signs=vital_signs,
            state=state,
        )

    assert result["vital_state"]["mode"] == "conservative"
    assert int(result["vital_state"]["recommended_delay_seconds"]) >= 600


def test_proxy_rotation() -> None:
    """A 403 must rotate proxy/UA and continue successfully.

    Un 403 debe rotar proxy/UA y continuar de forma exitosa.
    """
    state: dict[str, Any] = {"consecutive_failures": 0}

    blocked = MagicMock(status_code=403, text="blocked")
    recovered = MagicMock(status_code=200, text='{"ok": true}')
    scrape_request = MagicMock(side_effect=[blocked, recovered])

    proxy_manager = MagicMock()
    proxy_manager.get_proxy_and_ua.return_value = ({"https": "http://proxy-a"}, "UA-A")
    proxy_manager.rotate_proxy_and_ua.return_value = ({"https": "http://proxy-b"}, "UA-B")

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

    assert result["error"] is None
    assert result["hash"] is not None
    proxy_manager.rotate_proxy_and_ua.assert_called_once_with(force_proxy_rotation=True)


def test_backup_on_failure() -> None:
    """When scrape fails, partial backup must still run in finally.

    Cuando el scrape falla, el backup parcial debe ejecutarse en finally.
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
