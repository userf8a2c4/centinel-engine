"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `src/centinel/core/rules/table_consistency_rule.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - apply

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `src/centinel/core/rules/table_consistency_rule.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - apply

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
"""

# Table Consistency Rule Module
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

from typing import List, Optional

from centinel.core.rules.common import (
    extract_department,
    extract_mesa_candidate_votes,
    extract_mesa_code,
    extract_mesa_vote_breakdown,
    extract_mesas,
)
from centinel.core.rules.registry import rule


@rule(
    name="Consistencia por Mesa",
    severity="CRITICAL",
    description="Valida válidos+nulos+blancos vs total y suma candidatos vs válidos.",
    config_key="table_consistency",
)
def apply(current_data: dict, previous_data: Optional[dict], config: dict) -> List[dict]:
    """
    Verifica consistencia aritmética por mesa en votos válidos y total emitido.

    La regla revisa que válidos+nulos+blancos coincida con el total emitido
    (tolerancia ±1) y que la suma de candidatos sea igual a votos válidos.
    Cualquier falla genera alerta CRITICAL.

    Args:
        current_data: Snapshot JSON actual del CNE.
        previous_data: Snapshot JSON anterior (None en el primer snapshot).
        config: Configuración específica de la regla.

    Returns:
        Lista de alertas en formato estándar.

    English:
        Checks arithmetic consistency per table for valid and total votes.

        The rule validates that valid+null+blank equals total emitted (±1)
        and that candidate sums match valid votes. Any failure generates
        a CRITICAL alert.

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

    tolerance = int(config.get("total_tolerance", 1))
    department = extract_department(current_data)

    total_mismatch = []
    valid_mismatch = []

    for mesa in mesas:
        breakdown = extract_mesa_vote_breakdown(mesa)
        valid_votes = breakdown.get("valid_votes")
        null_votes = breakdown.get("null_votes")
        blank_votes = breakdown.get("blank_votes")
        total_votes = breakdown.get("total_votes")
        candidate_votes = extract_mesa_candidate_votes(mesa)
        mesa_code = extract_mesa_code(mesa) or "SIN_CODIGO"

        components = [value for value in (valid_votes, null_votes, blank_votes) if value is not None]
        if total_votes is not None and components:
            if abs(total_votes - sum(components)) > tolerance:
                total_mismatch.append(mesa_code)

        if valid_votes is not None and candidate_votes:
            if sum(candidate_votes.values()) != valid_votes:
                valid_mismatch.append(mesa_code)

    if not total_mismatch and not valid_mismatch:
        return alerts

    message = "Inconsistencias aritméticas detectadas en mesas."
    alerts.append(
        {
            "type": "Inconsistencia por Mesa",
            "severity": "CRITICAL",
            "department": department,
            "message": message,
            "value": {
                "total_mismatch": len(total_mismatch),
                "valid_mismatch": len(valid_mismatch),
                "samples_total": total_mismatch[:5],
                "samples_valid": valid_mismatch[:5],
            },
            "threshold": {
                "total_tolerance": tolerance,
                "valid_tolerance": 0,
            },
            "result": (
                "CRITICAL",
                message,
                {
                    "total_mismatch": len(total_mismatch),
                    "valid_mismatch": len(valid_mismatch),
                },
                {"total_tolerance": tolerance, "valid_tolerance": 0},
            ),
            "justification": (
                "Se encontraron mesas con descuadre de votos. "
                f"descuadres_total={len(total_mismatch)}, "
                f"descuadres_validos={len(valid_mismatch)}, "
                f"tolerancia_total=±{tolerance}."
            ),
        }
    )

    return alerts
