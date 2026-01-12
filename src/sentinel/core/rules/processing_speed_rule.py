from __future__ import annotations

from typing import List, Optional

from sentinel.core.rules.common import (
    extract_actas_mesas_counts,
    extract_department,
    parse_timestamp,
)


def apply(
    current_data: dict, previous_data: Optional[dict], config: dict
) -> List[dict]:
    """
    Evalúa la capacidad de procesamiento físico de actas en intervalos cortos.

    La regla calcula la velocidad de procesamiento de actas entre snapshots,
    normaliza la tasa a 15 minutos y la compara contra un umbral máximo. Si se
    supera el umbral, se genera una alerta de carga automatizada no humana.

    Args:
        current_data: Snapshot JSON actual del CNE.
        previous_data: Snapshot JSON anterior (None en el primer snapshot).
        config: Sección de configuración específica de la regla desde config.yaml.

    Returns:
        Lista de alertas en formato estándar (vacía si todo normal).

    English:
        Evaluates physical processing capacity for tally sheets over short intervals.

        The rule computes the processing speed between snapshots, normalizes the
        rate to a 15-minute window, and compares it against a maximum threshold. If
        exceeded, a high-severity alert is issued for non-human automated loading.

    Args:
        current_data: Current CNE JSON snapshot.
        previous_data: Previous JSON snapshot (None for the first snapshot).
        config: Rule-specific configuration section from config.yaml.

    Returns:
        List of alerts in the standard format (empty if normal).
    """
    alerts: List[dict] = []
    if not previous_data:
        return alerts

    current_ts = parse_timestamp(current_data)
    previous_ts = parse_timestamp(previous_data)
    if not current_ts or not previous_ts:
        return alerts

    delta_minutes = (current_ts - previous_ts).total_seconds() / 60
    if delta_minutes <= 0:
        return alerts

    current_actas = extract_actas_mesas_counts(current_data).get("actas_procesadas")
    previous_actas = extract_actas_mesas_counts(previous_data).get("actas_procesadas")
    if current_actas is None or previous_actas is None:
        return alerts

    delta_actas = current_actas - previous_actas
    if delta_actas <= 0:
        return alerts

    rate_per_15min = (delta_actas / delta_minutes) * 15
    max_rate = float(config.get("max_actas_per_15min", 500))
    if rate_per_15min > max_rate:
        alerts.append(
            {
                "type": "Carga Automatizada No Humana",
                "severity": "High",
                "department": extract_department(current_data),
                "justification": (
                    "La velocidad de procesamiento supera la capacidad física. "
                    f"delta_actas={delta_actas}, delta_min={delta_minutes:.2f}, "
                    f"tasa_15min={rate_per_15min:.2f}, umbral={max_rate:.2f}."
                ),
            }
        )

    return alerts
