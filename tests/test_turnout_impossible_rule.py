"""Pruebas para la regla de turnout imposible."""

from __future__ import annotations

from sentinel.core.rules.turnout_impossible_rule import apply


def test_turnout_impossible_flags_over_100():
    data = {
        "totals": {"registered_voters": 1000, "total_votes": 1200},
        "meta": {"department": "Demo"},
    }
    alerts = apply(data, None, {"min_turnout_pct": 0, "max_turnout_pct": 100})
    assert alerts
    assert alerts[0]["type"] == "Turnout Imposible"


def test_turnout_impossible_allows_normal_range():
    data = {
        "totals": {"registered_voters": 1000, "total_votes": 800},
        "meta": {"department": "Demo"},
    }
    alerts = apply(data, None, {"min_turnout_pct": 0, "max_turnout_pct": 100})
    assert alerts == []
