"""Proxy rotation and validation resilience tests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import httpx
import pytest

from centinel import proxy_handler


@dataclass
class _DummyResponse:
    status_code: int


class _DummyClient:
    def __init__(self, responses: dict[str, int], errors: dict[str, Exception]):
        self._responses = responses
        self._errors = errors

    def get(self, _url: str, *, proxies: str):
        if proxies in self._errors:
            raise self._errors[proxies]
        return _DummyResponse(status_code=self._responses.get(proxies, 200))

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False


def test_proxy_validation_rejects_403_and_errors(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Español: Valida rechazo de proxy 403 y errores de conexión en validación.

    English: Validate rejection of 403 proxies and connection errors during validation.
    """
    responses = {
        "http://proxy-1.local:8080": 200,
        "http://proxy-2.local:8080": 403,
    }
    errors = {"http://proxy-3.local:8080": httpx.RequestError("boom")}

    def dummy_client(*_args, **_kwargs):
        return _DummyClient(responses, errors)

    monkeypatch.setattr(proxy_handler.httpx, "Client", dummy_client)

    validator = proxy_handler.ProxyValidator(test_url="https://cne.hn/health")
    with caplog.at_level("WARNING"):
        validated = validator.validate(list(responses.keys()) + list(errors.keys()))

    assert [proxy.url for proxy in validated] == ["http://proxy-1.local:8080"]
    assert "proxy_validation_failed" in caplog.text
    assert "proxy_validation_error" in caplog.text


def test_proxy_rotator_round_robin_and_fallback_to_direct(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Español: Verifica rotación round-robin y fallback a directo si fallan.

    English: Verify round-robin rotation and fallback to direct when proxies fail.
    """
    proxies: List[proxy_handler.ProxyInfo] = [
        proxy_handler.ProxyInfo(url="http://proxy-1.local:8080"),
        proxy_handler.ProxyInfo(url="http://proxy-2.local:8080"),
    ]
    rotator = proxy_handler.ProxyRotator(
        mode="rotate",
        proxies=proxies,
        proxy_urls=[proxy.url for proxy in proxies],
        rotation_strategy="round_robin",
        rotation_every_n=1,
    )

    first = rotator.get_proxy_for_request()
    second = rotator.get_proxy_for_request()
    assert first != second

    with caplog.at_level("WARNING"):
        for _ in range(3):
            rotator.mark_failure(first, "proxy 403")
        for _ in range(3):
            rotator.mark_failure(second, "proxy timeout")

    assert rotator.mode == "direct"
    assert rotator.get_proxy_for_request() is None
    assert "proxy_fallback_direct" in caplog.text


def test_proxy_rotator_refreshes_pool_when_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Español: Asegura refresco de pool y recuperación cuando hay proxies válidos.

    English: Ensure pool refresh and recovery when valid proxies are available.
    """
    rotator = proxy_handler.ProxyRotator(
        mode="rotate",
        proxies=[],
        proxy_urls=["http://proxy-1.local:8080"],
        rotation_strategy="round_robin",
        rotation_every_n=1,
    )

    class DummyValidator:
        def validate(self, _proxies):
            return [proxy_handler.ProxyInfo(url="http://proxy-1.local:8080")]

    assert rotator.refresh_proxies(DummyValidator()) is True
    assert rotator.mode == "rotate"
    assert rotator.get_proxy_for_request() == "http://proxy-1.local:8080"
