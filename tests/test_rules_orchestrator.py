"""Tests para las reglas individuales del motor de detección.

English:
    Tests for individual detection engine rules.
"""

from __future__ import annotations

from typing import List

from sentinel.core.rules.basic_diff_rule import apply as basic_diff_apply


def test_basic_diff_detects_arithmetic_mismatch():
    """Detecta descuadre cuando la suma de candidatos ≠ total reportado."""
    snapshot = {
        "totals": {"total_votes": 1000, "valid_votes": 900, "null_votes": 50, "blank_votes": 50},
        "candidates": [
            {"name": "A", "votes": 600},
            {"name": "B", "votes": 300},
        ],
    }
    alerts = basic_diff_apply(snapshot, None, {})
    types = [a["type"] for a in alerts]
    assert "Descuadre Aritmético de Votos" in types


def test_basic_diff_no_alerts_when_consistent():
    """Sin alertas cuando todo cuadra."""
    snapshot = {
        "totals": {"total_votes": 1000, "valid_votes": 900, "null_votes": 50, "blank_votes": 50},
        "candidates": [
            {"name": "A", "votes": 600},
            {"name": "B", "votes": 400},
        ],
    }
    alerts = basic_diff_apply(snapshot, None, {})
    types = [a["type"] for a in alerts]
    assert "Descuadre Aritmético de Votos" not in types
