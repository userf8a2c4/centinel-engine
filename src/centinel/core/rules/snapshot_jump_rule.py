"""Regla de saltos anómalos entre snapshots.

Anomalous jump rule between snapshots.
"""

from __future__ import annotations

from datetime import timedelta
from typing import List, Optional

from centinel.core.rules.common import extract_total_votes, parse_timestamp
from centinel.core.rules.registry import rule


@rule(
    name="Saltos entre Snapshots",
    severity="CRITICAL",
    description="Detecta cambios >5% en 10 minutos.",
    config_key="snapshot_jump",
)
def apply(current_data: dict, previous_data: Optional[dict], config: dict) -> List[dict]:
    """
    Detecta saltos anómalos en votos emitidos entre snapshots cercanos.

    Si el cambio porcentual supera el umbral en una ventana de tiempo corta,
    se reporta alerta CRITICAL para observadores internacionales.

    Args:
        current_data: Snapshot JSON actual del CNE.
        previous_data: Snapshot JSON anterior (None en el primer snapshot).
        config: Configuración específica de la regla.

    Returns:
        Lista de alertas en formato estándar.

    English:
        Detects anomalous jumps in emitted votes between close snapshots.

        If the percentage change exceeds the threshold within a short window,
        a CRITICAL alert is reported for international observers.

    Args:
        current_data: Current CNE JSON snapshot.
        previous_data: Previous JSON snapshot (None for the first snapshot).
        config: Rule-specific configuration section.

    Returns:
        List of alerts in the standard format.
    """
    alerts: List[dict] = []
    if not previous_data:
        return alerts

    current_total = extract_total_votes(current_data)
    previous_total = extract_total_votes(previous_data)
    if not current_total or not previous_total:
        return alerts

    current_ts = parse_timestamp(current_data)
    previous_ts = parse_timestamp(previous_data)
    if not current_ts or not previous_ts:
        return alerts

    max_minutes = int(config.get("max_minutes", 10))
    if current_ts - previous_ts > timedelta(minutes=max_minutes):
        return alerts

    change_pct = (current_total - previous_total) / previous_total
    threshold = float(config.get("max_change_pct", 5)) / 100
    if abs(change_pct) <= threshold:
        return alerts

    message = "Salto anómalo en votos emitidos entre snapshots."
    alerts.append(
        {
            "type": "Salto Anómalo entre Snapshots",
            "severity": "CRITICAL",
            "message": message,
            "value": {"change_pct": change_pct},
            "threshold": {"max_change_pct": threshold},
            "result": (
                "CRITICAL",
                message,
                {"change_pct": change_pct},
                {"max_change_pct": threshold},
            ),
            "justification": (
                "Variación de votos emitidos excede el umbral en pocos minutos. "
                f"delta_pct={change_pct:.2%}, ventana_minutos={max_minutes}."
            ),
        }
    )

    return alerts
