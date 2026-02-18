"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `tests/test_turnout_impossible_rule.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - test_turnout_impossible_flags_over_100
  - test_turnout_impossible_allows_normal_range

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `tests/test_turnout_impossible_rule.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - test_turnout_impossible_flags_over_100
  - test_turnout_impossible_allows_normal_range

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
"""

from __future__ import annotations

from centinel.core.rules.turnout_impossible_rule import apply


def test_turnout_impossible_flags_over_100():
    """Español: Función test_turnout_impossible_flags_over_100 del módulo tests/test_turnout_impossible_rule.py.

    English: Function test_turnout_impossible_flags_over_100 defined in tests/test_turnout_impossible_rule.py.
    """
    data = {
        "totals": {"registered_voters": 1000, "total_votes": 1200},
        "meta": {"department": "Demo"},
    }
    alerts = apply(data, None, {"min_turnout_pct": 0, "max_turnout_pct": 100})
    assert alerts
    assert alerts[0]["type"] == "Turnout Imposible"


def test_turnout_impossible_allows_normal_range():
    """Español: Función test_turnout_impossible_allows_normal_range del módulo tests/test_turnout_impossible_rule.py.

    English: Function test_turnout_impossible_allows_normal_range defined in tests/test_turnout_impossible_rule.py.
    """
    data = {
        "totals": {"registered_voters": 1000, "total_votes": 800},
        "meta": {"department": "Demo"},
    }
    alerts = apply(data, None, {"min_turnout_pct": 0, "max_turnout_pct": 100})
    assert alerts == []
