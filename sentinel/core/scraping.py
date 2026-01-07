import json
from typing import Any, Dict, Mapping
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from playwright.sync_api import sync_playwright


def _build_url(base_url: str, params: Mapping[str, str]) -> str:
    split = urlsplit(base_url)
    query = dict(parse_qsl(split.query))
    query.update({key: str(value) for key, value in params.items()})
    return urlunsplit((split.scheme, split.netloc, split.path, urlencode(query), split.fragment))


def fetch_payload_with_playwright(
    base_url: str,
    params: Mapping[str, str],
    timeout: float,
    headers: Mapping[str, str],
) -> Dict[str, Any]:
    url = _build_url(base_url, params)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(extra_http_headers=dict(headers))
        try:
            page = context.new_page()
            response = page.goto(url, wait_until="networkidle", timeout=int(timeout * 1000))
            if response is None:
                raise RuntimeError("Playwright no recibió respuesta al cargar la URL.")
            try:
                payload = response.json()
            except Exception:
                text = response.text()
                try:
                    payload = json.loads(text)
                except json.JSONDecodeError as exc:
                    raise ValueError("Respuesta Playwright no es JSON válido.") from exc
        finally:
            context.close()
            browser.close()

    if not isinstance(payload, dict):
        raise ValueError("Respuesta Playwright no es un objeto JSON.")

    return payload
