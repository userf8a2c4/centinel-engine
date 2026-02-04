"""Proxy rotation and validation tests."""

from __future__ import annotations

import logging

import pytest

from centinel import proxy_handler


class DummyResponse:
    """Español: Respuesta simple para simular httpx.

    English: Simple response to simulate httpx.
    """

    def __init__(self, status_code: int):
        self.status_code = status_code


def test_proxy_validator_filters_invalid_proxies(caplog, monkeypatch) -> None:
    """Español: Valida proxies y filtra respuestas 4xx con logs esperados.

    English: Validate proxies and filter 4xx responses with expected logs.
    """
    calls = []

    def fake_get(_self, _url, proxies=None):
        calls.append(proxies)
        if proxies == "http://ok.proxy":
            return DummyResponse(200)
        return DummyResponse(403)

    monkeypatch.setattr("httpx.Client.get", fake_get, raising=True)

    validator = proxy_handler.ProxyValidator(logger=logging.getLogger("proxy.test"))
    with caplog.at_level(logging.INFO):
        validated = validator.validate(["http://ok.proxy", "http://bad.proxy"])

    assert [proxy.url for proxy in validated] == ["http://ok.proxy"]
    assert any("proxy_validation_ok" in record.message for record in caplog.records)
    assert any(
        "proxy_validation_failed" in record.message for record in caplog.records
    )
    assert calls == ["http://ok.proxy", "http://bad.proxy"]


def test_proxy_rotator_round_robin_and_fallback(caplog) -> None:
    """Español: Verifica round-robin, fallbacks y modo directo.

    English: Verify round-robin rotation, fallbacks, and direct mode.
    """
    logger = logging.getLogger("proxy.rotator")
    proxies = [
        proxy_handler.ProxyInfo(url="http://proxy1"),
        proxy_handler.ProxyInfo(url="http://proxy2"),
    ]
    rotator = proxy_handler.ProxyRotator(
        mode="rotate",
        proxies=proxies,
        proxy_urls=[p.url for p in proxies],
        rotation_strategy="round_robin",
        rotation_every_n=1,
        logger=logger,
    )

    assert rotator.get_proxy_for_request() == "http://proxy1"
    assert rotator.get_proxy_for_request() == "http://proxy2"
    assert rotator.get_proxy_for_request() == "http://proxy1"

    with caplog.at_level(logging.WARNING):
        rotator.mark_failure("http://proxy1", "403")
        rotator.mark_failure("http://proxy1", "403")
        rotator.mark_failure("http://proxy1", "403")
        rotator.mark_failure("http://proxy2", "403")
        rotator.mark_failure("http://proxy2", "403")
        rotator.mark_failure("http://proxy2", "403")

    assert rotator.mode == "direct"
    assert any("proxy_fallback_direct" in record.message for record in caplog.records)


def test_proxy_rotator_refreshes_pool(monkeypatch) -> None:
    """Español: Refresca pool cuando todos los proxies están agotados.

    English: Refresh proxy pool when all proxies are exhausted.
    """
    logger = logging.getLogger("proxy.refresh")
    rotator = proxy_handler.ProxyRotator(
        mode="rotate",
        proxies=[],
        proxy_urls=["http://proxy1"],
        rotation_strategy="round_robin",
        rotation_every_n=1,
        logger=logger,
    )

    class DummyValidator:
        """Español: Validador dummy para proxies.

        English: Dummy validator for proxies.
        """

        def validate(self, proxies):
            return [proxy_handler.ProxyInfo(url=proxies[0])]

    validator = DummyValidator()

    assert rotator.refresh_proxies(validator) is True
    assert rotator.active_proxies


def test_get_proxy_rotator_falls_back_to_direct(monkeypatch, caplog) -> None:
    """Español: Asegura fallback a directo si ninguna validación pasa.

    English: Ensure fallback to direct when no proxies validate.
    """
    proxy_handler._ROTATOR = None

    def fake_load_proxy_config():
        return {
            "mode": "rotate",
            "rotation_strategy": "round_robin",
            "rotation_every_n": 1,
            "proxy_timeout_seconds": 1.0,
            "test_url": "https://example.com",
            "proxies": ["http://proxy1"],
        }

    class FakeValidator:
        """Español: Validador que falla todas las validaciones.

        English: Validator that fails all validations.
        """

        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        def validate(self, _proxies):
            return []

    monkeypatch.setattr(proxy_handler, "load_proxy_config", fake_load_proxy_config)
    monkeypatch.setattr(proxy_handler, "ProxyValidator", FakeValidator)

    with caplog.at_level(logging.WARNING):
        rotator = proxy_handler.get_proxy_rotator(logging.getLogger("proxy.test"))

    assert rotator.mode == "direct"
    assert any(
        "proxy_startup_no_valid_proxies" in record.message for record in caplog.records
    )
