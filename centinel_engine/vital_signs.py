"""Level 1 vital signs for resilient execution.

ES: Señales vitales mínimas para derivar modo operativo base.
EN: Minimal vital signs to derive baseline operating mode.
"""

from __future__ import annotations

from typing import Any


def check_vital_signs(metrics: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """ES: Evalúa métricas básicas y devuelve modo + delay recomendado.

    EN: Evaluate basic metrics and return mode + recommended delay.
    """
    cpu_percent = float(metrics.get("cpu_percent", 0.0))
    error_rate = float(metrics.get("error_rate", 0.0))

    cpu_warn = float(config.get("cpu_warn", 75.0))
    cpu_critical = float(config.get("cpu_critical", 90.0))
    error_warn = float(config.get("error_warn", 0.05))
    error_critical = float(config.get("error_critical", 0.15))

    if cpu_percent >= cpu_critical or error_rate >= error_critical:
        return {"mode": "critical", "delay_seconds": int(config.get("critical_delay_seconds", 1200))}

    if cpu_percent >= cpu_warn or error_rate >= error_warn:
        return {"mode": "elevated", "delay_seconds": int(config.get("elevated_delay_seconds", 300))}

    return {"mode": "normal", "delay_seconds": int(config.get("normal_delay_seconds", 60))}
