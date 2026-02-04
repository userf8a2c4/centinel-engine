"""Retry and download resilience tests using responses."""

from __future__ import annotations

import json
import random
from typing import Any

import pytest
import requests

from centinel.downloader import (
    RetryConfig,
    RetryPolicy,
    RetryableExceptionError,
    RetryableStatusError,
    request_json_with_retry,
    request_with_retry,
)
from scripts.download_and_hash import build_request_headers


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


def test_request_with_retry_retries_429_503_and_preserves_headers(
    mock_responses,
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

    mock_responses.add_callback(mock_responses.GET, url, callback=callback)

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


def test_request_with_retry_retries_timeout_then_succeeds(
    mock_responses,
    retry_config: RetryConfig,
) -> None:
    """Español: Reintenta timeout (conexión lenta) y recupera con éxito.

    English: Retry on timeout (slow connection) and recover successfully.
    """
    url = "https://cne.hn/api/slow"
    retry_config.per_exception["ReadTimeout"] = RetryPolicy(
        max_attempts=3,
        backoff_base=1.0,
        backoff_multiplier=2.0,
        max_delay=5.0,
        jitter_min=0.0,
        jitter_max=0.0,
    )

    mock_responses.add(
        mock_responses.GET,
        url,
        body=requests.exceptions.ReadTimeout("slow"),
    )
    mock_responses.add(mock_responses.GET, url, body="ok", status=200)

    session = requests.Session()
    try:
        response = request_with_retry(
            session,
            url,
            retry_config=retry_config,
            timeout=1.0,
        )
    finally:
        session.close()

    assert response.status_code == 200
    assert len(mock_responses.calls) == 2


def test_request_json_with_retry_recovers_from_malformed_json(
    mock_responses,
    retry_config: RetryConfig,
) -> None:
    """Español: Reintenta JSON parcial/malformado y recupera respuesta válida.

    English: Retry on partial/malformed JSON and recover with a valid payload.
    """
    url = "https://cne.hn/api/json"
    mock_responses.add(mock_responses.GET, url, body="{bad json", status=200)
    mock_responses.add(mock_responses.GET, url, json={"ok": True}, status=200)

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
    assert len(mock_responses.calls) == 2


def test_request_with_retry_persists_failed_requests_jsonl(
    mock_responses,
    retry_config: RetryConfig,
) -> None:
    """Español: Asegura registro en failed_requests.jsonl cuando se agotan intentos.

    English: Ensure failed_requests.jsonl is written when attempts are exhausted.
    """
    url = "https://cne.hn/api/always-503"
    mock_responses.add(mock_responses.GET, url, body="down", status=503)
    mock_responses.add(mock_responses.GET, url, body="down", status=503)
    mock_responses.add(mock_responses.GET, url, body="down", status=503)

    session = requests.Session()
    try:
        with pytest.raises(RetryableStatusError):
            request_with_retry(
                session,
                url,
                retry_config=retry_config,
                timeout=1.0,
            )
    finally:
        session.close()

    failed_path = retry_config.failed_requests_path
    assert failed_path.exists()
    lines = failed_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["url"] == url
    assert payload["attempts"] == 3
    assert payload["status_code"] == 503


def test_request_with_retry_retries_timeout_until_max_attempts(
    mock_responses,
    retry_config: RetryConfig,
) -> None:
    """Español: Asegura reintentos ante timeout y respeta max_attempts.

    English: Ensure timeout retries respect max_attempts limits.
    """
    url = "https://cne.hn/api/timeout"
    mock_responses.add(
        mock_responses.GET,
        url,
        body=requests.exceptions.ReadTimeout("slow"),
    )

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

    assert len(mock_responses.calls) == 2
