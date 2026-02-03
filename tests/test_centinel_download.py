"""Pruebas de descarga y hashing en Centinel.

Tests for Centinel download and hashing.
"""

import asyncio
from pathlib import Path

import httpx
import pytest

from centinel.download import download_and_hash, fetch_content

pytest.importorskip("pytest_httpx")


def test_download_and_hash_success(httpx_mock, tmp_path):
    """Español: Función test_download_and_hash_success del módulo tests/test_centinel_download.py.

    English: Function test_download_and_hash_success defined in tests/test_centinel_download.py.
    """
    url = "https://example.com/data"
    payload = b"payload"
    httpx_mock.add_response(url=url, content=payload)

    output_path = tmp_path / "data.bin"
    result = asyncio.run(download_and_hash(url, output_path, previous_hash="abc"))

    assert output_path.read_bytes() == payload
    assert result


def test_download_and_hash_handles_429(httpx_mock, tmp_path):
    """Español: Función test_download_and_hash_handles_429 del módulo tests/test_centinel_download.py.

    English: Function test_download_and_hash_handles_429 defined in tests/test_centinel_download.py.
    """
    url = "https://example.com/limited"
    httpx_mock.add_response(url=url, status_code=429)

    output_path = tmp_path / "data.bin"
    with pytest.raises(Exception):
        asyncio.run(download_and_hash(url, output_path))


def test_fetch_content_retries_on_timeout(httpx_mock, monkeypatch):
    """Español: Función test_fetch_content_retries_on_timeout del módulo tests/test_centinel_download.py.

    English: Function test_fetch_content_retries_on_timeout defined in tests/test_centinel_download.py.
    """
    url = "https://example.com/timeout"
    httpx_mock.add_exception(httpx.TimeoutException("timeout"))
    monkeypatch.setattr("tenacity.nap.sleep", lambda _: None)

    async def run():
        """Español: Función asíncrona run del módulo tests/test_centinel_download.py.

        English: Async function run defined in tests/test_centinel_download.py.
        """
        async with httpx.AsyncClient() as client:
            with pytest.raises(httpx.TimeoutException):
                await fetch_content(client, url)

    asyncio.run(run())
