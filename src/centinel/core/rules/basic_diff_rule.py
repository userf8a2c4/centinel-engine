"""Regla de consistencia aritmética y cambios básicos entre snapshots.

Rule for arithmetic consistency and basic snapshot changes.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from centinel.core.rules.common import (
    extract_actas_mesas_counts,
    extract_candidate_votes,
    extract_department,
    extract_total_votes,
    extract_vote_breakdown,
)
from centinel.core.rules.registry import rule


def _build_candidate_map(data: dict) -> Dict[str, Dict[str, object]]:
    """Normaliza candidatos a un mapa con votos enteros.

    Convierte el resultado de `extract_candidate_votes` en un diccionario con
    campos homogéneos para comparar entre snapshots.

    English:
        Normalize candidates into a map with integer votes.

        Converts `extract_candidate_votes` output into a homogeneous dictionary
        used for comparing snapshots.
    """
    candidates = extract_candidate_votes(data)
    return {
        key: {
            "id": candidate.get("id"),
            "name": candidate.get("name"),
            "votes": int(candidate.get("votes") or 0),
        }
        for key, candidate in candidates.items()
    }


@rule(
    name="Consistencia Aritmética Básica",
    severity="High",
    description="Valida consistencia aritmética y cambios básicos entre snapshots.",
    config_key="basic_diff",
)
def apply(current_data: dict, previous_data: Optional[dict], config: dict) -> List[dict]:
    """
    Valida consistencia aritmética y cambios básicos entre snapshots.

    Esta regla revisa desajustes entre el total de votos y la suma de candidatos,
    inconsistencias entre votos válidos/nulos/blancos y total, cambios relativos
    extremos en el total de votos, regresiones (votos que disminuyen), y aumentos
    de votos sin incremento de actas procesadas.

    Args:
        current_data: Snapshot JSON actual del CNE.
        previous_data: Snapshot JSON anterior (None en el primer snapshot).
        config: Sección de configuración específica de la regla desde config.yaml.

    Returns:
        Lista de alertas en formato estándar (vacía si todo normal).

    English:
        Validates arithmetic consistency and basic changes between snapshots.

        This rule checks mismatches between total votes and candidate sums,
        inconsistencies between valid/null/blank votes and total, extreme relative
        vote changes, vote regressions, and vote increases without processed tally
        sheets increases.

    Args:
        current_data: Current CNE JSON snapshot.
        previous_data: Previous JSON snapshot (None for the first snapshot).
        config: Rule-specific configuration section from config.yaml.

    Returns:
        List of alerts in the standard format (empty if normal).
    """
    alerts: List[dict] = []
    department = extract_department(current_data)

    breakdown = extract_vote_breakdown(current_data)
    candidate_map = _build_candidate_map(current_data)
    candidate_total = sum(candidate["votes"] for candidate in candidate_map.values())

    total_votes = breakdown.get("total_votes")
    valid_votes = breakdown.get("valid_votes")
    null_votes = breakdown.get("null_votes")
    blank_votes = breakdown.get("blank_votes")

    if total_votes is not None and candidate_total and total_votes != candidate_total:
        alerts.append(
            {
                "type": "Descuadre Aritmético de Votos",
                "severity": "High",
                "department": department,
                "justification": (
                    "El total de votos no coincide con la suma de candidatos. "
                    f"total_reportado={total_votes}, suma_candidatos={candidate_total}."
                ),
            }
        )

    components = [value for value in (valid_votes, null_votes, blank_votes) if value is not None]
    if total_votes is not None and components:
        sum_components = sum(components)
        if total_votes != sum_components:
            alerts.append(
                {
                    "type": "Inconsistencia en Desglose de Votos",
                    "severity": "High",
                    "department": department,
                    "justification": (
                        "El total reportado no coincide con válidos+nulos+blancos. "
                        f"total_reportado={total_votes}, suma_componentes={sum_components}, "
                        f"validos={valid_votes}, nulos={null_votes}, blancos={blank_votes}."
                    ),
                }
            )

    if previous_data:
        previous_candidates = _build_candidate_map(previous_data)
        for key, current_candidate in candidate_map.items():
            prev_votes = previous_candidates.get(key, {}).get("votes", 0)
            delta_votes = current_candidate["votes"] - int(prev_votes)
            if delta_votes < 0:
                alerts.append(
                    {
                        "type": "Disminución de Votos",
                        "severity": "High",
                        "department": department,
                        "justification": (
                            "Se detectó una reducción de votos entre snapshots. "
                            f"candidato={current_candidate.get('name') or key}, "
                            f"anterior={prev_votes}, actual={current_candidate['votes']}, "
                            f"delta={delta_votes}."
                        ),
                    }
                )

        previous_total = extract_total_votes(previous_data) or 0
        if previous_total > 0 and total_votes is not None:
            relative_change_pct = ((total_votes - previous_total) / previous_total) * 100
            threshold = float(config.get("relative_vote_change_pct", 15))
            if abs(relative_change_pct) >= threshold:
                alerts.append(
                    {
                        "type": "Cambio Relativo de Votos",
                        "severity": "Medium",
                        "department": department,
                        "justification": (
                            "El cambio relativo de votos excede el umbral. "
                            f"delta_pct={relative_change_pct:.2f}%, umbral={threshold:.2f}%, "
                            f"total_anterior={previous_total}, total_actual={total_votes}."
                        ),
                    }
                )

        actas_current = extract_actas_mesas_counts(current_data).get("actas_procesadas")
        actas_previous = extract_actas_mesas_counts(previous_data).get("actas_procesadas")
        if actas_current is not None and actas_previous is not None:
            delta_votes = (total_votes or 0) - (previous_total or 0)
            delta_actas = actas_current - actas_previous
            if delta_votes > 0 and delta_actas <= 0:
                alerts.append(
                    {
                        "type": "Votos Sin Incremento de Actas",
                        "severity": "High",
                        "department": department,
                        "justification": (
                            "Aumentaron votos sin incremento de actas procesadas. "
                            f"delta_votos={delta_votes}, delta_actas={delta_actas}, "
                            f"actas_previas={actas_previous}, actas_actuales={actas_current}."
                        ),
                    }
                )

    return alerts
