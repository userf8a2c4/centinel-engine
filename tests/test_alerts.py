"""Tests for monitoring alerts helpers."""

import httpx

from monitoring.alerts import _parse_retry_after


def test_parse_retry_after_reads_retry_param() -> None:
    """Español: Verifica lectura de retry_after en payload válido.

    English: Ensure retry_after is parsed from a valid payload.
    """
    response = httpx.Response(429, json={"parameters": {"retry_after": "3"}})

    assert _parse_retry_after(response) == 3.0


def test_parse_retry_after_defaults_on_invalid_json() -> None:
    """Español: Usa default si la respuesta no es JSON válido.

    English: Use default value when response JSON is invalid.
    """
    response = httpx.Response(429, content=b"not-json")

    assert _parse_retry_after(response) == 2.0
