#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
download_and_hash.py

Descarga snapshots de resultados electorales del CNE Honduras y genera hashes encadenados
SHA-256 para integridad.

Uso:
    python -m scripts.download_and_hash [--mock]

Dependencias: requests, pyyaml, hashlib, logging, argparse, pathlib, json, datetime

Este script es parte del proyecto C.E.N.T.I.N.E.L. y se usa solo para auditoría
ciudadana neutral.

Download CNE Honduras election results snapshots and generate chained SHA-256 hashes
for integrity.

Usage:
    python -m scripts.download_and_hash [--mock]

Dependencies: requests, pyyaml, hashlib, logging, argparse, pathlib, json, datetime

This script is part of the C.E.N.T.I.N.E.L. project and is used only for neutral
civic auditing.
"""

import argparse
import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import requests
import yaml
from dateutil import parser as date_parser
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from monitoring.health import get_health_state
from scripts.logging_utils import configure_logging, log_event

logger = configure_logging("centinel.download", log_file="logs/centinel.log")

DEFAULT_CONFIG_PATH = "config.yaml"
COMMAND_CENTER_PATH = Path("command_center") / "config.yaml"
RULES_CONFIG_PATH = Path("command_center") / "rules.yaml"
config_path = DEFAULT_CONFIG_PATH
TEMP_DIR = Path("data") / "temp"
CHECKPOINT_PATH = TEMP_DIR / "download_checkpoint.json"
DEFAULT_RETRY_MAX = 5
DEFAULT_BACKOFF_FACTOR = 2.0


def resolve_config_path(config_path_override: str | None = None) -> str:
    """/** Resuelve ruta de configuración priorizando command_center. / Resolve configuration path prioritizing command_center. **"""
    if config_path_override:
        return config_path_override
    if COMMAND_CENTER_PATH.exists():
        return str(COMMAND_CENTER_PATH)
    return config_path


def apply_env_overrides(config: dict[str, Any]) -> dict[str, Any]:
    """/** Aplica overrides desde variables de entorno. / Apply overrides from environment variables. **"""
    env_base_url = os.getenv("BASE_URL")
    env_timeout = os.getenv("TIMEOUT")
    env_retries = os.getenv("RETRIES")
    env_headers = os.getenv("HEADERS")
    env_backoff_base = os.getenv("BACKOFF_BASE_SECONDS")
    env_backoff_max = os.getenv("BACKOFF_MAX_SECONDS")
    env_candidate_count = os.getenv("CANDIDATE_COUNT")
    env_required_keys = os.getenv("REQUIRED_KEYS")
    env_master_switch = os.getenv("MASTER_SWITCH")

    if env_base_url:
        config["base_url"] = env_base_url
    if env_timeout:
        config["timeout"] = float(env_timeout)
    if env_retries:
        config["retries"] = int(env_retries)
    if env_headers:
        try:
            parsed_headers = json.loads(env_headers)
            if isinstance(parsed_headers, dict):
                merged = {**config.get("headers", {}), **parsed_headers}
                config["headers"] = merged
        except json.JSONDecodeError as exc:
            logger.warning("invalid_headers_env error=%s", exc)
    if env_backoff_base:
        config["backoff_base_seconds"] = float(env_backoff_base)
    if env_backoff_max:
        config["backoff_max_seconds"] = float(env_backoff_max)
    if env_candidate_count:
        config["candidate_count"] = int(env_candidate_count)
    if env_required_keys:
        config["required_keys"] = [
            key.strip() for key in env_required_keys.split(",") if key.strip()
        ]
    if env_master_switch:
        config["master_switch"] = env_master_switch

    return config


def normalize_master_switch(value: Any) -> str:
    """/** Normaliza el switch maestro a 'ON' o 'OFF'. / Normalize master switch to 'ON' or 'OFF'. **"""
    if value is None:
        return "ON"
    if isinstance(value, bool):
        return "ON" if value else "OFF"
    if isinstance(value, (int, float)):
        return "ON" if value else "OFF"
    if isinstance(value, str):
        cleaned = value.strip().upper()
        if cleaned in {"ON", "OFF"}:
            return cleaned
    return "ON"


def is_master_switch_on(config: dict[str, Any]) -> bool:
    """/** Indica si el switch maestro permite procesos automáticos. / Indicates whether the master switch allows automatic processes. **"""
    return normalize_master_switch(config.get("master_switch")) == "ON"


def load_config(config_path_override: str | None = None) -> dict[str, Any]:
    """/** Carga la configuración desde config.yaml. / Load configuration from config.yaml. **"""
    try:
        resolved_path = resolve_config_path(config_path_override)
        with open(resolved_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
        logger.info("Configuración cargada desde %s", resolved_path)
        return apply_env_overrides(config)
    except FileNotFoundError:
        logger.error("Archivo de configuración no encontrado: %s", resolved_path)
        raise
    except yaml.YAMLError as e:
        logger.error("Error al parsear YAML: %s", e)
        raise


def compute_hash(data: bytes) -> str:
    """/** Calcula hash SHA-256. / Compute SHA-256 hash. **"""
    return hashlib.sha256(data).hexdigest()


def chain_hash(previous_hash: str, current_data: bytes) -> str:
    """/** Genera hash encadenado. / Generate chained hash. **"""
    combined = (previous_hash + current_data.decode("utf-8", errors="ignore")).encode(
        "utf-8"
    )
    return compute_hash(combined)


def download_with_retries(
    url: str,
    *,
    timeout: float = 10.0,
) -> requests.Response:
    """/** Descarga con reintentos explícitos y backoff. / Download with explicit retries and backoff. **"""
    rules_thresholds = load_rules_thresholds()
    retry_max = int(rules_thresholds.get("retry_max", DEFAULT_RETRY_MAX))
    backoff_factor = float(
        rules_thresholds.get("backoff_factor", DEFAULT_BACKOFF_FACTOR)
    )
    retry_strategy = Retry(
        total=retry_max,
        connect=retry_max,
        read=retry_max,
        backoff_factor=backoff_factor,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    try:
        for attempt in range(1, retry_max + 1):
            logger.info("download_attempt=%s/%s url=%s", attempt, retry_max, url)
            try:
                response = session.get(url, timeout=timeout)
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as exc:
                logger.warning(
                    "download_attempt_failed attempt=%s url=%s error=%s",
                    attempt,
                    url,
                    exc,
                )
                if attempt == retry_max:
                    logger.error("download_retries_exhausted url=%s", url)
                    raise
    finally:
        session.close()


def fetch_with_retry(
    url: str,
    *,
    timeout: float = 10.0,
    session: Optional[requests.Session] = None,
) -> requests.Response:
    """/** Realiza request con reintentos fijos y backoff. / Perform request with fixed retries and backoff. **"""
    if session is None:
        return download_with_retries(url, timeout=timeout)

    try:
        response = session.get(url, timeout=timeout)
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as exc:
        logger.warning("Error en fetch: %s", exc)
        raise


def load_rules_thresholds() -> dict[str, Any]:
    """/** Carga umbrales desde command_center/rules.yaml. / Load thresholds from command_center/rules.yaml. **"""
    if not RULES_CONFIG_PATH.exists():
        return {}
    try:
        payload = yaml.safe_load(RULES_CONFIG_PATH.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        logger.warning("rules_yaml_invalid error=%s", exc)
        return {}
    return payload if isinstance(payload, dict) else {}


def resolve_retry_policy(config: dict[str, Any]) -> tuple[int, float]:
    """/** Resuelve política de reintentos. / Resolve retry policy. **"""
    rules_thresholds = load_rules_thresholds()
    retry_max = int(
        rules_thresholds.get("retry_max", config.get("retries", DEFAULT_RETRY_MAX))
    )
    backoff_factor = float(
        rules_thresholds.get(
            "backoff_factor",
            config.get("backoff_base_seconds", DEFAULT_BACKOFF_FACTOR),
        )
    )
    return retry_max, backoff_factor


def build_retry_session(retry_max: int, backoff_factor: float) -> requests.Session:
    """/** Crea sesión HTTP con reintentos y backoff. / Build HTTP session with retries and backoff. **"""
    retry_strategy = Retry(
        total=retry_max,
        connect=retry_max,
        read=retry_max,
        backoff_factor=backoff_factor,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def create_mock_snapshot() -> Path:
    """/** Crea snapshot mock para modo CI. / Create mock snapshot for CI mode. **"""
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)

    mock_data = {
        "timestamp": datetime.now().isoformat(),
        "source": "MOCK_CI",
        "level": "NACIONAL",
        "porcentaje_escrutado": 0.0,
        "votos_totales": 0,
        "note": "Este es un snapshot mock para pruebas en CI - no datos reales",
    }

    mock_file = data_dir / "snapshot_mock_ci.json"
    mock_file.write_text(json.dumps(mock_data, indent=2, ensure_ascii=False))
    logger.info("Snapshot mock creado: %s", mock_file)
    return mock_file


def run_mock_mode() -> None:
    """/** Ejecuta flujo mock para CI. / Run mock flow for CI. **"""
    logger.info("MODO MOCK ACTIVADO (CI) - No se intentará descargar del CNE real")
    create_mock_snapshot()
    logger.info("Modo mock completado - pipeline continúa con datos dummy")


def _extract_payload_timestamp(payload: Any) -> Optional[datetime]:
    """/** Extrae timestamp desde payload. / Extract timestamp from payload. **"""
    if isinstance(payload, list) and payload:
        payload = payload[0]
    if not isinstance(payload, dict):
        return None
    meta = payload.get("meta") or payload.get("metadata") or {}
    raw_ts = (
        payload.get("timestamp")
        or payload.get("timestamp_utc")
        or payload.get("fecha")
        or payload.get("fecha_hora")
        or payload.get("hora_actualizacion")
        or meta.get("timestamp_utc")
    )
    if not raw_ts:
        return None
    try:
        parsed = date_parser.parse(str(raw_ts))
    except (ValueError, TypeError):
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _payload_has_cne_source(payload: Any) -> bool:
    """/** Valida fuente CNE en payload. / Validate CNE source in payload. **"""
    if isinstance(payload, list) and payload:
        payload = payload[0]
    if not isinstance(payload, dict):
        return False
    source_value = str(payload.get("source") or payload.get("fuente") or "").upper()
    if "CNE" in source_value:
        return True
    meta = payload.get("meta") or payload.get("metadata") or {}
    meta_source = str(meta.get("source") or meta.get("fuente") or "").upper()
    return "CNE" in meta_source


def _is_cne_endpoint(endpoint: str, config: dict[str, Any]) -> bool:
    """/** Verifica si endpoint pertenece a CNE. / Check whether endpoint belongs to CNE. **"""
    domains = config.get("cne_domains") or ["cne.hn"]
    endpoint_lower = endpoint.lower()
    return any(domain.lower() in endpoint_lower for domain in domains)


def _validate_real_payload(
    payload: Any, endpoint: str, config: dict[str, Any]
) -> bool:
    """/** Valida payload real del CNE. / Validate real CNE payload. **"""
    if not _is_cne_endpoint(endpoint, config):
        logger.error("Endpoint fuera de CNE: %s", endpoint)
        return False

    timestamp = _extract_payload_timestamp(payload)
    if not timestamp:
        logger.error("Payload sin timestamp real: %s", endpoint)
        return False

    max_age_hours = float(config.get("timestamp_max_age_hours", 24))
    now = datetime.now(timezone.utc)
    age_hours = (now - timestamp).total_seconds() / 3600
    if age_hours < -1:
        logger.error("Timestamp en el futuro detectado: %s", timestamp.isoformat())
        return False
    if age_hours > max_age_hours:
        logger.error(
            "Timestamp demasiado antiguo (%.1f h) para %s", age_hours, endpoint
        )
        return False
    if not _payload_has_cne_source(payload):
        logger.warning("Payload sin fuente CNE explícita: %s", endpoint)
    return True


def resolve_endpoint(source: dict[str, Any], endpoints: dict[str, str]) -> str | None:
    """/** Resuelve endpoint para una fuente configurada. / Resolve endpoint for a configured source. **"""
    scope = source.get("scope")
    if scope == "NATIONAL":
        return endpoints.get("nacional") or endpoints.get("fallback_nacional")
    if scope == "DEPARTMENT":
        department_code = source.get("department_code")
        if department_code:
            return endpoints.get(department_code)
    return source.get("endpoint")


def process_sources(
    sources: list[dict[str, Any]],
    endpoints: dict[str, str],
    config: dict[str, Any],
) -> None:
    """/** Procesa fuentes reales y actualiza hashes. / Process real sources and update hashes. **"""
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    checkpoint = _load_checkpoint()
    previous_hash = checkpoint.get("previous_hash", "0" * 64)
    processed_sources = set(checkpoint.get("processed_sources", []))
    max_sources = int(config.get("max_sources_per_cycle", 19))

    data_dir = Path("data")
    hash_dir = Path("hashes")
    data_dir.mkdir(exist_ok=True)
    hash_dir.mkdir(exist_ok=True)

    health_state = get_health_state()

    for source in sources[:max_sources]:
        endpoint = resolve_endpoint(source, endpoints)
        if not endpoint:
            logger.error("Fuente sin endpoint definido: %s", source)
            continue
        source_label = source.get("source_id") or source.get("name", "unknown")
        if source_label in processed_sources:
            logger.info("Fuente ya procesada en checkpoint: %s", source_label)
            continue

        try:
            response = download_with_retries(
                endpoint,
                timeout=float(config.get("timeout", 10)),
            )
            try:
                payload = response.json()
            except ValueError:
                payload = {
                    "raw": response.text,
                    "note": "Respuesta no JSON convertida a texto.",
                }

            if not _validate_real_payload(payload, response.url, config):
                logger.error("Payload inválido (no CNE/fecha real) en %s", endpoint)
                health_state.record_failure()
                continue

            normalized_payload = payload if isinstance(payload, list) else [payload]
            snapshot_payload = {
                "timestamp": datetime.now().isoformat(),
                "source": source.get("source_id") or source.get("name", "unknown"),
                "source_url": response.url,
                "data": normalized_payload,
            }
            snapshot_bytes = json.dumps(
                snapshot_payload, ensure_ascii=False, indent=2
            ).encode("utf-8")

            current_hash = compute_hash(snapshot_bytes)
            chained_hash = chain_hash(previous_hash, snapshot_bytes)

            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            source_id = source.get("source_id") or source.get("department_code", "NA")
            snapshot_file = data_dir / f"snapshot_{timestamp}_{source_id}.json"
            hash_file = hash_dir / f"snapshot_{timestamp}_{source_id}.sha256"
            snapshot_file.write_bytes(snapshot_bytes)
            hash_file.write_text(
                json.dumps(
                    {"hash": current_hash, "chained_hash": chained_hash},
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            previous_hash = chained_hash
            logger.info("Snapshot descargado y hasheado para %s", source_label)
            health_state.record_success()
            processed_sources.add(source_label)
            _save_checkpoint(previous_hash, processed_sources)
            logger.debug(
                "current_hash=%s chained_hash=%s source=%s",
                current_hash,
                chained_hash,
                source_label,
            )
        except Exception as e:
            logger.error("Fallo al descargar %s: %s", endpoint, e)
            health_state.record_failure()
    _clear_checkpoint()


def _load_checkpoint() -> dict[str, Any]:
    """/** Carga checkpoint de descarga si existe. / Load download checkpoint if available. **"""
    if not CHECKPOINT_PATH.exists():
        return {}
    try:
        payload = json.loads(CHECKPOINT_PATH.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except json.JSONDecodeError as exc:
        logger.warning("checkpoint_invalid error=%s", exc)
        return {}


def _save_checkpoint(previous_hash: str, processed_sources: set[str]) -> None:
    """/** Guarda checkpoint parcial para recuperar hash chain. / Save partial checkpoint to recover hash chain. **"""
    payload = {
        "previous_hash": previous_hash,
        "processed_sources": sorted(processed_sources),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    CHECKPOINT_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def _clear_checkpoint() -> None:
    """/** Limpia el checkpoint al completar el ciclo. / Clear checkpoint once cycle completes. **"""
    if CHECKPOINT_PATH.exists():
        CHECKPOINT_PATH.unlink()


def main() -> None:
    """/** Función principal del script. / Main script function. **"""
    logger.info("Iniciando download_and_hash")
    log_event(logger, logging.INFO, "download_start")

    parser = argparse.ArgumentParser(
        description="Descarga y hashea snapshots del CNE"
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Modo mock para CI - no intenta fetch real",
    )
    args = parser.parse_args()

    config = load_config()
    health_state = get_health_state()
    master_status = normalize_master_switch(config.get("master_switch"))
    logger.info("MASTER SWITCH: %s", master_status)
    if not is_master_switch_on(config):
        logger.warning("Ejecución detenida por switch maestro (OFF)")
        return

    if args.mock:
        if not config.get("allow_mock", False):
            logger.error("Modo mock deshabilitado por configuración")
            raise ValueError("Mock mode disabled by configuration.")
        run_mock_mode()
        logger.info("Proceso completado")
        log_event(logger, logging.INFO, "download_complete")
        return

    logger.info("Modo real activado - procediendo con fetch al CNE")
    sources = config.get("sources", [])
    if not sources:
        logger.error("No se encontraron fuentes en config/config.yaml")
        health_state.record_failure(critical=True)
        raise ValueError("No sources defined in config/config.yaml")

    endpoints = config.get("endpoints", {})
    process_sources(sources, endpoints, config)
    logger.info("Proceso completado")
    log_event(logger, logging.INFO, "download_complete")


if __name__ == "__main__":
    main()
