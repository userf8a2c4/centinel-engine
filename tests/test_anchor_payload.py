"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `tests/test_anchor_payload.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - test_build_diff_summary_detects_changes
  - test_compute_anchor_root_changes_with_rules

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `tests/test_anchor_payload.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - test_build_diff_summary_detects_changes
  - test_compute_anchor_root_changes_with_rules

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
"""

from centinel.core import anchoring_payload


def test_build_diff_summary_detects_changes():
    """Español: Función test_build_diff_summary_detects_changes del módulo tests/test_anchor_payload.py.

    English: Function test_build_diff_summary_detects_changes defined in tests/test_anchor_payload.py.
    """
    previous = {"a": 1, "b": {"nested": 2}, "c": [1, 2]}
    current = {"a": 2, "b": {"nested": 3}, "c": [1, 2, 3]}

    summary = anchoring_payload.build_diff_summary(previous, current)

    assert summary["change_count"] == 3
    paths = {change["path"] for change in summary["changes"]}
    assert paths == {"$.a", "$.b", "$.c"}


def test_compute_anchor_root_changes_with_rules():
    """Español: Función test_compute_anchor_root_changes_with_rules del módulo tests/test_anchor_payload.py.

    English: Function test_compute_anchor_root_changes_with_rules defined in tests/test_anchor_payload.py.
    """
    snapshot_payload = {"mesa": 1, "resultados": {"a": 100}}
    diff_summary = anchoring_payload.build_diff_summary(None, snapshot_payload)
    rules_payload = {"alerts": [{"type": "BENFORD"}], "critical_alerts": []}
    baseline = anchoring_payload.compute_anchor_root(snapshot_payload, diff_summary, rules_payload)

    altered_rules = {"alerts": [], "critical_alerts": ["CRITICAL"]}
    updated = anchoring_payload.compute_anchor_root(snapshot_payload, diff_summary, altered_rules)

    assert baseline["root_hash"] != updated["root_hash"]
