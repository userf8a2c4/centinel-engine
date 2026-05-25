#!/usr/bin/env python
"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `scripts/download_and_hash.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - resolve_config_path
  - apply_env_overrides
  - normalize_master_switch
  - is_master_switch_on
  - load_config
  - compute_hash
  - chain_hash
  - download_with_retries
  - fetch_with_retry
  - resolve_retry_policy
  - resolve_low_profile_settings
  - build_request_headers
  - resolve_timeout_seconds
  - create_mock_snapshot
  - run_mock_mode
  - ...

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `scripts/download_and_hash.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - resolve_config_path
  - apply_env_overrides
  - normalize_master_switch
  - is_master_switch_on
  - load_config
  - compute_hash
  - chain_hash
  - download_with_retries
  - fetch_with_retry
  - resolve_retry_policy
  - resolve_low_profile_settings
  - build_request_headers
  - resolve_timeout_seconds
  - create_mock_snapshot
  - run_mock_mode
  - ...

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
"""

# Download And Hash Module
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

# -*- coding: utf-8 -*-


import argparse
import contextlib
import fcntl
import hashlib
import json
import logging
import os
import random
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Optional

import requests
import yaml
from dateutil import parser as date_parser
from centinel.downloader import (
    StructuredLogger,
    build_alert_hook,
    load_retry_config,
    request_json_with_retry,
    request_with_retry,
    should_skip_snapshot,
)
from centinel.download import write_atomic
from centinel.paths import (
    ensure_source_dirs,
    hash_filename,
    resolve_source_id,
    snapshot_filename,
)
from scripts.circuit_breaker import CircuitBreaker
from core.fetcher import build_rotating_request_profile
from core.hasher import trigger_post_hash_backup

from monitoring.health import get_health_state
from scripts.logging_utils import configure_logging, log_event
from centinel.core.custody import sign_hash_record

logger = configure_logging("centinel.download", log_file="logs/centinel.log")

DEFAULT_CONFIG_PATH = "config.yaml"
COMMAND_CENTER_PATH = Path("command_center") / "config.yaml"
config_path = DEFAULT_CONFIG_PATH
TEMP_DIR = Path("data") / "temp"
CHECKPOINT_PATH = TEMP_DIR / "download_checkpoint.json"
BREAKER_STATE_PATH = TEMP_DIR / "circuit_breaker_state.json"
DEFAULT_RETRY_CONFIG_PATH = "config/prod/retry_config.yaml"


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
    env_retry_config = os.getenv("RETRY_CONFIG_PATH")

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
        config["required_keys"] = [key.strip() for key in env_required_keys.split(",") if key.strip()]
    if env_master_switch:
        config["master_switch"] = env_master_switch
    if env_retry_config:
        config["retry_config_path"] = env_retry_config

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
    combined = (previous_hash + current_data.decode("utf-8", errors="ignore")).encode("utf-8")
    return compute_hash(combined)


def download_with_retries(
    url: str,
    *,
    timeout: float | None = None,
    headers: dict[str, str] | None = None,
) -> requests.Response:
    """/** Descarga con reintentos configurables (tenacity). / Download with configurable retries (tenacity). **"""
    retry_config = load_retry_config(DEFAULT_RETRY_CONFIG_PATH)
    session = requests.Session()
    structured_logger = StructuredLogger("centinel.download")
    alert_hook = build_alert_hook(structured_logger)
    try:
        return request_with_retry(
            session,
            url,
            retry_config=retry_config,
            timeout=timeout,
            headers=headers,
            logger=structured_logger,
            context={"scope": "download_with_retries"},
            alert_hook=alert_hook,
        )
    finally:
        session.close()


def fetch_with_retry(
    url: str,
    *,
    timeout: float | None = None,
    headers: dict[str, str] | None = None,
    session: Optional[requests.Session] = None,
) -> requests.Response:
    """/** Realiza request con reintentos fijos y backoff. / Perform request with fixed retries and backoff. **"""
    if session is None:
        return download_with_retries(url, timeout=timeout, headers=headers)

    try:
        retry_config = load_retry_config(DEFAULT_RETRY_CONFIG_PATH)
        structured_logger = StructuredLogger("centinel.download")
        alert_hook = build_alert_hook(structured_logger)
        return request_with_retry(
            session,
            url,
            retry_config=retry_config,
            timeout=timeout,
            headers=headers,
            logger=structured_logger,
            context={"scope": "fetch_with_retry"},
            alert_hook=alert_hook,
        )
    except requests.exceptions.RequestException as exc:
        logger.warning("Error en fetch: %s", exc)
        raise


def resolve_retry_policy(config: dict[str, Any]) -> dict[str, Any]:
    """/** Resuelve política de reintentos. / Resolve retry policy. **"""
    retry_path = config.get("retry_config_path") or os.getenv("RETRY_CONFIG_PATH")
    retry_path = retry_path or DEFAULT_RETRY_CONFIG_PATH
    retry_config = load_retry_config(retry_path)
    return {"retry_config": retry_config, "retry_path": retry_path}


def resolve_low_profile_settings(config: dict[str, Any]) -> dict[str, Any]:
    """/** Normaliza configuración low-profile. / Normalize low-profile settings. **/"""
    low_profile = config.get("low_profile", {}) if isinstance(config, dict) else {}
    return low_profile if isinstance(low_profile, dict) else {}


def build_request_headers(
    config: dict[str, Any],
    low_profile: dict[str, Any],
    rng: random.Random,
) -> dict[str, str]:
    """/** Construye headers por request (low-profile opcional). / Build per-request headers (low-profile optional). **/"""
    if not low_profile.get("enabled", False):
        headers = config.get("headers", {}) if isinstance(config.get("headers"), dict) else {}
        if "Accept" not in headers:
            headers = {"Accept": "application/json", **headers}
        try:
            secure_headers, _ = build_rotating_request_profile()
            headers = {**headers, **secure_headers}
        except Exception as exc:
            logger.warning("failed_to_build_rotating_profile error=%s", exc)
        return headers

    user_agents = low_profile.get("user_agents", []) or []
    accept_languages = low_profile.get("accept_languages", []) or []
    referers = low_profile.get("referers", []) or []

    headers: dict[str, str] = {
        "Accept": "application/json",
    }
    if user_agents:
        headers["User-Agent"] = rng.choice(user_agents)
    if accept_languages:
        headers["Accept-Language"] = rng.choice(accept_languages)
    if referers:
        headers["Referer"] = rng.choice(referers)
    return headers


def resolve_timeout_seconds(config: dict[str, Any], low_profile: dict[str, Any]) -> float:
    """/** Resuelve timeout efectivo. / Resolve effective timeout. **/"""
    if low_profile.get("enabled", False):
        timeout_value = low_profile.get("timeout_seconds")
        if timeout_value is not None:
            return float(timeout_value)
    return float(config.get("timeout", 10))


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
    write_atomic(
        mock_file,
        json.dumps(mock_data, indent=2, ensure_ascii=False).encode("utf-8"),
    )
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
    """Verify the endpoint belongs to CNE via hostname allowlist + optional
    public-IP resolution check (mitigates DNS rebinding and substring spoofing).

    Substring matching alone (the previous implementation) accepted obvious
    forgeries such as 'https://cne.hn.attacker.example.com/'. We now parse the
    URL, compare the hostname against the configured allowlist (suffix match
    on dot boundary), and — when enforce_public_ip_resolution is true — also
    require the host to resolve to a public, non-private IP address.

    Verifica que el endpoint pertenezca al CNE mediante allowlist de hostname
    y, opcionalmente, validacion de resolucion a IP publica (mitigando DNS
    rebinding y spoofing por substring).
    """
    from core.security_utils import is_safe_outbound_url

    domains = config.get("cne_domains") or ["cne.hn"]
    enforce_public_ip = bool(config.get("enforce_public_ip_resolution", True))
    require_https = bool(config.get("require_https", True))

    return is_safe_outbound_url(
        endpoint,
        allowed_domains={domain.lower() for domain in domains},
        require_https=require_https,
        enforce_public_ip_resolution=enforce_public_ip,
    )


def _validate_real_payload(payload: Any, endpoint: str, config: dict[str, Any]) -> bool:
    """/** Valida payload real del CNE. / Validate real CNE payload. **"""
    if not _is_cne_endpoint(endpoint, config):
        logger.error("Endpoint rechazado (no allowlist / no IP publica): %s", endpoint)
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
        logger.error("Timestamp demasiado antiguo (%.1f h) para %s", age_hours, endpoint)
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

    data_root = Path("data")
    hash_root = Path("hashes")
    data_root.mkdir(exist_ok=True)
    hash_root.mkdir(exist_ok=True)

    health_state = get_health_state()
    retry_payload = resolve_retry_policy(config)
    retry_config = retry_payload["retry_config"]
    structured_logger = StructuredLogger("centinel.download")
    alert_hook = build_alert_hook(structured_logger)
    breaker_settings = config.get("download_circuit_breaker", {}) or {}
    breaker = CircuitBreaker.load_state(BREAKER_STATE_PATH) or CircuitBreaker(
        failure_threshold=int(breaker_settings.get("failure_threshold", 3)),
        failure_window_seconds=int(breaker_settings.get("failure_window_seconds", 300)),
        open_timeout_seconds=int(breaker_settings.get("open_timeout_seconds", 900)),
        half_open_after_seconds=int(breaker_settings.get("half_open_after_seconds", 300)),
        success_threshold=int(breaker_settings.get("success_threshold", 2)),
        open_log_interval_seconds=int(breaker_settings.get("open_log_interval_seconds", 120)),
    )
    session = requests.Session()
    had_errors = False

    try:
        for source in sources[:max_sources]:
            endpoint = resolve_endpoint(source, endpoints)
            if not endpoint:
                logger.error("Fuente sin endpoint definido: %s", source)
                continue
            source_id = resolve_source_id(source)
            source_label = source_id
            data_dir, hash_dir = ensure_source_dirs(
                source_id,
                data_root=data_root,
                hash_root=hash_root,
            )
            if source_label in processed_sources:
                logger.info("Fuente ya procesada en checkpoint: %s", source_label)
                continue
            if should_skip_snapshot(data_dir, source_id, retry_config=retry_config):
                logger.info("Snapshot reciente detectado, se omite descarga: %s", source_label)
                continue

            # ES: Jitter entre fuentes — suaviza la ráfaga intra-nodo (default 0.8-1.2s por fuente).
            # EN: Inter-source jitter — smooths intra-node burst (default 0.8-1.2s per source).
            _inter_jitter = float(config.get("inter_source_jitter_seconds", 1.0))
            if _inter_jitter > 0:
                time.sleep(random.uniform(_inter_jitter * 0.8, _inter_jitter * 1.2))

            now = datetime.now(timezone.utc)
            if not breaker.allow_request(now):
                if breaker.should_log_open_wait(now):
                    logger.warning("download_circuit_open source=%s", source_label)
                fallback_hash = _use_fallback_snapshot(
                    data_dir,
                    hash_dir,
                    source_id,
                    endpoint,
                    previous_hash,
                    reason="circuit_open",
                )
                if fallback_hash:
                    previous_hash = fallback_hash
                    processed_sources.add(source_label)
                    _save_checkpoint(previous_hash, processed_sources)
                health_state.record_failure()
                had_errors = True
                continue

            try:
                response, payload = request_json_with_retry(
                    session,
                    endpoint,
                    retry_config=retry_config,
                    timeout=float(config.get("timeout", retry_config.timeout_seconds)),
                    logger=structured_logger,
                    context={"source": source_label},
                    alert_hook=alert_hook,
                )
            except Exception as e:
                logger.error("Fallo al descargar %s: %s", endpoint, e)
                # Distinguish "the authority is down" from "someone is
                # cutting us": diagnose the failure mode and record a
                # signed, append-only degradation event. Best-effort and
                # bounded — it must never raise into or stall the capture
                # loop that has to run for a month.
                try:
                    from centinel.core.connectivity import diagnose_and_record

                    diagnose_and_record(
                        endpoint,
                        source_id=source_id,
                        reason="request_failed",
                        exception_text=str(e),
                        exception_type=type(e).__name__,
                    )
                except Exception as diag_exc:  # noqa: BLE001
                    logger.warning(
                        "connectivity_diagnosis_skipped error=%s", diag_exc
                    )
                breaker.record_failure(now)
                _persist_breaker_state(breaker)
                if breaker.consume_open_alert():
                    log_event(
                        logger,
                        logging.CRITICAL,
                        "download_circuit_breaker_open",
                        failure_threshold=breaker.failure_threshold,
                        window_seconds=breaker.failure_window_seconds,
                    )
                fallback_hash = _use_fallback_snapshot(
                    data_dir,
                    hash_dir,
                    source_id,
                    endpoint,
                    previous_hash,
                    reason="request_failed",
                )
                if fallback_hash:
                    previous_hash = fallback_hash
                    processed_sources.add(source_label)
                    _save_checkpoint(previous_hash, processed_sources)
                health_state.record_failure()
                had_errors = True
                continue

            if not _validate_real_payload(payload, response.url, config):
                logger.error("Payload inválido (no CNE/fecha real) en %s", endpoint)
                breaker.record_failure(now)
                _persist_breaker_state(breaker)
                fallback_hash = _use_fallback_snapshot(
                    data_dir,
                    hash_dir,
                    source_id,
                    endpoint,
                    previous_hash,
                    reason="payload_invalid",
                )
                if fallback_hash:
                    previous_hash = fallback_hash
                    processed_sources.add(source_label)
                    _save_checkpoint(previous_hash, processed_sources)
                health_state.record_failure()
                had_errors = True
                continue

            normalized_payload = payload if isinstance(payload, list) else [payload]
            snapshot_payload = {
                "timestamp": datetime.now().isoformat(),
                "source": source_id,
                "source_url": response.url,
                "data": normalized_payload,
            }
            (
                chained_hash,
                current_hash,
                snapshot_file,
            ) = _persist_snapshot_payload(
                snapshot_payload,
                source_id=source_id,
                data_dir=data_dir,
                hash_dir=hash_dir,
                previous_hash=previous_hash,
            )
            previous_hash = chained_hash

            logger.info("Snapshot descargado y hasheado para %s", source_label)
            health_state.record_success()
            breaker.record_success(now)
            _persist_breaker_state(breaker)
            processed_sources.add(source_label)
            _save_checkpoint(previous_hash, processed_sources)
            logger.debug(
                "current_hash=%s chained_hash=%s source=%s",
                current_hash,
                chained_hash,
                source_label,
            )
    finally:
        session.close()

    # ES: Política de cobertura — solo log. Umbrales: <82% CRITICAL, 82-89% ELEVATED, ≥90% HIGH_TRUST.
    # EN: Coverage policy — logging only. Thresholds: <82% CRITICAL, 82-89% ELEVATED, ≥90% HIGH_TRUST.
    _total_sources = min(len(sources), max_sources)
    if _total_sources > 0:
        _pct = len(processed_sources) / _total_sources * 100
        if _pct < 82:
            logger.critical("swarm_coverage pct=%.1f%% status=CRITICAL covered=%d/%d",
                            _pct, len(processed_sources), _total_sources)
        elif _pct < 90:
            logger.warning("swarm_coverage pct=%.1f%% status=ELEVATED covered=%d/%d",
                           _pct, len(processed_sources), _total_sources)
        else:
            logger.info("swarm_coverage pct=%.1f%% status=HIGH_TRUST covered=%d/%d",
                        _pct, len(processed_sources), _total_sources)

    if not had_errors:
        _clear_checkpoint()


def _persist_snapshot_payload(
    snapshot_payload: dict[str, Any],
    *,
    source_id: str,
    data_dir: Path,
    hash_dir: Path,
    previous_hash: str,
) -> tuple[str, str, Path]:
    """English: Persist snapshot and chained hash.

    Español: Persiste snapshot y hash encadenado.
    """
    snapshot_bytes = json.dumps(snapshot_payload, ensure_ascii=False, indent=2).encode("utf-8")
    current_hash = compute_hash(snapshot_bytes)
    chained_hash = chain_hash(previous_hash, snapshot_bytes)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    snapshot_file = data_dir / snapshot_filename(timestamp)
    hash_file = hash_dir / hash_filename(timestamp)
    write_atomic(snapshot_file, snapshot_bytes)
    hash_record = {"hash": current_hash, "chained_hash": chained_hash}

    # FASE 2: Firma Ed25519 del operador.
    #
    # En modo elección/producción estricta (CENTINEL_REQUIRE_SIGNATURE=true)
    # la firma es OBLIGATORIA: un fallo detiene el snapshot de forma ruidosa
    # en lugar de persistir evidencia sin custodio criptográfico. Sin este
    # control, un atacante que comprometa el disco antes de configurar la
    # clave produce una cadena entera sin firma y nadie lo detecta.
    require_signature = os.getenv("CENTINEL_REQUIRE_SIGNATURE", "false").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    try:
        sign_hash_record(hash_record)
    except FileNotFoundError as exc:
        if require_signature:
            raise RuntimeError(
                "signature_required_but_no_key — CENTINEL_REQUIRE_SIGNATURE is on "
                "but no operator key is configured. Refusing to persist unsigned "
                f"evidence for {hash_file.name}."
            ) from exc
        logger.warning(
            "operator_sign_skipped file=%s reason=no_key (signature NOT required)",
            hash_file.name,
        )
    except Exception as exc:  # noqa: BLE001
        if require_signature:
            raise RuntimeError(
                f"signature_required_but_failed file={hash_file.name} error={exc}"
            ) from exc
        logger.warning("operator_sign_failed file=%s error=%s", hash_file.name, exc)

    write_atomic(
        hash_file,
        json.dumps(hash_record, ensure_ascii=False, indent=2).encode("utf-8"),
    )
    trigger_post_hash_backup(snapshot_file, hash_file)
    return chained_hash, current_hash, snapshot_file


def _find_latest_snapshot_for_source(data_dir: Path, source_id: str) -> tuple[Path | None, dict[str, Any] | None]:
    """English: Find the latest valid snapshot for a source.

    Español: Busca el último snapshot válido para una fuente.

    data_dir ya apunta al subdirectorio de la fuente (e.g. data/snapshots/NACIONAL/).
    data_dir already points to the source subdirectory (e.g. data/snapshots/NACIONAL/).
    """
    if not data_dir.exists():
        return None, None
    candidates = sorted(
        data_dir.glob("snapshot_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for snapshot_path in candidates:
        try:
            payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return snapshot_path, payload
    return None, None


def _use_fallback_snapshot(
    data_dir: Path,
    hash_dir: Path,
    source_id: str,
    endpoint: str,
    previous_hash: str,
    *,
    reason: str,
) -> str | None:
    """English: Use the latest valid snapshot as fallback.

    Español: Usa el último snapshot válido como fallback.

    Forensic semantics: a fallback emits the OLD captured data with TWO
    timestamps so third-party auditors can distinguish data freshness from
    capture time:

      - original_timestamp:        when the source was originally captured
      - fallback_recovered_at:     when this fallback decision was taken (UTC,
                                   microseconds + sequence for total ordering)
      - timestamp (legacy field):  aliases fallback_recovered_at for backward
                                   compatibility with downstream consumers

    Without this separation, a cascade of fallbacks in the same second produces
    snapshots indistinguishable from one another and from real captures.
    """
    snapshot_path, payload = _find_latest_snapshot_for_source(data_dir, source_id)
    if not payload:
        logger.warning("fallback_snapshot_missing source=%s", source_id)
        return None

    now_utc = datetime.now(timezone.utc)
    recovered_at_iso = now_utc.isoformat(timespec="microseconds")
    sequence = _next_fallback_sequence(source_id)

    original_timestamp = payload.get("timestamp") or payload.get("timestamp_utc")
    if original_timestamp is None and snapshot_path is not None:
        try:
            original_timestamp = datetime.fromtimestamp(
                snapshot_path.stat().st_mtime, tz=timezone.utc
            ).isoformat(timespec="microseconds")
        except OSError:
            original_timestamp = None

    fallback_payload = {
        "timestamp": recovered_at_iso,
        "fallback_recovered_at": recovered_at_iso,
        "fallback_sequence": sequence,
        "original_timestamp": original_timestamp,
        "source": source_id,
        "source_url": payload.get("source_url") or endpoint,
        "data": payload.get("data", []),
        "fallback": True,
        "fallback_reason": reason,
        "fallback_snapshot": snapshot_path.name if snapshot_path else None,
    }
    chained_hash, _, _ = _persist_snapshot_payload(
        fallback_payload,
        source_id=source_id,
        data_dir=data_dir,
        hash_dir=hash_dir,
        previous_hash=previous_hash,
    )
    logger.warning("fallback_snapshot_used source=%s reason=%s", source_id, reason)
    return chained_hash


_FALLBACK_SEQUENCE_COUNTERS: dict[str, int] = {}
_FALLBACK_SEQUENCE_LOCK = __import__("threading").Lock()
_FALLBACK_SEQUENCE_STATE_PATH = TEMP_DIR / "fallback_sequence_state.json"
_FALLBACK_SEQUENCE_LOADED = False


def _load_fallback_sequence_state() -> None:
    """Load persisted per-source counters once (caller holds the lock).

    Without persistence the counter resets to 0 on every process restart,
    so after an election-night restart fallback sequences would repeat
    (1,2,3,...,1,2,3). Auditors rely on (timestamp, sequence) as a TOTAL
    order; in a hostile environment the attacker may also push the system
    clock backwards, at which point the in-process counter was the only
    remaining tiebreaker. Persisting it keeps the order monotonic across
    restarts. Missing/corrupt state degrades to empty (== legacy
    behavior): improvement only, never a regression.
    """
    global _FALLBACK_SEQUENCE_LOADED
    if _FALLBACK_SEQUENCE_LOADED:
        return
    _FALLBACK_SEQUENCE_LOADED = True
    try:
        raw = _FALLBACK_SEQUENCE_STATE_PATH.read_text(encoding="utf-8")
        persisted = json.loads(raw)
    except (FileNotFoundError, ValueError, OSError):
        return
    if not isinstance(persisted, dict):
        return
    for source_id, value in persisted.items():
        try:
            seq = int(value)
        except (TypeError, ValueError):
            continue
        # Never move a counter backwards: take the max of any in-memory
        # value and the persisted one.
        _FALLBACK_SEQUENCE_COUNTERS[source_id] = max(
            _FALLBACK_SEQUENCE_COUNTERS.get(source_id, 0), seq
        )


def _persist_fallback_sequence_state() -> None:
    """Durably persist counters (caller holds the lock). Best-effort.

    Uses the same fsync-durable atomic writer as snapshots so a crash
    cannot leave a torn counter file. Failure is logged, never raised:
    in-process ordering still holds; only cross-restart durability
    degrades, which is no worse than the legacy behavior.
    """
    try:
        _FALLBACK_SEQUENCE_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(
            _FALLBACK_SEQUENCE_COUNTERS, ensure_ascii=False, sort_keys=True
        ).encode("utf-8")
        write_atomic(_FALLBACK_SEQUENCE_STATE_PATH, payload)
    except Exception as exc:  # noqa: BLE001
        logger.warning("fallback_sequence_state_persist_failed error=%s", exc)


def _persist_breaker_state(breaker: CircuitBreaker) -> None:
    """Best-effort save of circuit breaker state to BREAKER_STATE_PATH.

    Persists state after every state transition so a process restart cannot
    silently reset the breaker (which would defeat the throttling purpose
    under sustained adversarial load).

    Save failures are logged but never raise — breaker logic must keep
    working even if the disk is temporarily unavailable.
    """
    try:
        breaker.save_state(BREAKER_STATE_PATH)
    except Exception as exc:  # noqa: BLE001
        logger.warning("circuit_breaker_state_persist_failed error=%s", exc)


def _next_fallback_sequence(source_id: str) -> int:
    """Monotonic per-source counter for fallback ordering within a process.

    Combined with microsecond UTC timestamps, this gives third-party auditors
    a total order over fallback events even when many are emitted in the same
    microsecond (catastrophic upstream outage).

    Contador monotonico por fuente para ordenar fallbacks dentro del proceso.
    Combinado con timestamps UTC con microsegundos, da a auditores externos un
    orden total sobre eventos de fallback incluso si varios ocurren en el mismo
    microsegundo (apagon catastrofico de la fuente).
    """
    with _FALLBACK_SEQUENCE_LOCK:
        _load_fallback_sequence_state()
        current = _FALLBACK_SEQUENCE_COUNTERS.get(source_id, 0) + 1
        _FALLBACK_SEQUENCE_COUNTERS[source_id] = current
        _persist_fallback_sequence_state()
        return current


@contextlib.contextmanager
def _checkpoint_lock(timeout_seconds: float = 30.0) -> Iterator[None]:
    """Cross-process exclusive lock for checkpoint operations.

    Prevents two pipeline instances from corrupting the hash chain by reading
    and writing the checkpoint concurrently (election-night restart scenarios).

    Bloqueo exclusivo entre procesos para operaciones de checkpoint.
    Previene corrupcion del hash chain cuando dos instancias del pipeline
    leen/escriben el checkpoint concurrentemente (escenarios de reinicio en
    noche electoral).
    """
    lock_path = CHECKPOINT_PATH.with_suffix(CHECKPOINT_PATH.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout_seconds
    with open(lock_path, "w") as lock_file:
        while True:
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise TimeoutError(
                        f"checkpoint_lock_timeout path={lock_path} timeout={timeout_seconds}s"
                    )
                time.sleep(0.1)
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _load_checkpoint() -> dict[str, Any]:
    """/** Carga checkpoint de descarga si existe. / Load download checkpoint if available. **"""
    if not CHECKPOINT_PATH.exists():
        return {}
    with _checkpoint_lock():
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
    with _checkpoint_lock():
        write_atomic(
            CHECKPOINT_PATH,
            json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8"),
        )


def _clear_checkpoint() -> None:
    """/** Limpia el checkpoint al completar el ciclo. / Clear checkpoint once cycle completes. **"""
    if CHECKPOINT_PATH.exists():
        CHECKPOINT_PATH.unlink()


def main() -> None:
    """/** Función principal del script. / Main script function. **"""
    logger.info("Iniciando download_and_hash")
    log_event(logger, logging.INFO, "download_start")

    parser = argparse.ArgumentParser(description="Descarga y hashea snapshots del CNE")
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
        logger.error("No se encontraron fuentes en command_center/config.yaml")
        health_state.record_failure(critical=True)
        raise ValueError("No sources defined in command_center/config.yaml")

    # ES: Jitter de inicio de ciclo — distribuye los nodos en el tiempo para evitar burst coordinado.
    # EN: Cycle jitter — staggers node start times to prevent coordinated bursts.
    _cycle_jitter = float(os.getenv("CENTINEL_SCRAPE_JITTER_SECONDS", "30"))
    if _cycle_jitter > 0:
        _jitter_delay = random.uniform(0.0, _cycle_jitter)
        logger.info("scrape_cycle_jitter delay_s=%.1f max_s=%.1f", _jitter_delay, _cycle_jitter)
        time.sleep(_jitter_delay)

    # ES: Filtro de fuentes activas — valida contra source_ids del config. Fail-safe: si todos
    #     los IDs pedidos son inválidos, raspa todo y emite WARNING.
    # EN: Active sources filter — validates against config source_ids. Fail-safe: if all
    #     requested IDs are invalid, scrapes everything and emits WARNING.
    _active_env = os.getenv("CENTINEL_ACTIVE_SOURCES", "").strip()
    if _active_env:
        _known_ids = {resolve_source_id(s) for s in sources}
        _requested = {sid.strip() for sid in _active_env.split(",") if sid.strip()}
        _unknown = _requested - _known_ids
        if _unknown:
            logger.warning("active_sources_unknown ids=%s — these will be ignored", sorted(_unknown))
        _active_set = _requested & _known_ids
        if _active_set:
            sources = [s for s in sources if resolve_source_id(s) in _active_set]
            logger.info("active_sources_filter count=%d/%d ids=%s",
                        len(sources), len(_known_ids), sorted(_active_set))
        else:
            logger.warning("active_sources_empty — all requested IDs unknown; scraping all %d sources",
                           len(sources))

    endpoints = config.get("endpoints", {})
    process_sources(sources, endpoints, config)
    logger.info("Proceso completado")
    log_event(logger, logging.INFO, "download_complete")


if __name__ == "__main__":
    main()
