#!/usr/bin/env python
"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `scripts/collector.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - configure_logging
  - load_yaml
  - is_safe_http_url
  - fetch_json_with_retry
  - validate_collected_payloads
  - detect_statistical_anomalies
  - run_collection
  - main
  - bloque_main

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `scripts/collector.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - configure_logging
  - load_yaml
  - is_safe_http_url
  - fetch_json_with_retry
  - validate_collected_payloads
  - detect_statistical_anomalies
  - run_collection
  - main
  - bloque_main

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
"""

# Collector Module
# AUTO-DOC-INDEX
#
# ES: Índice rápido
#   1) Propósito del módulo
#   2) Componentes principales
#   3) Puntos de extensión
#
# EN: Quick index
#   1) Module purpose
#   2) Main components
#   3) Extension points
#
# Secciones / Sections:
#   - Configuración / Configuration
#   - Lógica principal / Core logic
#   - Integraciones / Integrations



from __future__ import annotations

import json
import logging
import random
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from core.security_utils import is_safe_outbound_url, pin_dns_resolution, resolve_outbound_target

import requests
import yaml
from scipy import stats

from centinel.proxy_handler import get_proxy_rotator
from centinel.schemas import validate_snapshot

LOGGER = logging.getLogger("centinel.collector")
DEFAULT_CONFIG_PATH = Path("command_center/config.yaml")
DEFAULT_RETRY_PATH = Path("config/prod/retry_config.yaml")
DEFAULT_OUTPUT_PATH = Path("data/collector_latest.json")


def configure_logging() -> None:
    """Configure collector logging.

    Configura logging del colector.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def load_yaml(path: Path) -> dict[str, Any]:
    """Load YAML safely and return a dict.

    Carga YAML de forma segura y retorna un diccionario.
    """
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    return payload if isinstance(payload, dict) else {}


def is_safe_http_url(
    url: str,
    *,
    allowed_domains: set[str] | None = None,
    enforce_public_ip_resolution: bool = False,
) -> bool:
    """Validate URL safety constraints before requesting.

    Valida restricciones de seguridad de URL antes de consultar.
    """
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    return is_safe_outbound_url(
        url,
        allowed_domains=allowed_domains,
        require_https=False,
        enforce_public_ip_resolution=enforce_public_ip_resolution,
    )


def fetch_json_with_retry(
    session: requests.Session,
    url: str,
    *,
    timeout_seconds: float,
    max_attempts: int,
    backoff_base: float,
    user_agents: list[str] | None = None,
    proxy_url: str | None = None,
    allowed_domains: set[str] | None = None,
    enforce_public_ip_resolution: bool = False,
) -> dict[str, Any] | None:
    """Fetch JSON from URL with retries.

    Descarga JSON desde URL con reintentos.
    """
    if not is_safe_http_url(
        url,
        allowed_domains=allowed_domains,
        enforce_public_ip_resolution=enforce_public_ip_resolution,
    ):
        LOGGER.error("collector_unsafe_url_skipped url=%s", url)
        return None

    target = resolve_outbound_target(
        url,
        allowed_domains=allowed_domains,
        require_https=False,
        enforce_public_ip_resolution=enforce_public_ip_resolution,
    )
    if target is None:
        LOGGER.error("collector_target_resolution_failed url=%s", url)
        return None

    for attempt in range(1, max_attempts + 1):
        try:
            headers = {
                "User-Agent": (
                    random.choice(user_agents) if user_agents else "Mozilla/5.0 (compatible; Centinel-Collector/1.0)"
                ),
                "Accept": "application/json",
            }
            proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None
            request_headers = dict(headers)
            request_headers["Connection"] = "close"
            with pin_dns_resolution(target):
                response = session.get(url, timeout=timeout_seconds, headers=request_headers, proxies=proxies)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, json.JSONDecodeError, ValueError) as exc:
            LOGGER.warning("collector_fetch_failed attempt=%s/%s url=%s error=%s", attempt, max_attempts, url, exc)
            if attempt == max_attempts:
                return None
            # English/Spanish: exponential backoff avoids burst retries / evita reintentos en ráfaga.
            time.sleep(min(backoff_base * (2 ** (attempt - 1)), 15))
    return None


def validate_collected_payloads(
    payloads: list[dict[str, Any]], expected_count: int = 96
) -> tuple[list[dict[str, Any]], int]:
    """Validate payloads against canonical schema.

    Valida payloads contra el esquema canónico.
    """
    valid_payloads: list[dict[str, Any]] = []
    invalid_count = 0
    for payload in payloads:
        try:
            valid_payloads.append(validate_snapshot(payload))
        except ValueError as exc:
            invalid_count += 1
            LOGGER.error("collector_schema_invalid error=%s", exc)

    if len(valid_payloads) != expected_count:
        LOGGER.warning(
            "collector_expected_count_mismatch expected=%s valid=%s invalid=%s",
            expected_count,
            len(valid_payloads),
            invalid_count,
        )
    return valid_payloads, invalid_count


def detect_statistical_anomalies(payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compute simple z-score anomalies over total votes.

    Calcula anomalías simples por z-score sobre votos totales.
    """
    totals = [entry["totals"]["total_votes"] for entry in payloads if isinstance(entry.get("totals"), dict)]
    if len(totals) < 3:
        return []

    zscores = stats.zscore(totals)
    anomalies: list[dict[str, Any]] = []
    for index, zvalue in enumerate(zscores):
        if abs(float(zvalue)) >= 3.0:
            anomalies.append({"index": index, "zscore": float(zvalue), "total_votes": totals[index]})
    return anomalies


def run_collection(config_path: Path = DEFAULT_CONFIG_PATH, retry_path: Path = DEFAULT_RETRY_PATH) -> int:
    """Run resilient collection and persist validated snapshots.

    Ejecuta recolección resiliente y persiste snapshots validados.
    """
    configure_logging()
    config = load_yaml(config_path)
    retry_cfg = load_yaml(retry_path)

    default_retry = retry_cfg.get("default", {}) if isinstance(retry_cfg.get("default"), dict) else {}
    max_attempts = int(default_retry.get("max_attempts", 3))
    backoff_base = float(default_retry.get("backoff_base", 1.0))
    timeout_seconds = float(retry_cfg.get("timeout_seconds", config.get("timeout", 20)))

    sources = config.get("sources", []) if isinstance(config.get("sources"), list) else []
    endpoints = config.get("endpoints", {}) if isinstance(config.get("endpoints"), dict) else {}
    scraping_profile = config.get("scraping_profile", {}) if isinstance(config.get("scraping_profile"), dict) else {}
    jitter_bounds = scraping_profile.get("request_jitter_seconds", [0.0, 0.0])
    if not isinstance(jitter_bounds, list) or len(jitter_bounds) != 2:
        jitter_bounds = [0.0, 0.0]
    min_jitter = max(float(jitter_bounds[0]), 0.0)
    max_jitter = max(float(jitter_bounds[1]), min_jitter)
    user_agents = (
        scraping_profile.get("user_agents", []) if isinstance(scraping_profile.get("user_agents"), list) else []
    )
    user_agents = [str(agent) for agent in user_agents if str(agent).strip()]
    rotator = get_proxy_rotator(LOGGER)

    if not sources:
        LOGGER.warning("collector_no_sources_found config_path=%s", config_path)

    allowed_domains = {str(item).lower() for item in config.get("cne_domains", []) if str(item).strip()}

    fetched_payloads: list[dict[str, Any]] = []
    with requests.Session() as session:
        for source in sources:
            endpoint = source.get("endpoint") or endpoints.get(source.get("department_code"))
            if not endpoint:
                LOGGER.error("collector_source_without_endpoint source=%s", source)
                continue
            proxy_url = rotator.get_proxy_for_request()
            payload = fetch_json_with_retry(
                session,
                str(endpoint),
                timeout_seconds=timeout_seconds,
                max_attempts=max_attempts,
                backoff_base=backoff_base,
                user_agents=user_agents,
                proxy_url=proxy_url,
                allowed_domains=allowed_domains or None,
                enforce_public_ip_resolution=True,
            )
            if payload is not None:
                fetched_payloads.append(payload)
                if proxy_url:
                    rotator.mark_success(proxy_url)
            elif proxy_url:
                rotator.mark_failure(proxy_url, "collector_fetch_failed")

            if max_jitter > 0:
                jitter = random.uniform(min_jitter, max_jitter)
                LOGGER.debug("collector_request_jitter_sleep seconds=%.2f", jitter)
                time.sleep(jitter)

    expected_count = int(config.get("expected_json_count", 96))
    valid_payloads, invalid_count = validate_collected_payloads(fetched_payloads, expected_count=expected_count)
    anomalies = detect_statistical_anomalies(valid_payloads)

    DEFAULT_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "expected_json_count": expected_count,
        "fetched_count": len(fetched_payloads),
        "valid_count": len(valid_payloads),
        "invalid_count": invalid_count,
        "anomalies": anomalies,
        "snapshots": valid_payloads,
    }
    DEFAULT_OUTPUT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    LOGGER.info(
        "collector_report_written path=%s valid=%s invalid=%s", DEFAULT_OUTPUT_PATH, len(valid_payloads), invalid_count
    )
    return 0


def main() -> None:
    """CLI entrypoint for the collector.

    Punto de entrada CLI para el colector.
    """
    raise SystemExit(run_collection())


if __name__ == "__main__":
    main()
