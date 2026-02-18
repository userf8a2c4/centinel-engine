# Vital Signs Module
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

"""Vital signs monitoring for resilient, ethical scrape cadence adaptation.

This module evaluates operational telemetry ("vital signs") from the latest scrape
cycle and recommends an adaptive delay while preserving ethical constraints.
Implements Level 1 homeostasis: deterministic, auditable, 100% reproducible.

Este modulo evalua telemetria operativa ("signos vitales") del ultimo ciclo de
scraping y recomienda un delay adaptativo preservando limites eticos.
Implementa Nivel 1 de homeostasis: deterministico, auditable, 100% reproducible.
"""

from __future__ import annotations

import json
import logging
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from centinel_engine.config_loader import load_config
from centinel_engine.telegram_hook import send_alert_via_telegram

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default thresholds / Umbrales por defecto
# ---------------------------------------------------------------------------
DEFAULT_THRESHOLDS: Dict[str, Any] = {
    "consecutive_failures_conservative": 3,
    "consecutive_failures_critical": 5,
    "min_success_rate": 0.70,
    "max_avg_latency": 10.0,
    "success_history_window": 10,
}

# Default health state returned when file is missing or corrupted /
# Estado de salud por defecto cuando el archivo no existe o esta corrupto.
DEFAULT_HEALTH_STATE: Dict[str, Any] = {
    "mode": "normal",
    "recommended_delay_seconds": 300,
    "alert_needed": False,
    "consecutive_failures": 0,
    "success_history": [],
    "latency_history": [],
    "hash_chain_valid": True,
    "metrics": {},
}




def load_vital_signs_config(env: str = "prod") -> Dict[str, Any]:
    """Load vital-signs thresholds from centralized config storage.

    Bilingual: Carga umbrales de signos vitales desde el almacenamiento
    centralizado de configuración.

    Args:
        env: Environment folder under ``config``.

    Returns:
        Vital-sign thresholds dictionary, or defaults when unavailable.
    """
    try:
        loaded = load_config("rules.yaml", env=env)
    except ValueError as exc:
        logger.error("vital_signs_config_error | error de config de signos vitales: %s", exc)
        return dict(DEFAULT_THRESHOLDS)

    candidate = loaded.get("vital_signs", loaded) if isinstance(loaded, dict) else {}
    if not isinstance(candidate, dict):
        return dict(DEFAULT_THRESHOLDS)
    return {**DEFAULT_THRESHOLDS, **candidate}

def _compute_success_rate(success_history: List[bool]) -> float:
    """Compute success rate from recent history.

    Bilingual: Calcula la tasa de exito a partir del historial reciente.

    Args:
        success_history: List of booleans (True = success, False = failure).

    Returns:
        Float between 0.0 and 1.0, or 1.0 if history is empty.
    """
    if not success_history:
        return 1.0
    return sum(1 for s in success_history if s) / len(success_history)


def _compute_avg_latency(latency_history: List[float]) -> float:
    """Compute average latency from recent history.

    Bilingual: Calcula la latencia promedio a partir del historial reciente.

    Args:
        latency_history: List of latency values in seconds.

    Returns:
        Average latency in seconds, or 0.0 if history is empty.
    """
    if not latency_history:
        return 0.0
    return sum(latency_history) / len(latency_history)


def _emit_alert(mode: str, metrics: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> None:
    """Emit alert for degraded modes (stub for future encrypted email).

    Bilingual: Emite alerta para modos degradados (stub para email cifrado futuro).

    Args:
        mode: Current operational mode ('conservative' or 'critical').
        metrics: Dictionary with computed diagnostics.
        config: Runtime configuration dictionary used for extension flags.
    """
    msg = (
        f"[CENTINEL ALERT] Mode={mode} | "
        f"consecutive_failures={metrics.get('consecutive_failures', '?')}, "
        f"success_rate={metrics.get('success_rate', '?')}, "
        f"avg_latency={metrics.get('avg_latency', '?')}s, "
        f"hash_chain_valid={metrics.get('hash_chain_valid', '?')}"
    )
    logger.warning(msg)
    # Fallback print for environments without logging config /
    # Print de respaldo para entornos sin config de logging.
    print(msg)  # noqa: T201
    # TODO: stub for encrypted email notification /
    # TODO: stub para notificacion por email cifrado.

    # Future critical alert channel guarded by flag /
    # Canal futuro de alerta critica protegido por flag.
    effective_config: Dict[str, Any] = config or {}
    if mode == "critical" and bool(effective_config.get("ENABLE_TELEGRAM", False)):
        send_alert_via_telegram(msg, effective_config)


def check_vital_signs(
    config: Dict[str, Any],
    last_scrape_status: Dict[str, Any],
) -> Dict[str, Any]:
    """Evaluate system homeostasis and recommend the next scrape delay.

    Bilingual: Evalua la homeostasis del sistema y recomienda el proximo delay de scrape.

    Inspects the latest scrape telemetry and classifies the system as
    ``normal``, ``conservative``, or ``critical``. The recommendation always
    respects ethical lower bounds for public CNE scraping and only performs
    passive adaptation (no bypass attempts).

    Args:
        config: Configuration dictionary with keys such as:
            - scrape_interval_seconds (default: 300)
            - consecutive_failures_conservative (default: 3)
            - consecutive_failures_critical (default: 5)
            - min_success_rate (default: 0.70)
            - max_avg_latency (default: 10.0)
            - success_history_window (default: 10)
            - critical_delay_seconds (default: 1800)
        last_scrape_status: Dictionary with latest metrics, expected keys:
            - consecutive_failures (int)
            - success_history (list of bool)
            - latency_history (list of float, seconds)
            - hash_chain_valid (bool)
            - last_status_code (int, optional)

    Returns:
        Dictionary with keys:
            - mode: 'normal' | 'conservative' | 'critical'
            - recommended_delay_seconds: int
            - alert_needed: bool
            - consecutive_failures: int
            - success_history: list
            - latency_history: list
            - hash_chain_valid: bool
            - metrics: dict with computed diagnostics
    """
    # Resolve thresholds from config with defaults /
    # Resolver umbrales desde config con valores por defecto.
    thresholds = {**DEFAULT_THRESHOLDS, **config}

    base_delay = int(thresholds.get("scrape_interval_seconds", 300))
    cons_fail_conservative = int(thresholds.get("consecutive_failures_conservative", 3))
    cons_fail_critical = int(thresholds.get("consecutive_failures_critical", 5))
    min_success_rate = float(thresholds.get("min_success_rate", 0.70))
    max_avg_latency = float(thresholds.get("max_avg_latency", 10.0))
    window = int(thresholds.get("success_history_window", 10))
    critical_delay = int(thresholds.get("critical_delay_seconds", 1800))

    # Enforce ethical lower bound: never below 5 minutes /
    # Forzar limite etico minimo: nunca por debajo de 5 minutos.
    ethical_base_delay = max(base_delay, 300)

    # Extract metrics from last scrape status /
    # Extraer metricas del ultimo estado de scrape.
    consecutive_failures = int(last_scrape_status.get("consecutive_failures", 0))
    success_history: List[bool] = list(last_scrape_status.get("success_history", []))
    latency_history: List[float] = list(last_scrape_status.get("latency_history", []))
    hash_chain_valid = bool(last_scrape_status.get("hash_chain_valid", True))

    # Trim histories to window size / Recortar historiales al tamano de ventana.
    success_history = success_history[-window:]
    latency_history = latency_history[-window:]

    # Compute derived metrics / Calcular metricas derivadas.
    success_rate = _compute_success_rate(success_history)
    avg_latency = _compute_avg_latency(latency_history)

    # Determine operational mode with priority: critical > conservative > normal /
    # Determinar modo operativo con prioridad: critical > conservative > normal.
    mode = "normal"
    recommended_delay = ethical_base_delay

    # --- Conservative triggers / Disparadores de modo conservador ---
    conservative_reasons: List[str] = []
    if consecutive_failures >= cons_fail_conservative:
        conservative_reasons.append(
            f"consecutive_failures({consecutive_failures}) >= threshold({cons_fail_conservative})"
        )
    if success_rate < min_success_rate and len(success_history) > 0:
        conservative_reasons.append(f"success_rate({success_rate:.2f}) < min({min_success_rate})")
    if avg_latency > max_avg_latency and len(latency_history) > 0:
        conservative_reasons.append(f"avg_latency({avg_latency:.2f}s) > max({max_avg_latency}s)")

    if conservative_reasons:
        mode = "conservative"
        recommended_delay = max(600, ethical_base_delay * 2)

    # --- Critical triggers (override conservative) /
    # --- Disparadores criticos (sobreescriben conservador) ---
    critical_reasons: List[str] = []
    if consecutive_failures >= cons_fail_critical:
        critical_reasons.append(
            f"consecutive_failures({consecutive_failures}) >= critical_threshold({cons_fail_critical})"
        )
    if not hash_chain_valid:
        # Hash chain broken ALWAYS triggers critical /
        # Cadena de hashes rota SIEMPRE dispara critico.
        critical_reasons.append("hash_chain_broken")

    if critical_reasons:
        mode = "critical"
        recommended_delay = max(critical_delay, 1800)

    alert_needed = mode in {"conservative", "critical"}

    metrics: Dict[str, Any] = {
        "timestamp_epoch": int(time.time()),
        "ethical_minimum_delay": 300,
        "base_delay_requested": base_delay,
        "base_delay_effective": ethical_base_delay,
        "consecutive_failures": consecutive_failures,
        "success_rate": round(success_rate, 4),
        "avg_latency": round(avg_latency, 4),
        "hash_chain_valid": hash_chain_valid,
        "last_status_code": last_scrape_status.get("last_status_code"),
        "conservative_reasons": conservative_reasons,
        "critical_reasons": critical_reasons,
        "window_size": window,
        "success_history_len": len(success_history),
        "latency_history_len": len(latency_history),
    }

    state: Dict[str, Any] = {
        "mode": mode,
        "recommended_delay_seconds": int(recommended_delay),
        "alert_needed": alert_needed,
        "consecutive_failures": consecutive_failures,
        "success_history": success_history,
        "latency_history": latency_history,
        "hash_chain_valid": hash_chain_valid,
        "metrics": metrics,
    }

    logger.info(
        "Vital signs evaluated | Signos vitales evaluados: mode=%s, delay=%ss, alert=%s",
        state["mode"],
        state["recommended_delay_seconds"],
        state["alert_needed"],
    )

    # Emit alert if degraded / Emitir alerta si hay degradacion.
    if alert_needed:
        _emit_alert(mode, metrics, config=thresholds)

    return state


def load_health_state(
    path: Path = Path("data/health_state.json"),
) -> Dict[str, Any]:
    """Load persisted health state or return defaults if missing/corrupted.

    Bilingual: Carga el estado de salud persistido o retorna valores por defecto
    si no existe o esta corrupto.

    Args:
        path: Input JSON file path.

    Returns:
        Parsed state dictionary (never None).
    """
    if not path.exists():
        logger.info(
            "Health state not found, returning defaults | "
            "Estado de salud no encontrado, retornando valores por defecto: %s",
            path,
        )
        return dict(DEFAULT_HEALTH_STATE)

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Health state is not a dict")  # noqa: TRY301
        logger.info(
            "Health state loaded successfully | Estado de salud cargado correctamente: %s",
            path,
        )
        return payload
    except Exception:
        logger.warning(
            "Corrupted health state, returning defaults | "
            "Estado de salud corrupto, retornando valores por defecto: %s",
            path,
        )
        return dict(DEFAULT_HEALTH_STATE)


def save_health_state(
    state: Dict[str, Any],
    path: Path = Path("data/health_state.json"),
) -> None:
    """Save current health state atomically using tempfile.

    Bilingual: Guarda el estado de salud actual de forma atomica usando tempfile.

    Writes to a temporary file first, then renames to the target path to
    prevent corruption from partial writes or crashes.

    Args:
        state: State dictionary to persist.
        path: Output JSON file path.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(state, indent=2, ensure_ascii=False)

    # Atomic write: write to temp file then rename /
    # Escritura atomica: escribir a archivo temporal y renombrar.
    try:
        fd, tmp_path_str = tempfile.mkstemp(
            dir=str(path.parent),
            prefix=".health_state_",
            suffix=".tmp",
        )
        tmp_path = Path(tmp_path_str)
        try:
            with open(fd, "w", encoding="utf-8") as f:
                f.write(content)
            tmp_path.replace(path)
        except BaseException:
            # Cleanup temp file on failure / Limpiar archivo temporal si falla.
            if tmp_path.exists():
                tmp_path.unlink()
            raise
    except OSError as exc:
        logger.error(
            "Failed to save health state | No se pudo guardar estado de salud: %s",
            exc,
        )
        raise

    logger.info(
        "Health state saved atomically | Estado de salud guardado atomicamente: %s",
        path,
    )


# ---------------------------------------------------------------------------
# Integration helpers / Helpers de integracion
# ---------------------------------------------------------------------------


def update_status_after_scrape(
    current_state: Dict[str, Any],
    success: bool,
    latency: float,
    status_code: Optional[int] = None,
    hash_chain_valid: bool = True,
    window: int = 10,
) -> Dict[str, Any]:
    """Update the running status after a scrape attempt (for scheduler integration).

    Bilingual: Actualiza el estado corriente despues de un intento de scrape
    (para integracion con el scheduler).

    Args:
        current_state: The current accumulated state dictionary.
        success: Whether the scrape succeeded.
        latency: Request latency in seconds.
        status_code: HTTP status code (optional).
        hash_chain_valid: Whether the hash chain is still valid.
        window: History window size.

    Returns:
        Updated state dictionary ready for check_vital_signs().
    """
    # Update consecutive failures / Actualizar fallos consecutivos.
    if success:
        consecutive_failures = 0
    else:
        consecutive_failures = int(current_state.get("consecutive_failures", 0)) + 1

    # Update histories / Actualizar historiales.
    success_history: List[bool] = list(current_state.get("success_history", []))
    success_history.append(success)
    success_history = success_history[-window:]

    latency_history: List[float] = list(current_state.get("latency_history", []))
    latency_history.append(latency)
    latency_history = latency_history[-window:]

    return {
        "consecutive_failures": consecutive_failures,
        "success_history": success_history,
        "latency_history": latency_history,
        "hash_chain_valid": hash_chain_valid,
        "last_status_code": status_code,
    }


# ---------------------------------------------------------------------------
# Scheduler integration snippet (example) /
# Snippet de integracion con scheduler (ejemplo)
# ---------------------------------------------------------------------------
#
#   from centinel_engine.vital_signs import (
#       check_vital_signs, load_health_state, save_health_state,
#       update_status_after_scrape,
#   )
#
#   # Before scrape loop / Antes del ciclo de scrape:
#   health = load_health_state()
#   scrape_status = {
#       "consecutive_failures": health.get("consecutive_failures", 0),
#       "success_history": health.get("success_history", []),
#       "latency_history": health.get("latency_history", []),
#       "hash_chain_valid": health.get("hash_chain_valid", True),
#   }
#
#   # After each scrape / Despues de cada scrape:
#   scrape_status = update_status_after_scrape(
#       scrape_status, success=True, latency=2.3, status_code=200,
#   )
#   result = check_vital_signs(config, scrape_status)
#   save_health_state(result)
#   time.sleep(result["recommended_delay_seconds"])


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    dummy_config: Dict[str, Any] = {
        "scrape_interval_seconds": 300,
    }

    # Simulate a degraded scenario / Simular un escenario degradado.
    dummy_status: Dict[str, Any] = {
        "consecutive_failures": 4,
        "success_history": [True, True, False, False, False, False],
        "latency_history": [1.2, 2.1, 8.5, 12.0, 15.3, 11.0],
        "hash_chain_valid": True,
        "last_status_code": 503,
    }

    current_state = check_vital_signs(dummy_config, dummy_status)
    save_health_state(current_state)
    restored_state = load_health_state()

    print("Computed state / Estado calculado:")
    print(json.dumps(current_state, indent=2, ensure_ascii=False))
    print("\nRestored state / Estado restaurado:")
    print(json.dumps(restored_state, indent=2, ensure_ascii=False))
