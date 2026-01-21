from __future__ import annotations

"""Descarga resiliente y hashing encadenado para Centinel.

English: Resilient download and chained hashing for Centinel.
"""

import hashlib
import shutil
import tempfile
from pathlib import Path
from typing import Optional

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


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

    response = await client.get(url, headers=headers)

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
    async with build_client() as client:
        try:
            response = await fetch_content(
                client,
                url,
                if_none_match=if_none_match,
                if_modified_since=if_modified_since,
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
