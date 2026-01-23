"""Regla de votos nulos/blancos elevados.

High null/blank votes rule.
"""

from __future__ import annotations

from typing import List, Optional

from sentinel.core.rules.common import (
    extract_department,
    extract_vote_breakdown,
)
from sentinel.core.rules.registry import rule


@rule(
    name="Nulos y Blancos Elevados",
    severity="CRITICAL",
    description="Detecta porcentajes anómalos de votos nulos+blancos.",
    config_key="null_blank_votes",
)
def apply(
    current_data: dict, previous_data: Optional[dict], config: dict
) -> List[dict]:
    """
    Detecta porcentajes elevados de votos nulos y blancos.

    Se calcula (nulos + blancos) / total emitido. CRITICAL si supera 12%,
    WARNING si supera 8%.

    Args:
        current_data: Snapshot JSON actual del CNE.
        previous_data: Snapshot JSON anterior (None en el primer snapshot).
        config: Configuración específica de la regla.

    Returns:
        Lista de alertas en formato estándar.

    English:
        Detects elevated null and blank vote percentages.

        Computes (null + blank) / total emitted. CRITICAL if above 12%,
        WARNING if above 8%.

    Args:
        current_data: Current CNE JSON snapshot.
        previous_data: Previous JSON snapshot (None for the first snapshot).
        config: Rule-specific configuration section.

    Returns:
        List of alerts in the standard format.
    """
    del previous_data

    alerts: List[dict] = []
    breakdown = extract_vote_breakdown(current_data)
    total_votes = breakdown.get("total_votes")
    null_votes = breakdown.get("null_votes")
    blank_votes = breakdown.get("blank_votes")
    if not total_votes:
        return alerts

    null_blank = (null_votes or 0) + (blank_votes or 0)
    ratio = null_blank / total_votes

    warning_threshold = float(config.get("warning_pct", 8)) / 100
    critical_threshold = float(config.get("critical_pct", 12)) / 100

    severity = "INFO"
    threshold = warning_threshold
    if ratio > critical_threshold:
        severity = "CRITICAL"
        threshold = critical_threshold
    elif ratio > warning_threshold:
        severity = "WARNING"
        threshold = warning_threshold
    else:
        return alerts

    department = extract_department(current_data)
    message = "Porcentaje elevado de votos nulos y blancos."

    alerts.append(
        {
            "type": "Nulos/Blancos Elevados",
            "severity": severity,
            "department": department,
            "message": message,
            "value": {"ratio": ratio, "null_blank": null_blank},
            "threshold": {
                "warning_pct": warning_threshold,
                "critical_pct": critical_threshold,
            },
            "result": (
                severity,
                message,
                {"ratio": ratio, "null_blank": null_blank},
                {"warning_pct": warning_threshold, "critical_pct": critical_threshold},
            ),
            "justification": (
                "Se detectó porcentaje alto de votos nulos+blancos. "
                f"ratio={ratio:.2%}, nulos+blancos={null_blank}, "
                f"total={total_votes}."
            ),
        }
    )

    return alerts
