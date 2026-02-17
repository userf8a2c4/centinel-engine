"""Pruebas adicionales de resumen de diffs.

Additional diff summary tests.
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
