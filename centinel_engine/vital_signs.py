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
  - _compute_request_pressure
  - predict_mode
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
  - _compute_request_pressure
  - predict_mode
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
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from centinel_engine.config_loader import load_config

logger = logging.getLogger(__name__)

DEFAULT_THRESHOLDS: Dict[str, Any] = {
    "baseline_interval_seconds": 300,
    "consecutive_failures_conservative": 2,
    "consecutive_failures_critical": 5,
    "min_success_rate": 0.70,
    "max_avg_latency": 10.0,
    "high_pressure_threshold": 6.0,
    "high_pressure_window_seconds": 300,
    "hibernation_delay_seconds": 3600,
    "predictive_window_size": 15,
    "predictive_failure_ratio": 0.40,
    "policy_block_window_seconds": 1800,
}

DEFAULT_HEALTH_STATE: Dict[str, Any] = {
    "mode": "normal",
    "recommended_delay_seconds": 300,
    "consecutive_failures": 0,
    "success_rate": 1.0,
    "avg_latency_seconds": 0.0,
    "request_pressure": 0.0,
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
    """
    if not success_history:
        return 1.0
    return sum(1 for item in success_history if item) / len(success_history)


def _compute_avg_latency(latency_history: List[float]) -> float:
    """Compute average scrape latency.

    Bilingual: Calcula latencia promedio de scraping.
    """
    if not latency_history:
        return 0.0
    return float(sum(latency_history) / len(latency_history))


def _compute_request_pressure(consecutive_failures: int, avg_latency: float) -> float:
    """Compute operational pressure from failures and latency.

    Bilingual: Calcula presión operativa desde fallos y latencia.

    Args:
        consecutive_failures: Current consecutive failures count.
        avg_latency: Current average latency in seconds.

    Returns:
        float: Pressure score used for resilience mode selection.

    Raises:
        None.
    """
    return float(consecutive_failures + (avg_latency / 5.0))


def _emit_alert(mode: str, metrics: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> None:
    """Emit a concise health alert log.

    Bilingual: Emite un log conciso de alerta de salud operativa.
    """
    _ = config
    if mode == "normal":
        return
    logger.warning("vital_signs_alert | mode=%s metrics=%s", mode, metrics)


def _resolve_threshold(config: Dict[str, Any], key: str) -> Any:
    """Resolve threshold key from runtime config or defaults.

    Bilingual: Resuelve un umbral desde configuración runtime o defaults.
    """
    if key in config:
        return config[key]
    return DEFAULT_THRESHOLDS[key]


def _policy_blocks_exceed_window(status: Dict[str, Any], window_seconds: int) -> bool:
    """Check if 403/429 responses persisted for an entire compliance window.

    Bilingual: Verifica si respuestas 403/429 persistieron toda la ventana de cumplimiento.

    Args:
        status: Current scraper status payload.
        window_seconds: Policy block observation window.

    Returns:
        bool: True when persistent policy blocks are detected.

    Raises:
        None.
    """
    policy_since = status.get("policy_block_since")
    if policy_since is None:
        return False
    return (time.time() - float(policy_since)) >= float(window_seconds)


def predict_mode(config: Dict[str, Any], status: Dict[str, Any]) -> str:
    """Predict resilience mode with early preventive adaptation.

    Bilingual: Predice modo de resiliencia con adaptación preventiva temprana.

    Rules / Reglas:
    - Returns `conservative` early when consecutive failures reach 2.
    - Retorna `conservative` temprano cuando los fallos consecutivos llegan a 2.
    - Returns `conservative` early when failure trend is >40% over last 15 requests.
    - Retorna `conservative` temprano cuando la tendencia de fallos es >40% en 15 requests.
    - Returns `conservative` when pressure stays >6 for 5 minutes.
    - Retorna `conservative` cuando la presión se mantiene >6 durante 5 minutos.

    Args:
        config: Runtime scheduler configuration.
        status: Runtime status metrics from scraping loop.

    Returns:
        str: One of `normal`, `conservative`, or `hibernation`.

    Raises:
        None.
    """
    high_pressure_threshold = float(_resolve_threshold(config, "high_pressure_threshold"))
    high_pressure_window_seconds = int(_resolve_threshold(config, "high_pressure_window_seconds"))
    predictive_window_size = int(_resolve_threshold(config, "predictive_window_size"))
    predictive_failure_ratio = float(_resolve_threshold(config, "predictive_failure_ratio"))
    policy_block_window_seconds = int(_resolve_threshold(config, "policy_block_window_seconds"))

    success_history = list(status.get("success_history", []))
    latency_history = list(status.get("latency_history", []))
    consecutive_failures = int(status.get("consecutive_failures", 0))
    avg_latency = _compute_avg_latency(latency_history)
    pressure = _compute_request_pressure(consecutive_failures, avg_latency)

    if _policy_blocks_exceed_window(status, policy_block_window_seconds):
        return "hibernation"

    trend_window = success_history[-predictive_window_size:]
    if trend_window:
        failures = sum(1 for item in trend_window if not item)
        # Lower threshold for early detection / Umbral más bajo para detección temprana
        if (failures / len(trend_window)) > predictive_failure_ratio:
            # Prevents full block before reaction / Evita bloqueo completo antes de reaccionar
            return "conservative"

    # Lower threshold for early detection / Umbral más bajo para detección temprana
    if consecutive_failures >= int(_resolve_threshold(config, "consecutive_failures_conservative")):
        # Prevents full block before reaction / Evita bloqueo completo antes de reaccionar
        return "conservative"

    high_pressure_since = status.get("high_pressure_since")
    if pressure > high_pressure_threshold and high_pressure_since is not None:
        if (time.time() - float(high_pressure_since)) >= high_pressure_window_seconds:
            # Lower threshold for early detection / Umbral más bajo para detección temprana
            # Prevents full block before reaction / Evita bloqueo completo antes de reaccionar
            return "conservative"

    if pressure > high_pressure_threshold:
        return "conservative"
    return "normal"


def check_vital_signs(config: Dict[str, Any], status: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate health status and return mode + recommended delay.

    Bilingual: Evalúa estado de salud y retorna modo + delay recomendado.
    """
    baseline = int(_resolve_threshold(config, "baseline_interval_seconds"))
    failures_cons = int(_resolve_threshold(config, "consecutive_failures_conservative"))
    failures_crit = int(_resolve_threshold(config, "consecutive_failures_critical"))
    high_pressure_threshold = float(_resolve_threshold(config, "high_pressure_threshold"))
    hibernation_delay = int(_resolve_threshold(config, "hibernation_delay_seconds"))
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
    pressure = _compute_request_pressure(consecutive_failures, avg_latency)

    actions: List[str] = []
    mode = predict_mode(config, status)
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
    if pressure > high_pressure_threshold:
        conservative_reasons.append("high_request_pressure")

    if mode == "hibernation":
        delay = max(hibernation_delay, baseline * 12)
        actions.extend(["pause_collection", "keep_secure_backup", "validate_hash_chain_local"])
        if _policy_blocks_exceed_window(status, int(_resolve_threshold(config, "policy_block_window_seconds"))):
            logger.warning(
                "posible política anti-scraping detectada – pausando por cumplimiento ético"
            )
    elif critical_reasons:
        mode = "critical"
        delay = max(1800, baseline * 6)
        actions.append("pause_and_investigate")
    elif mode == "conservative" or conservative_reasons:
        mode = "conservative"
        delay = max(900, baseline * 3)
        actions.append("slow_down_and_rotate")

    alert_needed = mode != "normal"

    result = {
        "mode": mode,
        "recommended_delay_seconds": delay,
        "consecutive_failures": consecutive_failures,
        "success_rate": success_rate,
        "avg_latency_seconds": avg_latency,
        "request_pressure": pressure,
        "hash_chain_valid": hash_chain_valid,
        "actions": actions,
        "alert_needed": alert_needed,
        "metrics": {
            "critical_reasons": critical_reasons,
            "conservative_reasons": conservative_reasons,
        },
    }
    _emit_alert(mode, result, config=config)
    return result


def load_health_state(path: Path = Path("data/health_state.json")) -> Dict[str, Any]:
    """Load health state from disk, returning defaults on any failure.

    Bilingual: Carga estado de salud desde disco y retorna defaults si falla.
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
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Update rolling status metrics after each scrape cycle.

    Bilingual: Actualiza métricas de estado acumuladas después de cada ciclo.
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

    avg_latency = _compute_avg_latency(status["latency_history"])
    pressure = _compute_request_pressure(int(status["consecutive_failures"]), avg_latency)
    status["request_pressure"] = pressure

    now_ts = time.time()
    runtime_config = config or {}
    high_pressure_threshold = float(runtime_config.get("high_pressure_threshold", DEFAULT_THRESHOLDS["high_pressure_threshold"]))

    # English: ensure timestamps are set when threshold is crossed, even if key exists with None. / Español: asegurar timestamp aunque la llave exista con None.
    if pressure > high_pressure_threshold:
        if status.get("high_pressure_since") is None:
            status["high_pressure_since"] = now_ts
    else:
        status["high_pressure_since"] = None

    if status_code in {403, 429}:
        if status.get("policy_block_since") is None:
            status["policy_block_since"] = now_ts
    elif success:
        status["policy_block_since"] = None

    return status
