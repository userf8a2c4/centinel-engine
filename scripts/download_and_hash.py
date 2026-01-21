#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
download_and_hash.py

Descarga snapshots de resultados electorales del CNE Honduras y genera hashes encadenados SHA-256 para integridad.
Download CNE Honduras election results snapshots and generate chained SHA-256 hashes for integrity.

Uso / Usage:
    python -m scripts.download_and_hash [--mock]

Dependencias / Dependencies: requests, pyyaml, hashlib, logging, argparse, pathlib, json, datetime

Este script es parte del proyecto C.E.N.T.I.N.E.L. – solo para auditoría ciudadana neutral.
This script is part of C.E.N.T.I.N.E.L. project – for neutral citizen audit only.
"""

import argparse
import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from sentinel.utils.config_loader import load_config
from monitoring.health import get_health_state

# Configuración de logging global (inicializado temprano)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("centinel.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = "config.yaml"
CONTROL_MASTER_PATH = Path("control_master") / "config.yaml"
config_path = DEFAULT_CONFIG_PATH


def resolve_config_path(config_path_override: str | None = None) -> str:
    """Resuelve la ruta de configuración priorizando control_master.

    English:
        Resolve configuration path prioritizing control_master.
    """
    if config_path_override:
        return config_path_override
    if CONTROL_MASTER_PATH.exists():
        return str(CONTROL_MASTER_PATH)
    return config_path


def apply_env_overrides(config: dict[str, Any]) -> dict[str, Any]:
    """Aplica overrides desde variables de entorno.

    Args:
        config (dict[str, Any]): Configuración base cargada.

    Returns:
        dict[str, Any]: Configuración con overrides aplicados.

    English:
        Apply overrides from environment variables.

    Args:
        config (dict[str, Any]): Loaded base configuration.

    Returns:
        dict[str, Any]: Configuration with applied overrides.
    """
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
    """Normaliza el switch maestro a 'ON' o 'OFF'.

    English:
        Normalize master switch to 'ON' or 'OFF'.
    """
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
    """Indica si el switch maestro permite procesos automáticos.

    English:
        Indicates whether the master switch allows automatic processes.
    """
    return normalize_master_switch(config.get("master_switch")) == "ON"


def load_config(config_path_override: str | None = None) -> dict[str, Any]:
    """Carga la configuración desde config.yaml.

    Args:
        config_path_override (str | None): Ruta al archivo de configuración si se proporciona.

    Returns:
        dict[str, Any]: Configuración cargada.

    Raises:
        FileNotFoundError: Si el archivo no existe.
        yaml.YAMLError: Si hay error de sintaxis YAML.

    English:
        Load configuration from config.yaml.

    Args:
        config_path_override (str | None): Path to config file when provided.

    Returns:
        dict[str, Any]: Loaded configuration.

    Raises:
        FileNotFoundError: If the file does not exist.
        yaml.YAMLError: If YAML syntax errors are found.
    """
    try:
        resolved_path = resolve_config_path(config_path_override)
        with open(resolved_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
        logger.info(
            "Configuración cargada desde %s / Configuration loaded from %s",
            resolved_path,
            resolved_path,
        )
        return apply_env_overrides(config)
    except FileNotFoundError:
        logger.error(
            "Archivo de configuración no encontrado: %s / Config file not found: %s",
            resolved_path,
            resolved_path,
        )
        raise
    except yaml.YAMLError as e:
        logger.error("Error al parsear YAML: %s / Error parsing YAML: %s", e, e)
        raise


def compute_hash(data: bytes) -> str:
    """Calcula hash SHA-256 de los datos.

    Args:
        data (bytes): Datos a hashear.

    Returns:
        str: Hash hexadecimal.

    English:
        Compute SHA-256 hash of data.

    Args:
        data (bytes): Data to hash.

    Returns:
        str: Hexadecimal hash.
    """
    return hashlib.sha256(data).hexdigest()


def chain_hash(previous_hash: str, current_data: bytes) -> str:
    """Genera hash encadenado: hash(previous_hash + current_data).

    Args:
        previous_hash (str): Hash anterior.
        current_data (bytes): Datos actuales.

    Returns:
        str: Nuevo hash encadenado.

    English:
        Generate chained hash: hash(previous_hash + current_data).

    Args:
        previous_hash (str): Previous hash.
        current_data (bytes): Current data.

    Returns:
        str: New chained hash.
    """
    combined = (previous_hash + current_data.decode("utf-8", errors="ignore")).encode(
        "utf-8"
    )
    return compute_hash(combined)


def fetch_with_retry(
    url: str, retries: int = 3, backoff_factor: float = 0.5
) -> requests.Response:
    """Realiza request con reintentos.

    Args:
        url (str): Endpoint a consultar.
        retries (int): Número máximo de reintentos.
        backoff_factor (float): Factor de espera entre reintentos.

    Returns:
        requests.Response: Respuesta exitosa.

    Raises:
        requests.exceptions.RequestException: Si todos los reintentos fallan.

    English:
        Perform request with retries.

    Args:
        url (str): Endpoint to fetch.
        retries (int): Max retries.
        backoff_factor (float): Backoff factor.

    Returns:
        requests.Response: Successful response.

    Raises:
        requests.exceptions.RequestException: If all retries fail.
    """
    retry_strategy = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)

    with requests.Session() as session:
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        try:
            response = session.get(url, timeout=10)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.warning("Error en fetch: %s / Fetch error: %s", e, e)
            raise


def create_mock_snapshot() -> Path:
    """Crea un snapshot mock para modo CI.

    Returns:
        Path: Ruta al archivo mock creado.

    English:
        Create a mock snapshot for CI mode.

    Returns:
        Path: Path to created mock file.
    """
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)

    mock_data = {
        "timestamp": datetime.now().isoformat(),
        "source": "MOCK_CI",
        "level": "NACIONAL",
        "porcentaje_escrutado": 0.0,
        "votos_totales": 0,
        "note": (
            "Este es un snapshot mock para pruebas en CI - no datos reales / "
            "This is a mock snapshot for CI testing - no real data"
        ),
    }

    mock_file = data_dir / "snapshot_mock_ci.json"
    mock_file.write_text(json.dumps(mock_data, indent=2, ensure_ascii=False))
    logger.info(
        "Snapshot mock creado: %s / Mock snapshot created: %s", mock_file, mock_file
    )
    return mock_file


def run_mock_mode() -> None:
    """Ejecuta el flujo mock para CI.

    English:
        Run the mock flow for CI.
    """
    logger.info(
        "MODO MOCK ACTIVADO (CI) - No se intentará descargar del CNE real / "
        "MOCK MODE ACTIVATED (CI) - No real CNE fetch will be attempted"
    )
    create_mock_snapshot()
    logger.info(
        "Modo mock completado - pipeline continúa con datos dummy / "
        "Mock mode completed - pipeline continues with dummy data"
    )


def resolve_endpoint(source: dict[str, Any], endpoints: dict[str, str]) -> str | None:
    """Resuelve el endpoint para una fuente configurada."""
    scope = source.get("scope")
    if scope == "NATIONAL":
        return endpoints.get("nacional") or endpoints.get("fallback_nacional")
    if scope == "DEPARTMENT":
        department_code = source.get("department_code")
        if department_code:
            return endpoints.get(department_code)
    return source.get("endpoint")


def process_sources(sources: list[dict[str, Any]], endpoints: dict[str, str]) -> None:
    """Procesa fuentes reales y actualiza la cadena de hashes.

    Args:
        sources (list[dict[str, Any]]): Lista de fuentes configuradas.

    English:
        Process real sources and update the hash chain.

    Args:
        sources (list[dict[str, Any]]): Configured sources list.
    """
    previous_hash = "0" * 64

    data_dir = Path("data")
    hash_dir = Path("hashes")
    data_dir.mkdir(exist_ok=True)
    hash_dir.mkdir(exist_ok=True)

    health_state = get_health_state()

    for source in sources:
        endpoint = resolve_endpoint(source, endpoints)
        if not endpoint:
            logger.error(
                "Fuente sin endpoint definido: %s / Source without endpoint: %s",
                source,
                source,
            )
            continue

        try:
            response = fetch_with_retry(endpoint)
            try:
                payload = response.json()
            except ValueError:
                payload = {
                    "raw": response.text,
                    "note": "Respuesta no JSON convertida a texto.",
                }

            normalized_payload = payload if isinstance(payload, list) else [payload]
            snapshot_payload = {
                "timestamp": datetime.now().isoformat(),
                "source": source.get("source_id") or source.get("name", "unknown"),
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
            source_label = source.get("source_id") or source.get("name", "unknown")
            logger.info(
                "Snapshot descargado y hasheado para %s / Snapshot downloaded and hashed for %s",
                source_label,
                source_label,
            )
            health_state.record_success()
            logger.debug(
                "current_hash=%s chained_hash=%s source=%s",
                current_hash,
                chained_hash,
                source_label,
            )
        except Exception as e:
            logger.error(
                "Fallo al descargar %s: %s / Failed to download %s: %s",
                endpoint,
                e,
                endpoint,
                e,
            )
            health_state.record_failure()


def main() -> None:
    """Función principal del script.

    Descarga snapshots del CNE, genera hashes encadenados y guarda logs/alertas.

    English:
        Main script function.

    Download CNE snapshots, generate chained hashes and save logs/alerts.
    """
    logger.info("Iniciando download_and_hash / Starting download_and_hash")

    parser = argparse.ArgumentParser(
        description="Descarga y hashea snapshots del CNE / Download and hash CNE snapshots"
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Modo mock para CI - no intenta fetch real / Mock mode for CI - skips real fetch",
    )
    args = parser.parse_args()

    config = load_config()
    health_state = get_health_state()
    master_status = normalize_master_switch(config.get("master_switch"))
    logger.info("MASTER SWITCH: %s", master_status)
    if not is_master_switch_on(config):
        logger.warning(
            "Ejecución detenida por switch maestro (OFF) / Execution halted by master switch (OFF)"
        )
        return

    if args.mock:
        run_mock_mode()
        logger.info("Proceso completado / Process completed")
        return

    logger.info(
        "Modo real activado - procediendo con fetch al CNE / Real mode activated - proceeding with CNE fetch"
    )
    sources = config.get("sources", [])
    if not sources:
        logger.error(
            "No se encontraron fuentes en config/config.yaml / No sources found in config/config.yaml"
        )
        health_state.record_failure(critical=True)
        raise ValueError("No sources defined in config/config.yaml")

    endpoints = config.get("endpoints", {})
    process_sources(sources, endpoints)
    logger.info("Proceso completado / Process completed")


if __name__ == "__main__":
    main()
