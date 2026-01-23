"""Regla de Ley de Grandes Números para proporciones de votos por mesa.

Law of Large Numbers rule for per-table vote proportions.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional

from sentinel.core.rules.common import extract_department, safe_int_or_none
from sentinel.core.rules.registry import rule


def _extract_mesa_votes(mesa: dict) -> Dict[str, int]:
    """Extrae votos por candidato desde una mesa.

    Args:
        mesa: Diccionario con la información de la mesa.

    Returns:
        Diccionario con votos por candidato.

    English:
        Extracts per-candidate votes from a single table entry.

    Args:
        mesa: Dictionary with table information.

    Returns:
        Dictionary with votes per candidate.
    """
    votes_by_candidate: Dict[str, int] = {}
    entries = mesa.get("votos") or mesa.get("candidates") or mesa.get("candidatos") or []
    if not isinstance(entries, list):
        return votes_by_candidate

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        candidate_id = (
            entry.get("id")
            or entry.get("candidate_id")
            or entry.get("nombre")
            or entry.get("name")
            or entry.get("candidato")
            or "unknown"
        )
        votes = safe_int_or_none(entry.get("votos") or entry.get("votes"))
        if votes is None or votes < 0:
            continue
        votes_by_candidate[str(candidate_id)] = votes

    return votes_by_candidate


def _aggregate_mesas(mesas: List[dict]) -> tuple[Dict[str, int], List[Dict[str, float]]]:
    """Agrega votos totales y proporciones por mesa.

    Args:
        mesas: Lista de mesas con votos por candidato.

    Returns:
        Tupla con (votos totales por candidato, lista de proporciones por mesa).

    English:
        Aggregates total votes and per-table proportions.

    Args:
        mesas: List of tables with candidate votes.

    Returns:
        Tuple with (total votes per candidate, list of per-table proportions).
    """
    totals: Dict[str, int] = {}
    proportions: List[Dict[str, float]] = []

    for mesa in mesas:
        if not isinstance(mesa, dict):
            continue
        mesa_votes = _extract_mesa_votes(mesa)
        if not mesa_votes:
            continue
        mesa_total = sum(mesa_votes.values())
        if mesa_total <= 0:
            continue
        for candidate_id, votes in mesa_votes.items():
            totals[candidate_id] = totals.get(candidate_id, 0) + votes
        proportions.append(
            {candidate_id: votes / mesa_total for candidate_id, votes in mesa_votes.items()}
        )

    return totals, proportions


@rule(
    name="Convergencia Ley de Grandes Números",
    severity="Medium",
    description="Evalúa la convergencia de proporciones por mesa hacia el promedio global.",
    config_key="large_numbers_convergence",
)
def apply(
    current_data: dict, previous_data: Optional[dict], config: dict
) -> List[dict]:
    """
    Verifica convergencia de proporciones por mesa usando la Ley de Grandes Números.

    La regla calcula la proporción de votos por candidato en cada mesa y compara la
    media muestral con la proporción global. Si la diferencia excede un umbral de
    desviación estándar para un tamaño de muestra suficiente, se reporta una alerta.

    Args:
        current_data: Snapshot JSON actual de la autoridad electoral.
        previous_data: Snapshot JSON anterior (None en el primer snapshot).
        config: Configuración específica de la regla.

    Returns:
        Lista de alertas en formato estándar.

    English:
        Checks convergence of per-table proportions using the Law of Large Numbers.

        The rule computes candidate vote shares per table and compares the sample
        mean to the global share. If the gap exceeds a standard error threshold
        given a sufficient sample size, it raises an alert.

    Args:
        current_data: Current electoral authority JSON snapshot.
        previous_data: Previous JSON snapshot (None for the first snapshot).
        config: Rule-specific configuration section.

    Returns:
        List of alerts in the standard format.
    """
    del previous_data

    alerts: List[dict] = []
    mesas = current_data.get("mesas") or current_data.get("tables") or []
    if not isinstance(mesas, list) or not mesas:
        return alerts

    totals, proportions = _aggregate_mesas(mesas)
    if not totals or not proportions:
        return alerts

    min_samples = int(config.get("min_samples", 30))
    z_threshold = float(config.get("z_threshold", 3.0))
    min_total_votes = int(config.get("min_total_votes", 200))

    total_votes_all = sum(totals.values())
    if total_votes_all < min_total_votes:
        return alerts

    department = extract_department(current_data)

    for candidate_id, total_votes in totals.items():
        sample_values = [
            mesa_props.get(candidate_id)
            for mesa_props in proportions
            if candidate_id in mesa_props
        ]
        if len(sample_values) < min_samples:
            continue
        sample_mean = sum(sample_values) / len(sample_values)
        global_share = total_votes / total_votes_all
        variance = global_share * (1 - global_share)
        if variance <= 0:
            continue
        standard_error = math.sqrt(variance / len(sample_values))
        if standard_error == 0:
            continue
        z_score = abs(sample_mean - global_share) / standard_error
        if z_score <= z_threshold:
            continue

        alerts.append(
            {
                "type": "Desviación Ley de Grandes Números",
                "severity": "Medium",
                "department": department,
                "justification": (
                    "La media de proporciones por mesa no converge al promedio global. "
                    f"Candidato={candidate_id}, muestras={len(sample_values)}, "
                    f"media={sample_mean:.4f}, global={global_share:.4f}, "
                    f"error_std={standard_error:.4f}, z={z_score:.2f}, "
                    f"umbral_z={z_threshold:.2f}."
                ),
            }
        )

    return alerts
