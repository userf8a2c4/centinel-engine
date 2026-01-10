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
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
import yaml
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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
config_path = DEFAULT_CONFIG_PATH


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

    return config


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
        resolved_path = config_path_override or config_path
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


def process_sources(sources: list[dict[str, Any]]) -> None:
    """Procesa fuentes reales y actualiza la cadena de hashes.

    Args:
        sources (list[dict[str, Any]]): Lista de fuentes configuradas.

    English:
        Process real sources and update the hash chain.

    Args:
        sources (list[dict[str, Any]]): Configured sources list.
    """
    previous_hash = "0" * 64

    for source in sources:
        endpoint = source.get("endpoint")
        if not endpoint:
            logger.error(
                "Fuente sin endpoint definido: %s / Source without endpoint: %s",
                source,
                source,
            )
            continue

        try:
            response = fetch_with_retry(endpoint)
            data = response.content
            current_hash = compute_hash(data)
            chained_hash = chain_hash(previous_hash, data)
            # Guarda data y hashes... (tu código original aquí)
            previous_hash = chained_hash
            logger.info(
                "Snapshot descargado y hasheado para %s / Snapshot downloaded and hashed for %s",
                source.get("id", "unknown"),
                source.get("id", "unknown"),
            )
            logger.debug(
                "current_hash=%s chained_hash=%s source=%s",
                current_hash,
                chained_hash,
                source.get("id", "unknown"),
            )
        except Exception as e:
            logger.error(
                "Fallo al descargar %s: %s / Failed to download %s: %s",
                endpoint,
                e,
                endpoint,
                e,
            )


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
            "No se encontraron fuentes en config.yaml / No sources found in config.yaml"
        )
        raise ValueError("No sources defined in config.yaml")

    process_sources(sources)
    logger.info("Proceso completado / Process completed")


if __name__ == "__main__":
    main()
