import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

import requests
import yaml
from dotenv import load_dotenv

from sentinel.core.hashchain import compute_hash
from sentinel.core.normalyze import DEPARTMENT_CODES, normalize_snapshot, snapshot_to_canonical_json
from sentinel.core.scraping import fetch_payload_with_playwright
from sentinel.utils.logging_config import setup_logging

# Directorios
data_dir = Path("data")
hash_dir = Path("hashes")
config_path = Path(__file__).resolve().parents[1] / "config.yaml"

data_dir.mkdir(exist_ok=True)
hash_dir.mkdir(exist_ok=True)

load_dotenv()

setup_logging()
logger = logging.getLogger(__name__)


def load_config() -> Dict[str, Any]:
    config: Dict[str, Any] = {}
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as handle:
            config = yaml.safe_load(handle) or {}

    base_url = os.getenv("BASE_URL") or config.get("base_url")
    endpoints = config.get("endpoints") or []
    if base_url and not endpoints:
        endpoints = [base_url]
    if not endpoints:
        raise ValueError("ENDPOINTS o BASE_URL no está configurado (config.yaml o env var).")

    timeout = float(os.getenv("TIMEOUT") or config.get("timeout", 15))
    retries = int(os.getenv("RETRIES") or config.get("retries", 3))
    headers = config.get("headers", {})

    env_headers = os.getenv("HEADERS")
    if env_headers:
        headers = json.loads(env_headers)

    env_use_playwright = os.getenv("USE_PLAYWRIGHT")
    use_playwright = config.get("use_playwright", False)
    if env_use_playwright is not None:
        use_playwright = env_use_playwright.strip().lower() in {"1", "true", "yes", "on"}

    backoff_base = float(config.get("backoff_base_seconds", 1))
    backoff_max = float(config.get("backoff_max_seconds", 30))
    candidate_count = int(config.get("candidate_count", 10))
    required_keys = config.get("required_keys", [])
    field_map = config.get("field_map", {})
    playwright_stealth = bool(config.get("playwright_stealth", False))
    playwright_user_agent = config.get("playwright_user_agent")
    playwright_locale = config.get("playwright_locale")
    playwright_timezone = config.get("playwright_timezone")
    playwright_viewport = config.get("playwright_viewport")

    sources = config.get("sources")
    if not sources:
        sources = [
            {
                "name": department_name,
                "department_code": department_code,
                "level": "PD",
                "scope": "DEPARTMENT",
            }
            for department_name, department_code in DEPARTMENT_CODES.items()
        ]

    resolved_sources = []
    for source in sources:
        resolved = {**source}
        source_endpoints = resolved.get("endpoints") or endpoints
        if not source_endpoints:
            raise ValueError(
                f"ENDPOINTS no está configurado para la fuente {resolved.get('name') or resolved.get('source_id')}."
            )
        resolved["endpoints"] = list(source_endpoints)
        resolved_sources.append(resolved)

    return {
        "base_url": base_url,
        "endpoints": endpoints,
        "timeout": timeout,
        "retries": retries,
        "headers": headers,
        "backoff_base": backoff_base,
        "backoff_max": backoff_max,
        "candidate_count": candidate_count,
        "sources": resolved_sources,
        "required_keys": required_keys,
        "field_map": field_map,
        "use_playwright": use_playwright,
        "playwright_stealth": playwright_stealth,
        "playwright_user_agent": playwright_user_agent,
        "playwright_locale": playwright_locale,
        "playwright_timezone": playwright_timezone,
        "playwright_viewport": playwright_viewport,
    }


def get_previous_hash(department_code: str) -> str | None:
    """
    Busca el hash previo más reciente para el departamento.
    """
    pattern = f"snapshot_{department_code}_*.sha256"
    hash_files = sorted(hash_dir.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    if hash_files:
        with open(hash_files[0], "r", encoding="utf-8") as handle:
            return handle.read().strip()
    return None


def fetch_source_data(
    session: requests.Session,
    endpoints: list[str],
    source: Dict[str, Any],
    base_url: str | None,
    timeout: float,
    headers: Dict[str, str],
    retries: int,
    backoff_base: float,
    backoff_max: float,
    use_playwright: bool,
    playwright_stealth: bool,
    playwright_user_agent: str | None,
    playwright_locale: str | None,
    playwright_timezone: str | None,
    playwright_viewport: Dict[str, int] | None,
) -> Dict[str, Any]:
    if not endpoints:
        raise ValueError("No hay endpoints configurados para la fuente.")
    params = {"level": source.get("level", "PD")}
    department_code = source.get("department_code")
    if department_code:
        params["dept"] = department_code
    if source.get("params"):
        params.update(source["params"])
    source_id = source.get("source_id") or department_code or source.get("name")
    last_error: Exception | None = None
    last_endpoint: str | None = None

    def _looks_like_html_or_captcha(text: str) -> bool:
        lowered = text.lower()
        if "<html" in lowered or "<!doctype html" in lowered or "<body" in lowered:
            return True
        captcha_markers = (
            "captcha",
            "verify you are human",
            "recaptcha",
            "hcaptcha",
            "cf-turnstile",
            "cloudflare",
        )
        return any(marker in lowered for marker in captcha_markers)

    def _fetch_with_playwright(endpoint: str) -> Dict[str, Any]:
        return fetch_payload_with_playwright(
            base_url=endpoint,
            params=params,
            timeout=timeout,
            headers=headers,
            user_agent=playwright_user_agent,
            viewport=playwright_viewport,
            locale=playwright_locale,
            timezone=playwright_timezone,
            stealth=playwright_stealth,
        )

    for endpoint in endpoints:
        last_endpoint = endpoint
        for attempt in range(1, retries + 1):
            try:
                response = session.get(endpoint, params=params, timeout=timeout, headers=headers)
                if not response.ok:
                    raise requests.HTTPError(
                        f"HTTP {response.status_code}",
                        response=response,
                    )
                try:
                    payload = response.json()
                except ValueError as exc:
                    response_text = response.text
                    if use_playwright and _looks_like_html_or_captcha(response_text):
                        logger.info(
                            "fetch_fallback_playwright_html source_id=%s endpoint=%s status_code=%s",
                            source_id,
                            endpoint,
                            response.status_code,
                        )
                        try:
                            payload = _fetch_with_playwright(endpoint)
                            logger.info(
                                "fetch_fallback_success source_id=%s endpoint=%s",
                                source_id,
                                endpoint,
                            )
                            return payload
                        except Exception as fallback_exc:  # noqa: BLE001
                            last_error = fallback_exc
                            logger.error(
                                "fetch_fallback_failed source_id=%s endpoint=%s error=%s",
                                source_id,
                                endpoint,
                                fallback_exc,
                            )
                            break
                    raise ValueError("Respuesta no es JSON válido.") from exc

                if not isinstance(payload, dict):
                    raise ValueError("Respuesta JSON no es un objeto.")

                logger.info(
                    "fetch_success source_id=%s endpoint=%s status_code=%s attempt=%s",
                    source_id,
                    endpoint,
                    response.status_code,
                    attempt,
                )
                return payload
            except Exception as exc:  # noqa: BLE001 - queremos loggear y reintentar
                last_error = exc
                logger.warning(
                    "fetch_retry source_id=%s endpoint=%s attempt=%s error=%s",
                    source_id,
                    endpoint,
                    attempt,
                    exc,
                )
                if attempt < retries:
                    sleep_time = min(backoff_base * (2 ** (attempt - 1)), backoff_max)
                    time.sleep(sleep_time)

        logger.warning(
            "endpoint_failed source_id=%s endpoint=%s error=%s",
            source_id,
            endpoint,
            last_error or "Unknown error",
        )

    if use_playwright:
        if not base_url:
            logger.error(
                "fetch_fallback_missing_base_url source_id=%s",
                source.get("source_id") or department_code or source.get("name"),
            )
        else:
            logger.info(
                "fetch_fallback_playwright source_id=%s",
                source.get("source_id") or department_code or source.get("name"),
            )
        try:
            if base_url:
                payload = fetch_payload_with_playwright(
                    base_url=base_url,
                    params=params,
                    timeout=timeout,
                    headers=headers,
                    user_agent=playwright_user_agent,
                    locale=playwright_locale,
                    timezone_id=playwright_timezone,
                    viewport=playwright_viewport,
                    stealth=playwright_stealth,
                )
                logger.info(
                    "fetch_fallback_success source_id=%s",
                    source.get("source_id") or department_code or source.get("name"),
                )
                return payload
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            logger.error(
                "fetch_fallback_failed source_id=%s error=%s",
                source.get("source_id") or department_code or source.get("name"),
                exc,
            )

    logger.error(
        "fetch_failed source_id=%s endpoint=%s error=%s retries=%s",
        source_id,
        endpoints[-1] if endpoints else None,
        last_error or "Unknown error",
        retries,
    )
    raise last_error or RuntimeError("Fallo desconocido al descargar datos.")


def build_snapshot(payload: Dict[str, Any], source: Dict[str, Any]) -> Dict[str, Any]:
    timestamp = datetime.now(timezone.utc).isoformat()
    return {
        "metadata": {
            "department": source.get("name"),
            "department_code": source.get("department_code"),
            "scope": source.get("scope", "DEPARTMENT"),
            "source_id": source.get("source_id"),
            "timestamp_utc": timestamp,
        },
        "data": payload,
    }


def persist_snapshot(
    snapshot: Dict[str, Any],
    canonical_json: str,
    department_code: str,
    timestamp: str,
    source_id: str,
) -> str:
    json_path = data_dir / f"snapshot_{department_code}_{timestamp}.json"
    hash_path = hash_dir / f"snapshot_{department_code}_{timestamp}.sha256"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False)

    previous_hash = get_previous_hash(department_code)
    hash_value = compute_hash(canonical_json, previous_hash)

    with open(hash_path, "w", encoding="utf-8") as f:
        f.write(hash_value)

    logger.info(
        "snapshot_saved source_id=%s json_path=%s hash_path=%s previous_hash=%s hash=%s",
        source_id,
        json_path,
        hash_path,
        previous_hash or "none",
        hash_value,
    )
    return hash_value


def persist_normalized(snapshot: Dict[str, Any], source_id: str, timestamp: str) -> None:
    normalized_path = normalized_dir / f"snapshot_{source_id}_{timestamp}.json"
    with open(normalized_path, "w", encoding="utf-8") as handle:
        json.dump(snapshot, handle, indent=2, ensure_ascii=False)


def main() -> None:
    config = load_config()
    failures = []
    session = requests.Session()

    for source in config["sources"]:
        try:
            department_name = source.get("name") or "Desconocido"
            department_code = source.get("department_code") or source.get("source_id") or "NA"
            source_id = source.get("source_id") or department_code or department_name
            payload = fetch_source_data(
                session=session,
                endpoints=source["endpoints"],
                source=source,
                base_url=config.get("base_url"),
                timeout=config["timeout"],
                headers=config["headers"],
                retries=config["retries"],
                backoff_base=config["backoff_base"],
                backoff_max=config["backoff_max"],
                use_playwright=config["use_playwright"],
                playwright_stealth=config["playwright_stealth"],
                playwright_user_agent=config["playwright_user_agent"],
                playwright_locale=config["playwright_locale"],
                playwright_timezone=config["playwright_timezone"],
                playwright_viewport=config["playwright_viewport"],
            )
            snapshot = build_snapshot(payload, source)
            timestamp_utc = snapshot["metadata"]["timestamp_utc"]
            canonical_snapshot = normalize_snapshot(
                payload,
                department_name=department_name,
                timestamp_utc=timestamp_utc,
                scope=source.get("scope", "DEPARTMENT"),
                department_code=department_code if source.get("department_code") else None,
                candidate_count=config["candidate_count"],
                field_map=config["field_map"],
            )
            canonical_json = snapshot_to_canonical_json(canonical_snapshot)
            timestamp = snapshot["metadata"]["timestamp_utc"].replace(":", "-")
            persist_snapshot(snapshot, canonical_json, department_code, timestamp, source_id)
        except Exception as exc:  # noqa: BLE001
            source_id = source.get("source_id") or source.get("department_code") or source.get("name")
            failures.append((source_id, str(exc)))
            logger.error(
                "snapshot_failed source_id=%s error=%s",
                source_id,
                exc,
            )

    if failures:
        failure_summary = ", ".join(f"{dept}:{err}" for dept, err in failures)
        raise SystemExit(f"Fallos al descargar snapshots: {failure_summary}")


if __name__ == "__main__":
    main()
