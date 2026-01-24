"""Regla de turnout imposible para auditoría electoral.

Impossible turnout rule for electoral audits.
"""

from __future__ import annotations

from typing import List, Optional

from sentinel.core.rules.common import (
    extract_department,
    extract_registered_voters,
    extract_total_votes,
)
from sentinel.core.rules.registry import rule


@rule(
    name="Turnout Imposible",
    severity="CRITICAL",
    description="Detecta turnout <0% o >100% respecto al padrón.",
    config_key="turnout_impossible",
)
def apply(
    current_data: dict, previous_data: Optional[dict], config: dict
) -> List[dict]:
    """
    Detecta turnout imposible (negativo o mayor a 100%).

    La regla calcula turnout (votos emitidos / inscritos) y reporta
    alertas críticas si el valor está fuera del rango permitido.

    Args:
        current_data: Snapshot JSON actual del CNE.
        previous_data: Snapshot JSON anterior (None en el primer snapshot).
        config: Configuración específica de la regla.

    Returns:
        Lista de alertas en formato estándar.

    English:
        Detects impossible turnout (negative or above 100%).

        The rule computes turnout (votes / registered voters) and reports
        critical alerts if the value is outside allowed bounds.

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
    if total_votes is None or registered in (None, 0):
        return alerts

    turnout = total_votes / registered
    min_turnout = float(config.get("min_turnout_pct", 0)) / 100
    max_turnout = float(config.get("max_turnout_pct", 100)) / 100

    if min_turnout <= turnout <= max_turnout:
        return alerts

    message = "Turnout fuera de límites lógicos (imposible)."
    alerts.append(
        {
            "type": "Turnout Imposible",
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
                "El turnout calculado está fuera del rango permitido. "
                f"turnout={turnout:.2%}, min={min_turnout:.2%}, "
                f"max={max_turnout:.2%}."
            ),
        }
    )

    return alerts
