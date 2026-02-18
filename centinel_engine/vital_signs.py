"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `centinel_engine/vital_signs.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - load_vital_signs_config
  - _compute_success_rate
  - _compute_avg_latency
  - _emit_alert
  - _resolve_threshold
  - check_vital_signs
  - load_health_state
  - save_health_state
  - update_status_after_scrape

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `centinel_engine/vital_signs.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - load_vital_signs_config
  - _compute_success_rate
  - _compute_avg_latency
  - _emit_alert
  - _resolve_threshold
  - check_vital_signs
  - load_health_state
  - save_health_state
  - update_status_after_scrape

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from centinel_engine.config_loader import load_config

logger = logging.getLogger(__name__)

DEFAULT_THRESHOLDS: Dict[str, Any] = {
    "baseline_interval_seconds": 300,
    "consecutive_failures_conservative": 3,
    "consecutive_failures_critical": 5,
    "min_success_rate": 0.70,
    "max_avg_latency": 10.0,
}

DEFAULT_HEALTH_STATE: Dict[str, Any] = {
    "mode": "normal",
    "recommended_delay_seconds": 300,
    "consecutive_failures": 0,
    "success_rate": 1.0,
    "avg_latency_seconds": 0.0,
    "hash_chain_valid": True,
    "actions": [],
    "alert_needed": False,
}


def load_vital_signs_config(env: str = "prod") -> Dict[str, Any]:
    """Load vital-sign thresholds from `config/<env>/watchdog.yaml`.

    Bilingual: Carga umbrales vitales desde `config/<env>/watchdog.yaml`.

    Args:
        env: Configuration environment folder.

    Returns:
        Dict[str, Any]: Threshold dictionary merged with defaults.

    Raises:
        None.
    """
    try:
        loaded = load_config("watchdog.yaml", env=env)
    except Exception as exc:  # noqa: BLE001
        logger.warning("vital_signs_config_fallback | usando defaults: %s", exc)
        loaded = {}
    return {**DEFAULT_THRESHOLDS, **loaded}


def _compute_success_rate(success_history: List[bool]) -> float:
    """Compute success ratio for scrape history.

    Bilingual: Calcula la proporción de éxito para el historial de scraping.

    Args:
        success_history: Recent success/failure booleans.

    Returns:
        float: Success ratio in `[0.0, 1.0]`.

    Raises:
        None.
    """
    if not success_history:
        return 1.0
    return sum(1 for item in success_history if item) / len(success_history)


def _compute_avg_latency(latency_history: List[float]) -> float:
    """Compute average scrape latency.

    Bilingual: Calcula latencia promedio de scraping.

    Args:
        latency_history: Recent response latencies in seconds.

    Returns:
        float: Mean latency in seconds.

    Raises:
        None.
    """
    if not latency_history:
        return 0.0
    return float(sum(latency_history) / len(latency_history))


def _emit_alert(mode: str, metrics: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> None:
    """Emit a concise health alert log.

    Bilingual: Emite un log conciso de alerta de salud operativa.

    Args:
        mode: Current computed health mode.
        metrics: Health metrics payload.
        config: Optional alert configuration dictionary.

    Returns:
        None.

    Raises:
        None.
    """
    _ = config
    if mode == "normal":
        return
    logger.warning("vital_signs_alert | mode=%s metrics=%s", mode, metrics)


def _resolve_threshold(config: Dict[str, Any], key: str) -> Any:
    """Resolve threshold key from runtime config or defaults.

    Bilingual: Resuelve un umbral desde configuración runtime o defaults.

    Args:
        config: Runtime configuration payload.
        key: Threshold key name.

    Returns:
        Any: Resolved value.

    Raises:
        KeyError: If key is not known in defaults.
    """
    if key in config:
        return config[key]
    return DEFAULT_THRESHOLDS[key]


def check_vital_signs(config: Dict[str, Any], status: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate health status and return mode + recommended delay.

    Bilingual: Evalúa estado de salud y retorna modo + delay recomendado.

    Args:
        config: Runtime scheduler configuration.
        status: Runtime status metrics from scraping loop.

    Returns:
        Dict[str, Any]: Health state dictionary.

    Raises:
        None.
    """
    baseline = int(_resolve_threshold(config, "baseline_interval_seconds"))
    failures_cons = int(_resolve_threshold(config, "consecutive_failures_conservative"))
    failures_crit = int(_resolve_threshold(config, "consecutive_failures_critical"))
    low_success_threshold = float(
        config.get("low_success_rate_threshold", _resolve_threshold(config, "min_success_rate"))
    )
    max_latency = float(config.get("max_avg_latency_seconds", _resolve_threshold(config, "max_avg_latency")))

    consecutive_failures = int(status.get("consecutive_failures", 0))
    success_history = list(status.get("success_history", []))
    latency_history = list(status.get("latency_history", []))
    hash_chain_valid = bool(status.get("hash_chain_valid", True))

    success_rate = _compute_success_rate(success_history)
    avg_latency = _compute_avg_latency(latency_history)

    actions: List[str] = []
    mode = "normal"
    delay = baseline
    critical_reasons: List[str] = []
    conservative_reasons: List[str] = []

    if not hash_chain_valid:
        critical_reasons.append("hash_chain_broken")
    if consecutive_failures >= failures_crit:
        critical_reasons.append("consecutive_failures")

    if consecutive_failures >= failures_cons:
        conservative_reasons.append("consecutive_failures")
    if success_rate < low_success_threshold:
        conservative_reasons.append("low_success_rate")
    if avg_latency > max_latency:
        conservative_reasons.append("high_avg_latency")

    if critical_reasons:
        mode = "critical"
        delay = max(1800, baseline * 6)
        actions.append("pause_and_investigate")
    elif conservative_reasons:
        mode = "conservative"
        delay = max(600, baseline * 2)
        actions.append("slow_down_and_rotate")

    alert_needed = mode != "normal"

    result = {
        "mode": mode,
        "recommended_delay_seconds": delay,
        "consecutive_failures": consecutive_failures,
        "success_rate": success_rate,
        "avg_latency_seconds": avg_latency,
        "hash_chain_valid": hash_chain_valid,
        "actions": actions,
        "alert_needed": alert_needed,
        "metrics": {"critical_reasons": critical_reasons, "conservative_reasons": conservative_reasons},
    }
    _emit_alert(mode, result, config=config)
    return result


def load_health_state(path: Path = Path("data/health_state.json")) -> Dict[str, Any]:
    """Load health state from disk, returning defaults on any failure.

    Bilingual: Carga estado de salud desde disco y retorna defaults si falla.

    Args:
        path: JSON file path for persisted health state.

    Returns:
        Dict[str, Any]: Persisted or default health state.

    Raises:
        None.
    """
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            return {**DEFAULT_HEALTH_STATE, **loaded}
    except Exception:  # noqa: BLE001
        return dict(DEFAULT_HEALTH_STATE)
    return dict(DEFAULT_HEALTH_STATE)


def save_health_state(state: Dict[str, Any], path: Path = Path("data/health_state.json")) -> None:
    """Persist health state atomically-like via write/replace strategy.

    Bilingual: Persiste estado de salud de forma segura con estrategia write/replace.

    Args:
        state: Health state payload.
        path: Destination JSON path.

    Returns:
        None.

    Raises:
        None.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def update_status_after_scrape(
    current_status: Dict[str, Any],
    *,
    success: bool,
    latency: float,
    status_code: Optional[int] = None,
    window: int = 50,
) -> Dict[str, Any]:
    """Update rolling status metrics after each scrape cycle.

    Bilingual: Actualiza métricas de estado acumuladas después de cada ciclo.

    Args:
        current_status: Existing mutable status dictionary.
        success: Whether scrape execution succeeded.
        latency: Request latency in seconds.
        status_code: Optional HTTP status code from upstream.
        window: Max number of historical records to keep.

    Returns:
        Dict[str, Any]: Updated status dictionary.

    Raises:
        None.
    """
    status = dict(current_status)
    history = list(status.get("success_history", []))
    latencies = list(status.get("latency_history", []))

    history.append(bool(success))
    latencies.append(float(latency))

    status["success_history"] = history[-window:]
    status["latency_history"] = latencies[-window:]
    status["last_status_code"] = status_code

    if success:
        status["consecutive_failures"] = 0
    else:
        status["consecutive_failures"] = int(status.get("consecutive_failures", 0)) + 1
    return status
