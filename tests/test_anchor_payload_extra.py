"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `tests/test_anchor_payload_extra.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - test_build_diff_summary_previous_none_returns_no_changes

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `tests/test_anchor_payload_extra.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - test_build_diff_summary_previous_none_returns_no_changes

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
"""

from centinel.core.anchoring_payload import build_diff_summary


def test_build_diff_summary_previous_none_returns_no_changes() -> None:
    """Español: Sin snapshot previo, no hay cambios.

    English: Without a previous snapshot, no changes should be reported.
    """
    current = {"a": 1}

    summary = build_diff_summary(None, current)

    assert summary["change_count"] == 0
    assert summary["changes"] == []
