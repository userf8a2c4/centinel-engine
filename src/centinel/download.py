"""Descarga resiliente y hashing encadenado para Centinel.

Resilient download and chained hashing for Centinel.
"""

from __future__ import annotations

import hashlib
import logging
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
    retry=retry_if_exception_type((httpx.RequestError, httpx.TimeoutException)),
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
    if proxy_rotator and proxy_url:
        if response.status_code >= 400:
            proxy_rotator.mark_failure(proxy_url, f"status {response.status_code}")
            logger.warning(
                "proxy_response_error",
                proxy=proxy_url,
                status_code=response.status_code,
                elapsed_seconds=round(elapsed, 3),
            )
        else:
            proxy_rotator.mark_success(proxy_url)
            logger.info(
                "proxy_response_ok",
                proxy=proxy_url,
                status_code=response.status_code,
                elapsed_seconds=round(elapsed, 3),
            )
    else:
        logger.info(
            "direct_response",
            status_code=response.status_code,
            elapsed_seconds=round(elapsed, 3),
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


def chained_hash(content: bytes, previous_hash: Optional[str]) -> str:
    """Calcula hash encadenado: sha256(content + previous_hash).

    English: Compute chained hash: sha256(content + previous_hash).
    """
    base = content
    if previous_hash:
        base = content + previous_hash.encode()
    return hashlib.sha256(base).hexdigest()


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
    return chained_hash(content, previous_hash)
