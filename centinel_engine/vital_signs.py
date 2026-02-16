"""Vital signs monitoring for resilient, ethical scrape cadence adaptation.

This module evaluates operational telemetry ("vital signs") from the latest scrape
cycle and recommends an adaptive delay while preserving ethical constraints.

Este módulo evalúa telemetría operativa ("signos vitales") del último ciclo de
scraping y recomienda un delay adaptativo preservando límites éticos.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


def _resolve_config(config: dict[str, Any]) -> dict[str, Any]:
    """Resolve runtime configuration, optionally merging a YAML file.

    English:
        Returns a copy of the provided configuration. If `config` contains a
        `health_config_path` key, the function attempts to load that YAML file
        and overlays the explicit dictionary values on top of file values.

    Español:
        Retorna una copia de la configuración provista. Si `config` contiene la
        clave `health_config_path`, la función intenta cargar ese YAML y aplica
        los valores explícitos del diccionario por encima de los del archivo.

    Args:
        config: Runtime configuration dictionary.

    Returns:
        A normalized configuration dictionary.
    """
    resolved = dict(config)
    yaml_path = resolved.get("health_config_path")

    if not yaml_path:
        return resolved

    config_path = Path(yaml_path)
    if not config_path.exists():
        logging.info(
            "Vital signs YAML config missing, using inline config only | "
            "YAML de signos vitales no existe, usando solo config en memoria: %s",
            config_path,
        )
        return resolved

    try:
        yaml_payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except Exception as exc:  # noqa: BLE001
        logging.info(
            "Failed to read YAML config, using inline config | "
            "No se pudo leer YAML, usando config en memoria: %s",
            exc,
        )
        return resolved

    if not isinstance(yaml_payload, dict):
        logging.info(
            "Invalid YAML format, expected object/dict | "
            "Formato YAML inválido, se esperaba objeto/dict: %s",
            config_path,
        )
        return resolved

    merged = {**yaml_payload, **resolved}
    return merged


def check_vital_signs(config: dict[str, Any], last_scrape_status: dict[str, Any]) -> dict[str, Any]:
    """Evaluate system homeostasis and recommend the next scrape delay.

    English:
        Inspects the latest scrape telemetry and classifies the system as
        `normal`, `conservative`, or `critical`. The recommendation always
        respects ethical lower bounds for public CNE scraping and only performs
        passive adaptation (no bypass attempts).

    Español:
        Inspecciona la telemetría más reciente del scraping y clasifica el
        sistema como `normal`, `conservative` o `critical`. La recomendación
        siempre respeta límites éticos mínimos para scraping público del CNE y
        solo realiza adaptación pasiva (sin intentos de evasión).

    Args:
        config: Configuration dictionary with keys such as:
            - scrape_interval_seconds (default: 300)
            - failure_threshold (default: 3)
            - latency_critical_seconds (default: 30)
            - critical_delay_seconds (default: 1800)
        last_scrape_status: Dictionary with latest metrics, expected keys include:
            - success_rate (0.0..1.0)
            - consecutive_failures (int)
            - avg_latency (seconds)
            - hash_chain_valid (bool)
            - last_status_code (int)

    Returns:
        Dictionary with keys:
            - mode: 'normal' | 'conservative' | 'critical'
            - recommended_delay_seconds: int
            - alert_needed: bool
            - metrics: dict with computed diagnostics
    """
    resolved_config = _resolve_config(config)

    base_delay = int(resolved_config.get("scrape_interval_seconds", 300))
    failure_threshold = int(resolved_config.get("failure_threshold", 3))
    latency_critical = float(resolved_config.get("latency_critical_seconds", 30.0))
    critical_delay = int(resolved_config.get("critical_delay_seconds", 1800))

    # Enforce ethical lower bound: never below 5 minutes /
    # Forzar límite ético mínimo: nunca por debajo de 5 minutos.
    ethical_base_delay = max(base_delay, 300)
    if ethical_base_delay != base_delay:
        logging.info(
            "Adjusted base delay to ethical minimum (300s) | "
            "Delay base ajustado al mínimo ético (300s): requested=%s effective=%s",
            base_delay,
            ethical_base_delay,
        )

    success_rate = float(last_scrape_status.get("success_rate", 1.0))
    consecutive_failures = int(last_scrape_status.get("consecutive_failures", 0))
    avg_latency = float(last_scrape_status.get("avg_latency", 0.0))
    hash_chain_valid = bool(last_scrape_status.get("hash_chain_valid", True))
    last_status_code = last_scrape_status.get("last_status_code")

    conservative_triggered = consecutive_failures >= failure_threshold or not hash_chain_valid
    critical_triggered = success_rate < 0.5 or avg_latency > latency_critical

    mode = "normal"
    recommended_delay_seconds = ethical_base_delay

    if conservative_triggered:
        mode = "conservative"
        recommended_delay_seconds = max(ethical_base_delay * 2, 600)

    if critical_triggered:
        # Critical has higher priority due to severe degradation /
        # Critical tiene mayor prioridad por degradación severa.
        mode = "critical"
        recommended_delay_seconds = max(critical_delay, 1800)

    alert_needed = mode in {"conservative", "critical"}

    metrics = {
        "timestamp_epoch": int(time.time()),
        "ethical_minimum_delay": 300,
        "base_delay_requested": base_delay,
        "base_delay_effective": ethical_base_delay,
        "failure_threshold": failure_threshold,
        "latency_critical_seconds": latency_critical,
        "critical_delay_seconds": critical_delay,
        "success_rate": success_rate,
        "consecutive_failures": consecutive_failures,
        "avg_latency": avg_latency,
        "hash_chain_valid": hash_chain_valid,
        "last_status_code": last_status_code,
        "conservative_triggered": conservative_triggered,
        "critical_triggered": critical_triggered,
    }

    state = {
        "mode": mode,
        "recommended_delay_seconds": int(recommended_delay_seconds),
        "alert_needed": alert_needed,
        "metrics": metrics,
    }

    logging.info(
        "Vital signs evaluated | Signos vitales evaluados: mode=%s, delay=%ss, alert=%s",
        state["mode"],
        state["recommended_delay_seconds"],
        state["alert_needed"],
    )
    return state


def save_health_state(state: dict[str, Any], path: Path = Path("data/health_state.json")) -> None:
    """Persist health state as pretty JSON.

    English:
        Writes the provided state dictionary to disk in UTF-8, pretty-printed
        JSON format. Parent directories are created if needed.

    Español:
        Escribe el diccionario de estado en disco en formato JSON legible
        (pretty), codificado en UTF-8. Crea directorios padre si no existen.

    Args:
        state: State dictionary to persist.
        path: Output JSON file path.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    logging.info(
        "Health state saved successfully | Estado de salud guardado correctamente: %s",
        path,
    )


def load_health_state(path: Path = Path("data/health_state.json")) -> dict[str, Any] | None:
    """Load persisted health state if available.

    English:
        Reads and parses the saved health state JSON file. Returns `None`
        when the file does not exist.

    Español:
        Lee y parsea el archivo JSON de estado de salud guardado. Retorna
        `None` cuando el archivo no existe.

    Args:
        path: Input JSON file path.

    Returns:
        Parsed state dictionary or `None` when unavailable.
    """
    if not path.exists():
        logging.info(
            "Health state not found, starting clean | "
            "Estado de salud no encontrado, iniciando limpio: %s",
            path,
        )
        return None

    payload = json.loads(path.read_text(encoding="utf-8"))
    logging.info(
        "Health state loaded successfully | Estado de salud cargado correctamente: %s",
        path,
    )
    return payload


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    dummy_config = {
        "scrape_interval_seconds": 300,
        "failure_threshold": 3,
        "latency_critical_seconds": 30,
        "critical_delay_seconds": 1800,
    }

    dummy_last_scrape_status = {
        "success_rate": 0.42,
        "consecutive_failures": 2,
        "avg_latency": 34.8,
        "hash_chain_valid": True,
        "last_status_code": 503,
    }

    # Example usage for local smoke testing /
    # Ejemplo de uso para pruebas rápidas locales.
    current_state = check_vital_signs(dummy_config, dummy_last_scrape_status)
    save_health_state(current_state)
    restored_state = load_health_state()

    print("Computed state / Estado calculado:")
    print(json.dumps(current_state, indent=2, ensure_ascii=False))
    print("\nRestored state / Estado restaurado:")
    print(json.dumps(restored_state, indent=2, ensure_ascii=False))
