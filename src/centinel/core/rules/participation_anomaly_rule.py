# Participation Anomaly Rule Module
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

"""Regla para anomalías de participación y escrutinio.

Rule for participation and scrutiny anomalies.
"""

from __future__ import annotations

from typing import List, Optional

from centinel.core.rules.common import (
    extract_actas_mesas_counts,
    extract_department,
    extract_porcentaje_escrutado,
)
from centinel.core.rules.registry import rule


def _calculate_scrutiny_percentage(current_data: dict) -> Optional[float]:
    """Calcula el porcentaje escrutado desde múltiples fuentes.

    Usa el valor directo si existe, o calcula con actas procesadas/totales.

    English:
        Calculate the scrutiny percentage from multiple sources.

        Uses the direct value if available, or computes it from processed/total
        tally sheets.
    """
    percentage = extract_porcentaje_escrutado(current_data)
    if percentage is not None:
        return percentage
    actas = extract_actas_mesas_counts(current_data)
    actas_totales = actas.get("actas_totales")
    actas_procesadas = actas.get("actas_procesadas")
    if actas_totales and actas_procesadas is not None:
        return (actas_procesadas / actas_totales) * 100
    return None


@rule(
    name="Anomalía de Participación",
    severity="High",
    description="Detecta anomalías de participación y escrutinio entre snapshots.",
    config_key="participation_anomaly",
)
def apply(current_data: dict, previous_data: Optional[dict], config: dict) -> List[dict]:
    """
    Detecta anomalías de participación y escrutinio entre snapshots.

    La regla revisa saltos abruptos en el porcentaje escrutado y detecta
    inconsistencias cuando el número de actas procesadas supera al total
    reportado. Estos eventos pueden indicar actualización irregular o carga
    acelerada no compatible con los tiempos esperados del TREP.

    Args:
        current_data: Snapshot JSON actual del CNE.
        previous_data: Snapshot JSON anterior (None en el primer snapshot).
        config: Sección de configuración específica de la regla desde config.yaml.

    Returns:
        Lista de alertas en formato estándar (vacía si todo normal).

    English:
        Detects participation and scrutiny anomalies between snapshots.

        The rule flags abrupt jumps in the scrutiny percentage and inconsistencies
        where processed tally sheets exceed the reported total. These events can
        indicate irregular updates or automated loading inconsistent with expected
        TREP timing.

    Args:
        current_data: Current CNE JSON snapshot.
        previous_data: Previous JSON snapshot (None for the first snapshot).
        config: Rule-specific configuration section from config.yaml.

    Returns:
        List of alerts in the standard format (empty if normal).
    """
    alerts: List[dict] = []
    department = extract_department(current_data)

    actas = extract_actas_mesas_counts(current_data)
    actas_totales = actas.get("actas_totales")
    actas_procesadas = actas.get("actas_procesadas")

    if actas_totales is not None and actas_procesadas is not None:
        if actas_procesadas > actas_totales:
            alerts.append(
                {
                    "type": "Actas Procesadas Exceden Totales",
                    "severity": "High",
                    "department": department,
                    "justification": (
                        "Las actas procesadas superan el total reportado. "
                        f"actas_procesadas={actas_procesadas}, actas_totales={actas_totales}."
                    ),
                }
            )

    if previous_data:
        current_pct = _calculate_scrutiny_percentage(current_data)
        previous_pct = _calculate_scrutiny_percentage(previous_data)
        if current_pct is not None and previous_pct is not None:
            delta_pct = current_pct - previous_pct
            threshold = float(config.get("scrutiny_jump_pct", 5))
            if delta_pct >= threshold:
                alerts.append(
                    {
                        "type": "Salto Abrupto de Escrutinio",
                        "severity": "Medium",
                        "department": department,
                        "justification": (
                            "Se detectó un salto repentino en el % escrutado. "
                            f"delta_pct={delta_pct:.2f}%, umbral={threshold:.2f}%, "
                            f"previo={previous_pct:.2f}%, actual={current_pct:.2f}%."
                        ),
                    }
                )

    return alerts
