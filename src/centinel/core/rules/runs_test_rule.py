# Runs Test Rule Module
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

"""Regla de rachas (runs test) sobre mesas.

Runs test rule over polling tables.
"""

from __future__ import annotations

from typing import List, Optional

import numpy as np
from scipy.stats import norm

from centinel.core.rules.common import (
    extract_mesa_candidate_votes,
    extract_mesa_code,
    extract_mesa_vote_breakdown,
    extract_mesas,
)
from centinel.core.rules.registry import rule


def _runs_test(sequence: List[int]) -> float:
    """Calcula el p-value del runs test para una secuencia binaria.

    Evalúa la aleatoriedad de rachas 0/1 y retorna p-value bilateral.

    English:
        Compute the runs test p-value for a binary sequence.

        Evaluates randomness of 0/1 runs and returns a two-sided p-value.
    """
    if not sequence:
        return 1.0
    runs = 1
    for idx in range(1, len(sequence)):
        if sequence[idx] != sequence[idx - 1]:
            runs += 1
    n1 = sequence.count(1)
    n2 = sequence.count(0)
    if n1 == 0 or n2 == 0:
        return 1.0
    mean_runs = (2 * n1 * n2) / (n1 + n2) + 1
    numerator = 2 * n1 * n2 * (2 * n1 * n2 - n1 - n2)
    denominator = ((n1 + n2) ** 2) * (n1 + n2 - 1)
    if denominator == 0:
        return 1.0
    std_runs = np.sqrt(numerator / denominator)
    if std_runs == 0:
        return 1.0
    z_score = (runs - mean_runs) / std_runs
    return float(2 * (1 - norm.cdf(abs(z_score))))


@rule(
    name="Runs Test",
    severity="CRITICAL",
    description="Aplica runs test sobre secuencia ordenada de mesas.",
    config_key="runs_test",
)
def apply(current_data: dict, previous_data: Optional[dict], config: dict) -> List[dict]:
    """
    Aplica el runs test sobre mesas ordenadas por código.

    Se calcula el porcentaje del candidato líder en cada mesa, se binariza
    respecto a la mediana y se evalúa la aleatoriedad de rachas.
    p-value < 0.01 genera alerta CRITICAL.

    Args:
        current_data: Snapshot JSON actual del CNE.
        previous_data: Snapshot JSON anterior (None en el primer snapshot).
        config: Configuración específica de la regla.

    Returns:
        Lista de alertas en formato estándar.

    English:
        Applies runs test over tables ordered by code.

        Computes leading candidate share per table, binarizes by median,
        and evaluates run randomness. p-value < 0.01 triggers CRITICAL.

    Args:
        current_data: Current CNE JSON snapshot.
        previous_data: Previous JSON snapshot (None for the first snapshot).
        config: Rule-specific configuration section.

    Returns:
        List of alerts in the standard format.
    """
    del previous_data

    alerts: List[dict] = []
    mesas = extract_mesas(current_data)
    if not mesas:
        return alerts

    mesas_sorted = sorted(
        mesas,
        key=lambda mesa: extract_mesa_code(mesa) or "",
    )

    shares = []
    for mesa in mesas_sorted:
        breakdown = extract_mesa_vote_breakdown(mesa)
        candidate_votes = extract_mesa_candidate_votes(mesa)
        if not candidate_votes:
            continue
        valid_votes = breakdown.get("valid_votes") or sum(candidate_votes.values())
        if not valid_votes:
            continue
        leading_share = max(candidate_votes.values()) / valid_votes
        shares.append(leading_share)

    min_samples = int(config.get("min_samples", 30))
    if len(shares) < min_samples:
        return alerts

    median_share = float(np.median(shares))
    sequence = [1 if share >= median_share else 0 for share in shares]
    p_value = _runs_test(sequence)
    critical_pvalue = float(config.get("critical_pvalue", 0.01))
    if p_value >= critical_pvalue:
        return alerts

    message = "Runs test indica rachas no aleatorias en mesas ordenadas."
    alerts.append(
        {
            "type": "Runs Test",
            "severity": "CRITICAL",
            "message": message,
            "value": {"p_value": p_value},
            "threshold": {"critical_pvalue": critical_pvalue},
            "result": (
                "CRITICAL",
                message,
                {"p_value": p_value},
                {"critical_pvalue": critical_pvalue},
            ),
            "justification": (
                "El runs test sobre mesas ordenadas detectó rachas anómalas. "
                f"pvalue={p_value:.4f}, muestras={len(shares)}."
            ),
        }
    )

    return alerts
