"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `src/centinel/core/rules/trend_shift_rule.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - _compute_percentages
  - apply

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `src/centinel/core/rules/trend_shift_rule.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - _compute_percentages
  - apply

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
"""

# Trend Shift Rule Module
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



from __future__ import annotations

from typing import Dict, List, Optional

from centinel.core.rules.common import (
    extract_candidate_votes,
    extract_department,
    parse_timestamp,
)
from centinel.core.rules.registry import rule


def _compute_percentages(votes: Dict[str, Dict[str, object]]) -> Dict[str, float]:
    """Calcula porcentaje de votos por candidato respecto al total.

    Retorna un mapa id->porcentaje y evita divisiones por cero.

    English:
        Compute vote percentages per candidate relative to the total.

        Returns an id->percentage map and avoids division by zero.
    """
    total_votes = sum(int(candidate.get("votes") or 0) for candidate in votes.values())
    if total_votes <= 0:
        return {}
    return {
        candidate_id: (int(candidate.get("votes") or 0) / total_votes) * 100
        for candidate_id, candidate in votes.items()
    }


@rule(
    name="Desviación de Tendencia",
    severity="High",
    description="Detecta cambios de tendencia en votos por candidato entre snapshots.",
    config_key="trend_shift",
)
def apply(current_data: dict, previous_data: Optional[dict], config: dict) -> List[dict]:
    """
    Evalúa estabilidad de tendencia comparando el delta de votos con la tendencia histórica.

    La regla calcula el porcentaje de votos nuevos por candidato entre snapshots y lo
    compara con el porcentaje histórico acumulado. Si la diferencia absoluta supera el
    umbral configurado y el intervalo de tiempo es menor al máximo permitido, se genera
    una alerta de alta severidad por posible desvío de tendencia en tiempo real.

    Args:
        current_data: Snapshot JSON actual del CNE.
        previous_data: Snapshot JSON anterior (None en el primer snapshot).
        config: Sección de configuración específica de la regla desde config.yaml.

    Returns:
        Lista de alertas en formato estándar (vacía si todo normal).

    English:
        Evaluates trend stability by comparing delta vote percentages with historical share.

        The rule computes the percentage of new votes per candidate between snapshots
        and compares it to the historical accumulated percentage. If the absolute
        difference exceeds the configured threshold within the allowed time window, a
        high-severity alert is raised for potential real-time trend deviation.

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

    delta_hours = (current_ts - previous_ts).total_seconds() / 3600
    max_hours = float(config.get("max_hours", 3))
    if delta_hours <= 0 or delta_hours > max_hours:
        return alerts

    current_votes = extract_candidate_votes(current_data)
    previous_votes = extract_candidate_votes(previous_data)
    if not current_votes or not previous_votes:
        return alerts

    delta_votes = {}
    for candidate_id, current_candidate in current_votes.items():
        previous_candidate = previous_votes.get(candidate_id, {})
        delta_votes[candidate_id] = int(current_candidate.get("votes") or 0) - int(previous_candidate.get("votes") or 0)

    total_delta = sum(delta_votes.values())
    if total_delta <= 0:
        return alerts

    delta_percentages = {
        candidate_id: (delta / total_delta) * 100 for candidate_id, delta in delta_votes.items() if delta > 0
    }
    historical_percentages = _compute_percentages(current_votes)

    threshold = float(config.get("threshold_percent", 10))
    department = extract_department(current_data)

    for candidate_id, delta_pct in delta_percentages.items():
        historical_pct = historical_percentages.get(candidate_id)
        if historical_pct is None:
            continue
        diff = abs(delta_pct - historical_pct)
        if diff <= threshold:
            continue
        alerts.append(
            {
                "type": "Desviación de Tendencia",
                "severity": "High",
                "department": department,
                "justification": (
                    "El porcentaje de votos nuevos difiere de la tendencia histórica. "
                    f"candidato={candidate_id}, delta_pct={delta_pct:.2f}%, "
                    f"historico_pct={historical_pct:.2f}%, diferencia={diff:.2f}%, "
                    f"umbral={threshold:.2f}%, delta_horas={delta_hours:.2f}."
                ),
            }
        )

    return alerts
