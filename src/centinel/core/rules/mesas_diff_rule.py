"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `src/centinel/core/rules/mesas_diff_rule.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - apply

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `src/centinel/core/rules/mesas_diff_rule.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - apply

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
"""

# Mesas Diff Rule Module
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

from centinel.core.rules.common import extract_mesa_code, extract_mesas
from centinel.core.rules.registry import rule


@rule(
    name="Mesas Duplicadas o Desaparecidas",
    severity="CRITICAL",
    description="Compara sets de mesas entre snapshots.",
    config_key="mesas_diff",
)
def apply(current_data: dict, previous_data: Optional[dict], config: dict) -> List[dict]:
    """
    Compara mesas presentes entre snapshots consecutivos.

    Si aparecen mesas nuevas o desaparecen sin explicación, se genera
    alerta CRITICAL.

    Args:
        current_data: Snapshot JSON actual del CNE.
        previous_data: Snapshot JSON anterior (None en el primer snapshot).
        config: Configuración específica de la regla.

    Returns:
        Lista de alertas en formato estándar.

    English:
        Compares polling tables between consecutive snapshots.

        If new tables appear or existing ones disappear without explanation,
        a CRITICAL alert is generated.

    Args:
        current_data: Current CNE JSON snapshot.
        previous_data: Previous JSON snapshot (None for the first snapshot).
        config: Rule-specific configuration section.

    Returns:
        List of alerts in the standard format.
    """
    del config

    alerts: List[dict] = []
    if not previous_data:
        return alerts

    current_codes = {code for code in (extract_mesa_code(m) for m in extract_mesas(current_data)) if code}
    previous_codes = {code for code in (extract_mesa_code(m) for m in extract_mesas(previous_data)) if code}
    if not current_codes or not previous_codes:
        return alerts

    missing = sorted(previous_codes - current_codes)
    added = sorted(current_codes - previous_codes)

    if not missing and not added:
        return alerts

    message = "Mesas desaparecidas o nuevas entre snapshots."
    alerts.append(
        {
            "type": "Mesas Discrepantes",
            "severity": "CRITICAL",
            "message": message,
            "value": {
                "missing": missing[:10],
                "added": added[:10],
                "missing_count": len(missing),
                "added_count": len(added),
            },
            "threshold": {"missing": 0, "added": 0},
            "result": (
                "CRITICAL",
                message,
                {"missing_count": len(missing), "added_count": len(added)},
                {"missing": 0, "added": 0},
            ),
            "justification": (
                "Se detectaron cambios en el set de mesas entre snapshots. "
                f"desaparecidas={len(missing)}, nuevas={len(added)}."
            ),
        }
    )

    return alerts
