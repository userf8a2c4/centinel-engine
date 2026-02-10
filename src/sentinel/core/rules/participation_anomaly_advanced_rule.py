"""Regla avanzada de participación anómala.

Advanced turnout anomaly rule.
"""

from __future__ import annotations

from typing import List, Optional

from sentinel.core.rules.common import (
    extract_department,
    extract_registered_voters,
    extract_total_votes,
)
from sentinel.core.rules.registry import rule


def _normalize_ratio(value: float) -> float:
    """Normaliza porcentajes a proporciones cuando superan 1.

    Permite aceptar valores en rango 0-1 o en porcentaje 0-100.

    English:
        Normalize percentages to proportions when values exceed 1.

        Allows inputs in the 0-1 range or percentage 0-100 range.
    """
    return value / 100 if value > 1 else value


@rule(
    name="Participación Anómala",
    severity="CRITICAL",
    description="Detecta participación fuera de rango y desviaciones >3σ.",
    config_key="participation_anomaly_advanced",
)
def apply(current_data: dict, previous_data: Optional[dict], config: dict) -> List[dict]:
    """
    Detecta participación anómala a nivel agregado.

    La regla calcula participación (votos emitidos / inscritos) y compara con
    rangos críticos. También evalúa desviaciones >3σ de la media histórica por
    departamento si existe referencia en configuración.

    Args:
        current_data: Snapshot JSON actual del CNE.
        previous_data: Snapshot JSON anterior (None en el primer snapshot).
        config: Configuración específica de la regla.

    Returns:
        Lista de alertas en formato estándar.

    English:
        Detects anomalous turnout at the aggregate level.

        The rule computes turnout (votes / registered voters) and compares
        against critical ranges. It also evaluates >3σ deviations from
        historical departmental means when provided in configuration.

    Args:
        current_data: Current CNE JSON snapshot.
        previous_data: Previous JSON snapshot (None for the first snapshot).
        config: Rule-specific configuration section.

    Returns:
        List of alerts in the standard format.
    """
    del previous_data

    alerts: List[dict] = []
    department = extract_department(current_data)
    total_votes = extract_total_votes(current_data)
    registered = extract_registered_voters(current_data)
    if not total_votes or not registered:
        return alerts

    turnout = total_votes / registered

    min_turnout = float(config.get("min_turnout_pct", 40)) / 100
    max_turnout = float(config.get("max_turnout_pct", 90)) / 100

    if turnout < min_turnout or turnout > max_turnout:
        message = "Participación fuera del rango esperado para Honduras 2025."
        alerts.append(
            {
                "type": "Participación Fuera de Rango",
                "severity": "CRITICAL",
                "department": department,
                "message": message,
                "value": {"turnout": turnout},
                "threshold": {"min": min_turnout, "max": max_turnout},
                "result": (
                    "CRITICAL",
                    message,
                    {"turnout": turnout},
                    {"min": min_turnout, "max": max_turnout},
                ),
                "justification": (
                    "La participación agregada excede los límites críticos. "
                    f"turnout={turnout:.2%}, min={min_turnout:.2%}, "
                    f"max={max_turnout:.2%}."
                ),
            }
        )
        return alerts

    historical = config.get("historical_by_department", {})
    dept_reference = historical.get(department) if isinstance(historical, dict) else None
    mean_value = None
    std_value = None
    if isinstance(dept_reference, dict):
        mean_value = dept_reference.get("mean")
        std_value = dept_reference.get("std")
    else:
        mean_value = config.get("historical_mean")
        std_value = config.get("historical_std")

    if mean_value is None or std_value in (None, 0):
        return alerts

    mean_ratio = _normalize_ratio(float(mean_value))
    std_ratio = _normalize_ratio(float(std_value))
    if std_ratio == 0:
        return alerts

    z_score = (turnout - mean_ratio) / std_ratio
    if abs(z_score) <= 3:
        return alerts

    message = "Participación se desvía más de 3σ de la media histórica."
    alerts.append(
        {
            "type": "Participación Anómala Histórica",
            "severity": "WARNING",
            "department": department,
            "message": message,
            "value": {"turnout": turnout, "z_score": z_score},
            "threshold": {"historical_mean": mean_ratio, "historical_std": std_ratio},
            "result": (
                "WARNING",
                message,
                {"turnout": turnout, "z_score": z_score},
                {"historical_mean": mean_ratio, "historical_std": std_ratio},
            ),
            "justification": (
                "La participación excede ±3σ respecto a la media histórica. "
                f"turnout={turnout:.2%}, mean={mean_ratio:.2%}, "
                f"std={std_ratio:.2%}, z={z_score:.2f}."
            ),
        }
    )

    return alerts
