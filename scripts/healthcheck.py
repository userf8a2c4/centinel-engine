"""Healthchecks de conectividad CNE antes de ejecutar pipeline.

English:
    Connectivity checks to CNE endpoints before running the pipeline.
"""

from __future__ import annotations

import logging
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from scripts.logging_utils import configure_logging, log_event

logger = configure_logging("centinel.healthcheck", log_file="logs/centinel.log")


def _build_session(retries: int, backoff_factor: float) -> requests.Session:
    """Construye una sesión HTTP con reintentos y backoff exponencial.

    English:
        Build an HTTP session with retries and exponential backoff.
    """
    retry_strategy = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def _collect_endpoints(config: dict[str, Any]) -> list[str]:
    """Recoge endpoints configurados para el chequeo de salud.

    English:
        Collect configured endpoints for healthchecks.
    """
    endpoints = config.get("endpoints", {}) or {}
    sources = config.get("sources", []) or []
    max_sources = int(config.get("max_sources_per_cycle", 19))
    targets: list[str] = []
    for source in sources[:max_sources]:
        scope = source.get("scope")
        if scope == "NATIONAL":
            endpoint = endpoints.get("nacional") or endpoints.get("fallback_nacional")
        elif scope == "DEPARTMENT":
            department_code = source.get("department_code")
            endpoint = endpoints.get(department_code) if department_code else None
        else:
            endpoint = source.get("endpoint")
        if endpoint:
            targets.append(endpoint)
    return sorted(set(targets))


def check_cne_endpoints(config: dict[str, Any]) -> bool:
    """Verifica conectividad con endpoints CNE.

    English:
        Check connectivity to CNE endpoints.
    """
    endpoints = _collect_endpoints(config)
    if not endpoints:
        log_event(logger, logging.WARNING, "healthcheck_no_endpoints")
        return False

    retries = int(config.get("retries", 5))
    backoff_factor = float(config.get("backoff_base_seconds", 0.5))
    timeout = float(config.get("timeout", 10))

    session = _build_session(retries=retries, backoff_factor=backoff_factor)
    ok_count = 0
    for endpoint in endpoints:
        try:
            response = session.get(endpoint, timeout=timeout)
            response.raise_for_status()
            ok_count += 1
        except requests.RequestException as exc:
            log_event(
                logger,
                logging.WARNING,
                "healthcheck_failed",
                endpoint=endpoint,
                error=str(exc),
            )

    log_event(
        logger,
        logging.INFO,
        "healthcheck_summary",
        ok_count=ok_count,
        total=len(endpoints),
    )
    return ok_count > 0
