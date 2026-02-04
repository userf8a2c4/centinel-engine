"""Pruebas del orquestador de reglas de análisis.

Tests for the analysis rules orchestrator.
"""

from __future__ import annotations

from typing import List, Optional

import scripts.analyze_rules as analyze_rules


def _make_rule(tag: str, bucket: List[str]):
    """Español: Función _make_rule del módulo tests/test_rules_orchestrator.py.

    English: Function _make_rule defined in tests/test_rules_orchestrator.py.
    """

    def _rule(current: dict, previous: Optional[dict], config: dict) -> List[dict]:
        """Español: Función _rule del módulo tests/test_rules_orchestrator.py.

        English: Function _rule defined in tests/test_rules_orchestrator.py.
        """
        bucket.append(tag)
        return [
            {
                "type": f"Regla {tag}",
                "severity": "Low",
                "justification": "ok",
            }
        ]

    return _rule


def test_run_all_rules_respects_global_enabled(monkeypatch):
    """Español: Función test_run_all_rules_respects_global_enabled del módulo tests/test_rules_orchestrator.py.

    English: Function test_run_all_rules_respects_global_enabled defined in tests/test_rules_orchestrator.py.
    """
    called: List[str] = []
    monkeypatch.setattr(
        analyze_rules,
        "RULES",
        [("dummy", _make_rule("dummy", called))],
    )

    alerts = analyze_rules.run_all_rules({}, None, {"rules": {"global_enabled": False}})

    assert alerts == []
    assert called == []


def test_run_all_rules_filters_enabled_rules(monkeypatch):
    """Español: Función test_run_all_rules_filters_enabled_rules del módulo tests/test_rules_orchestrator.py.

    English: Function test_run_all_rules_filters_enabled_rules defined in tests/test_rules_orchestrator.py.
    """
    called: List[str] = []
    rules = [
        ("alpha", _make_rule("alpha", called)),
        ("beta", _make_rule("beta", called)),
    ]
    monkeypatch.setattr(analyze_rules, "RULES", rules)

    alerts = analyze_rules.run_all_rules(
        {"foo": "bar"},
        None,
        {
            "rules": {
                "global_enabled": True,
                "alpha": {"enabled": True},
                "beta": {"enabled": False},
            }
        },
    )

    assert called == ["alpha"]
    assert len(alerts) == 1
    assert alerts[0]["type"] == "Regla alpha"
