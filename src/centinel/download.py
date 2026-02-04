"""Descarga resiliente y hashing encadenado para Centinel.

Resilient download and chained hashing for Centinel.
"""

from __future__ import annotations

import hashlib
import logging
import string
import shutil
import tempfile
import time
from pathlib import Path
from typing import Optional

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .proxy_handler import ProxyRotator, get_proxy_rotator

logger = logging.getLogger(__name__)


class DownloadError(Exception):
    """Error controlado de descarga.

    English: Controlled download error.
    """


@retry(
    retry=retry_if_exception_type(
        (httpx.RequestError, httpx.TimeoutException, httpx.HTTPStatusError)
    ),
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    reraise=True,
)
async def fetch_content(
    client: httpx.AsyncClient,
    url: str,
    if_none_match: Optional[str] = None,
    if_modified_since: Optional[str] = None,
    proxy_rotator: Optional[ProxyRotator] = None,
) -> httpx.Response:
    """Descarga contenido con cabeceras condicionales.

    English: Fetch content with conditional headers.
    """
    headers = {
        "User-Agent": "CentinelEngine/0.4.0",
    }
    if if_none_match:
        headers["If-None-Match"] = if_none_match
    if if_modified_since:
        headers["If-Modified-Since"] = if_modified_since

    proxy_url = proxy_rotator.get_proxy_for_request() if proxy_rotator else None
    request_kwargs = {}
    if proxy_url:
        request_kwargs["proxies"] = proxy_url
        request_kwargs["timeout"] = httpx.Timeout(proxy_rotator.proxy_timeout_seconds)

    start = time.monotonic()
    logger.debug(
        "fetch_start",
        url=url,
        proxy=proxy_url or "direct",
        if_none_match=bool(if_none_match),
        if_modified_since=bool(if_modified_since),
    )
    try:
        response = await client.get(url, headers=headers, **request_kwargs)
    except httpx.RequestError as exc:
        elapsed = time.monotonic() - start
        if proxy_rotator and proxy_url:
            proxy_rotator.mark_failure(proxy_url, str(exc))
        logger.warning(
            "proxy_request_error",
            proxy=proxy_url or "direct",
            elapsed_seconds=round(elapsed, 3),
            error=str(exc),
        )
        raise

    elapsed = time.monotonic() - start
    content_length = response.headers.get("Content-Length")
    if proxy_rotator and proxy_url:
        if response.status_code >= 400:
            proxy_rotator.mark_failure(proxy_url, f"status {response.status_code}")
            logger.warning(
                "proxy_response_error",
                proxy=proxy_url,
                status_code=response.status_code,
                elapsed_seconds=round(elapsed, 3),
                content_length=content_length,
            )
        else:
            proxy_rotator.mark_success(proxy_url)
            logger.info(
                "proxy_response_ok",
                proxy=proxy_url,
                status_code=response.status_code,
                elapsed_seconds=round(elapsed, 3),
                content_length=content_length,
            )
    else:
        logger.info(
            "direct_response",
            status_code=response.status_code,
            elapsed_seconds=round(elapsed, 3),
            content_length=content_length,
        )

    if response.status_code in {429, 503}:
        raise httpx.HTTPStatusError(
            f"Retryable status: {response.status_code}",
            request=response.request,
            response=response,
        )

    if response.status_code >= 400:
        raise DownloadError(f"Unexpected status {response.status_code} for {url}")

    return response


def write_atomic(path: Path, content: bytes) -> None:
    """Escritura atómica usando archivo temporal.

    English: Atomic write using a temporary file.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(delete=False, dir=str(path.parent)) as tmp_file:
        tmp_file.write(content)
        temp_name = tmp_file.name
    shutil.move(temp_name, path)


def chained_hash(
    content: bytes,
    previous_hash: Optional[str],
    *,
    metadata: Optional[bytes] = None,
    timestamp: Optional[str] = None,
) -> str:
    """Calcula hash encadenado con separación de dominio.

    English: Compute chained hash with domain separation.
    """
    return hashlib.sha256(
        _build_chain_payload(
            content,
            previous_hash=previous_hash,
            metadata=metadata,
            timestamp=timestamp,
        )
    ).hexdigest()


def _build_chain_payload(
    content: bytes,
    *,
    previous_hash: Optional[str],
    metadata: Optional[bytes] = None,
    timestamp: Optional[str] = None,
) -> bytes:
    """Construye payload con separación de dominio y longitudes."""
    previous_hash_bytes = b""
    if previous_hash:
        normalized = previous_hash.strip().lower()
        previous_hash_bytes = normalized.encode("utf-8")
        if not _is_valid_hex_hash(normalized):
            logger.warning("hashchain_previous_hash_invalid value=%s", normalized)

    parts = [
        b"centinel-chain-v1",
        b"prev",
        str(len(previous_hash_bytes)).encode("utf-8"),
        previous_hash_bytes,
    ]
    if timestamp:
        timestamp_bytes = timestamp.encode("utf-8")
        parts.extend([b"ts", str(len(timestamp_bytes)).encode("utf-8"), timestamp_bytes])
    if metadata:
        parts.extend([b"meta", str(len(metadata)).encode("utf-8"), metadata])

    parts.extend([b"content", str(len(content)).encode("utf-8"), content])
    return b"|".join(parts)


def _is_valid_hex_hash(value: str) -> bool:
    if len(value) != 64:
        return False
    hex_chars = set(string.hexdigits.lower())
    return all(char in hex_chars for char in value)


def build_client() -> httpx.AsyncClient:
    """Construye un cliente HTTP con timeout global.

    English: Build an HTTP client with a global timeout.
    """
    return httpx.AsyncClient(timeout=httpx.Timeout(30.0))


async def download_and_hash(
    url: str,
    output_path: Path,
    previous_hash: Optional[str] = None,
    if_none_match: Optional[str] = None,
    if_modified_since: Optional[str] = None,
) -> str:
    """Descarga, guarda y devuelve el hash encadenado.

    English: Download, persist, and return the chained hash.
    """
    proxy_rotator = get_proxy_rotator(logger)
    async with build_client() as client:
        try:
            response = await fetch_content(
                client,
                url,
                if_none_match=if_none_match,
                if_modified_since=if_modified_since,
                proxy_rotator=proxy_rotator,
            )
        except httpx.RequestError as exc:
            raise DownloadError(f"Request failed for {url}: {exc}") from exc
        except httpx.HTTPStatusError as exc:
            raise DownloadError(f"HTTP error for {url}: {exc}") from exc
        except httpx.TransportError as exc:
            raise DownloadError(f"Transport/SSL error for {url}: {exc}") from exc

    content = response.content
    write_atomic(output_path, content)
    chained = chained_hash(content, previous_hash)
    logger.info(
        "download_hash_written",
        url=url,
        output_path=str(output_path),
        content_bytes=len(content),
        previous_hash=previous_hash,
        chained_hash=chained,
    )
    return chained
