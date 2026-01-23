"""Regla de correlación participación-voto.

Participation-vote correlation rule.
"""

from __future__ import annotations

from typing import List, Optional

import numpy as np
import pandas as pd
from scipy.stats import pearsonr

from sentinel.core.rules.common import (
    extract_mesa_candidate_votes,
    extract_mesa_vote_breakdown,
    extract_mesas,
)
from sentinel.core.rules.registry import rule


@rule(
    name="Correlación Participación-Voto",
    severity="CRITICAL",
    description="Calcula correlación Pearson entre participación y voto líder.",
    config_key="participation_vote_correlation",
)
def apply(
    current_data: dict, previous_data: Optional[dict], config: dict
) -> List[dict]:
    """
    Evalúa correlación espuria entre participación y voto principal.

    Para cada mesa, calcula participación y porcentaje del candidato líder.
    Si |r| excede el umbral configurado, se genera alerta CRITICAL.

    Args:
        current_data: Snapshot JSON actual de la autoridad electoral.
        previous_data: Snapshot JSON anterior (None en el primer snapshot).
        config: Configuración específica de la regla.

    Returns:
        Lista de alertas en formato estándar.

    English:
        Evaluates spurious correlation between turnout and leading vote share.

        For each table, computes turnout and leading candidate share.
        If |r| exceeds the configured threshold, a CRITICAL alert is generated.

    Args:
        current_data: Current electoral authority JSON snapshot.
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

    rows = []
    for mesa in mesas:
        breakdown = extract_mesa_vote_breakdown(mesa)
        total_votes = breakdown.get("total_votes")
        registered = breakdown.get("registered_voters")
        if not total_votes or not registered:
            continue
        candidate_votes = extract_mesa_candidate_votes(mesa)
        if not candidate_votes:
            continue
        valid_votes = breakdown.get("valid_votes") or sum(candidate_votes.values())
        if not valid_votes:
            continue
        leading_votes = max(candidate_votes.values())
        rows.append(
            {
                "turnout": total_votes / registered,
                "leading_share": leading_votes / valid_votes,
            }
        )

    if not rows:
        return alerts

    df = pd.DataFrame(rows)
    min_samples = int(config.get("min_samples", 30))
    if len(df) < min_samples:
        return alerts

    r_value, p_value = pearsonr(df["turnout"], df["leading_share"])
    threshold = float(config.get("critical_r", 0.85))
    if abs(r_value) <= threshold:
        return alerts

    message = "Correlación alta entre participación y voto principal."
    alerts.append(
        {
            "type": "Correlación Participación-Voto",
            "severity": "CRITICAL",
            "message": message,
            "value": {"r": float(r_value), "p_value": float(p_value)},
            "threshold": {"critical_r": threshold},
            "result": (
                "CRITICAL",
                message,
                {"r": float(r_value), "p_value": float(p_value)},
                {"critical_r": threshold},
            ),
            "justification": (
                "Se detectó correlación espuria entre participación y voto líder. "
                f"r={r_value:.3f}, p={p_value:.4f}, muestras={len(df)}."
            ),
        }
    )

    return alerts
