"""Retry and download resilience tests using responses."""

from __future__ import annotations

import random
from typing import Any

import pytest
import requests
import responses

from centinel.downloader import (
    RetryConfig,
    RetryPolicy,
    RetryableExceptionError,
    request_json_with_retry,
    request_with_retry,
)
from scripts.download_and_hash import build_request_headers, fetch_with_retry


def test_retry_policy_computes_exponential_backoff_with_jitter() -> None:
    """Español: Valida backoff exponencial con jitter determinístico.

    English: Validate exponential backoff with deterministic jitter.
    """
    policy = RetryPolicy(
        max_attempts=3,
        backoff_base=1.0,
        backoff_multiplier=2.0,
        max_delay=10.0,
        jitter_min=0.1,
        jitter_max=0.1,
    )

    values = iter([0.1, 1.05])

    def fake_uniform(*_: Any) -> float:
        return next(values)

    original_uniform = random.uniform
    random.uniform = fake_uniform
    try:
        delay = policy.compute_delay(2)
    finally:
        random.uniform = original_uniform

    assert delay == pytest.approx(2.0 * 1.05)


def test_build_request_headers_low_profile_selection() -> None:
    """Español: Verifica headers low-profile con selección aleatoria controlada.

    English: Verify low-profile headers with controlled random selection.
    """
    config = {"headers": {"Accept": "application/json"}}
    low_profile = {
        "enabled": True,
        "user_agents": ["UA-1", "UA-2"],
        "accept_languages": ["es-HN"],
        "referers": ["https://cne.hn"],
    }
    rng = random.Random(7)

    headers = build_request_headers(config, low_profile, rng)

    assert headers["Accept"] == "application/json"
    assert headers["User-Agent"] in low_profile["user_agents"]
    assert headers["Accept-Language"] == "es-HN"
    assert headers["Referer"] == "https://cne.hn"


@responses.activate
def test_request_with_retry_retries_429_503_and_preserves_headers(
    retry_config: RetryConfig,
    sample_headers: dict[str, str],
) -> None:
    """Español: Comprueba reintentos en 429/503 y headers persistentes.

    English: Confirm retries on 429/503 and persistent headers across attempts.
    """
    url = "https://cne.hn/api/snapshot"
    seen_headers: list[dict[str, str]] = []
    call_state = {"count": 0}

    def callback(request):
        call_state["count"] += 1
        seen_headers.append(dict(request.headers))
        if call_state["count"] == 1:
            return (429, {}, "rate limited")
        if call_state["count"] == 2:
            return (503, {}, "service unavailable")
        return (200, {}, "ok")

    responses.add_callback(responses.GET, url, callback=callback)

    session = requests.Session()
    try:
        response = request_with_retry(
            session,
            url,
            retry_config=retry_config,
            timeout=1.0,
            headers=sample_headers,
        )
    finally:
        session.close()

    assert response.status_code == 200
    assert len(seen_headers) == 3
    for headers in seen_headers:
        assert headers.get("User-Agent") == sample_headers["User-Agent"]
        assert headers.get("Accept-Language") == sample_headers["Accept-Language"]
        assert headers.get("Referer") == sample_headers["Referer"]


@responses.activate
def test_request_with_retry_retries_timeout_until_max_attempts(
    retry_config: RetryConfig,
) -> None:
    """Español: Asegura reintentos ante timeout y respeta max_attempts.

    English: Ensure timeout retries respect max_attempts limits.
    """
    url = "https://cne.hn/api/timeout"
    responses.add(responses.GET, url, body=requests.exceptions.ReadTimeout("slow"))

    session = requests.Session()
    try:
        with pytest.raises(RetryableExceptionError):
            request_with_retry(
                session,
                url,
                retry_config=retry_config,
                timeout=1.0,
            )
    finally:
        session.close()

    assert len(responses.calls) == 2


@responses.activate
def test_request_json_with_retry_recovers_from_malformed_json(
    retry_config: RetryConfig,
) -> None:
    """Español: Reintenta JSON malformado y recupera respuesta válida.

    English: Retry on malformed JSON and recover with a valid payload.
    """
    url = "https://cne.hn/api/json"
    responses.add(responses.GET, url, body="{bad json", status=200)
    responses.add(responses.GET, url, json={"ok": True}, status=200)

    session = requests.Session()
    try:
        response, payload = request_json_with_retry(
            session,
            url,
            retry_config=retry_config,
            timeout=1.0,
        )
    finally:
        session.close()

    assert response.status_code == 200
    assert payload == {"ok": True}
    assert len(responses.calls) == 2


@responses.activate
def test_fetch_with_retry_uses_session_and_headers(
    monkeypatch: pytest.MonkeyPatch,
    retry_config: RetryConfig,
    sample_headers: dict[str, str],
) -> None:
    """Español: Verifica que fetch_with_retry reutiliza sesión y headers.

    English: Verify fetch_with_retry reuses session and headers.
    """
    url = "https://cne.hn/api/fetch"
    captured: list[dict[str, str]] = []

    def callback(request):
        captured.append(dict(request.headers))
        return (200, {}, "ok")

    responses.add_callback(responses.GET, url, callback=callback)

    monkeypatch.setattr(
        "scripts.download_and_hash.load_retry_config", lambda _: retry_config
    )

    session = requests.Session()
    try:
        response = fetch_with_retry(
            url,
            timeout=1.0,
            headers=sample_headers,
            session=session,
        )
    finally:
        session.close()

    assert response.status_code == 200
    assert captured
    assert captured[0].get("User-Agent") == sample_headers["User-Agent"]
