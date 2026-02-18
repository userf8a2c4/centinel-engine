"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `scripts/healthcheck.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - _build_session
  - _collect_endpoints
  - check_cne_connectivity
  - check_cne_endpoints

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `scripts/healthcheck.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - _build_session
  - _collect_endpoints
  - check_cne_connectivity
  - check_cne_endpoints

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
"""

# Healthcheck Module
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


def check_cne_connectivity(config: dict[str, Any]) -> bool:
    """Verifica conectividad con CNE usando un HEAD rápido.

    English:
        Check connectivity to CNE using a quick HEAD request.
    """
    endpoints = config.get("endpoints", {}) or {}
    dummy_endpoint = (
        config.get("healthcheck_url")
        or config.get("base_url")
        or endpoints.get("nacional")
        or endpoints.get("fallback_nacional")
    )
    if not dummy_endpoint:
        log_event(logger, logging.WARNING, "healthcheck_missing_dummy_endpoint")
        return False

    timeout = 10
    session = requests.Session()
    try:
        response = session.head(dummy_endpoint, timeout=timeout, allow_redirects=True)
        if response.status_code >= 400:
            raise requests.HTTPError(f"status={response.status_code}")
        log_event(
            logger,
            logging.INFO,
            "healthcheck_dummy_ok",
            endpoint=dummy_endpoint,
        )
        return True
    except requests.RequestException as exc:
        log_event(
            logger,
            logging.WARNING,
            "healthcheck_dummy_failed",
            endpoint=dummy_endpoint,
            error=str(exc),
        )
        return False
    finally:
        session.close()


def check_cne_endpoints(config: dict[str, Any]) -> bool:
    """Verifica conectividad con endpoints CNE detallados.

    English:
        Check connectivity to detailed CNE endpoints.
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
