# Geographic Dispersion Rule Module
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

"""Regla de dispersión geográfica (coeficiente de variación).

Geographic dispersion rule (coefficient of variation).
"""

from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np

from centinel.core.rules.common import (
    extract_candidate_votes,
    extract_department_entries,
)
from centinel.core.rules.registry import rule


def _extract_department_candidate_shares(entry: dict) -> Dict[str, float]:
    """Calcula el porcentaje de votos por candidato en un departamento.

    Normaliza los votos del departamento y devuelve proporciones entre 0 y 1.

    English:
        Compute candidate vote shares for a department.

        Normalizes department votes and returns proportions between 0 and 1.
    """
    candidates = extract_candidate_votes(entry)
    total_votes = sum(candidate.get("votes") or 0 for candidate in candidates.values())
    if total_votes <= 0:
        return {}
    return {
        candidate.get("name") or candidate_id: (candidate.get("votes") or 0) / total_votes
        for candidate_id, candidate in candidates.items()
    }


@rule(
    name="Dispersión Geográfica",
    severity="CRITICAL",
    description="Calcula CV de % voto por partido entre departamentos.",
    config_key="geographic_dispersion",
)
def apply(current_data: dict, previous_data: Optional[dict], config: dict) -> List[dict]:
    """
    Calcula el coeficiente de variación de porcentajes por departamento.

    Para cada partido/candidato, calcula el CV de su porcentaje entre
    departamentos. Si el CV supera el umbral, se genera alerta CRITICAL.

    Args:
        current_data: Snapshot JSON actual del CNE.
        previous_data: Snapshot JSON anterior (None en el primer snapshot).
        config: Configuración específica de la regla.

    Returns:
        Lista de alertas en formato estándar.

    English:
        Computes coefficient of variation for vote shares by department.

        For each party/candidate, computes CV of vote share across departments.
        If CV exceeds threshold, a CRITICAL alert is generated.

    Args:
        current_data: Current CNE JSON snapshot.
        previous_data: Previous JSON snapshot (None for the first snapshot).
        config: Rule-specific configuration section.

    Returns:
        List of alerts in the standard format.
    """
    del previous_data

    alerts: List[dict] = []
    departments = extract_department_entries(current_data)
    if not departments:
        return alerts

    by_candidate: Dict[str, List[float]] = {}
    for entry in departments:
        shares = _extract_department_candidate_shares(entry)
        for candidate, share in shares.items():
            by_candidate.setdefault(candidate, []).append(share)

    threshold = float(config.get("critical_cv", 0.45))
    min_departments = int(config.get("min_departments", 5))
    triggered = []

    for candidate, shares in by_candidate.items():
        if len(shares) < min_departments:
            continue
        mean_share = float(np.mean(shares))
        if mean_share == 0:
            continue
        cv = float(np.std(shares, ddof=1) / mean_share)
        if cv > threshold:
            triggered.append((candidate, cv))

    if not triggered:
        return alerts

    message = "Alta dispersión geográfica del voto por partido."
    alerts.append(
        {
            "type": "Dispersión Geográfica",
            "severity": "CRITICAL",
            "message": message,
            "value": {"candidates": [{"name": name, "cv": cv} for name, cv in triggered]},
            "threshold": {"critical_cv": threshold},
            "result": (
                "CRITICAL",
                message,
                {"candidates": [{"name": name, "cv": cv} for name, cv in triggered]},
                {"critical_cv": threshold},
            ),
            "justification": (
                "El coeficiente de variación supera el umbral en departamentos. "
                f"candidatos={len(triggered)}, cv_umbral={threshold:.2f}."
            ),
        }
    )

    return alerts
