"""Pruebas del motor unificado de reglas.

Tests for the unified rules engine.
"""

from __future__ import annotations

from typing import List, Optional

from centinel.core.rules.registry import RuleDefinition, _RULE_REGISTRY
from centinel.core.rules_engine import RulesEngine


def _make_rule_def(tag: str, bucket: List[str]) -> RuleDefinition:
    """Crea un RuleDefinition de prueba que registra su ejecución en *bucket*.

    English:
        Create a test RuleDefinition that logs its execution into *bucket*.
    """

    def _rule(current: dict, previous: Optional[dict], config: dict) -> List[dict]:
        bucket.append(tag)
        return [
            {
                "type": f"Regla {tag}",
                "severity": "Low",
                "justification": "ok",
            }
        ]

    return RuleDefinition(
        name=tag,
        severity="Low",
        description=f"Test rule {tag}",
        config_key=tag,
        func=_rule,
    )


def test_engine_respects_global_enabled(monkeypatch):
    """Cuando global_enabled=false, ninguna regla debe ejecutarse.

    English:
        When global_enabled=false, no rule should execute.
    """
    called: List[str] = []
    monkeypatch.setattr(
        "centinel.core.rules_engine.list_rules",
        lambda: [_make_rule_def("dummy", called)],
    )

    engine = RulesEngine(config={"rules": {"global_enabled": False}})
    result = engine.run({}, None)

    assert result.alerts == []
    assert called == []


def test_engine_filters_enabled_rules(monkeypatch):
    """Solo las reglas habilitadas deben ejecutarse.

    English:
        Only enabled rules should execute.
    """
    called: List[str] = []
    monkeypatch.setattr(
        "centinel.core.rules_engine.list_rules",
        lambda: [
            _make_rule_def("alpha", called),
            _make_rule_def("beta", called),
        ],
    )

    engine = RulesEngine(
        config={
            "rules": {
                "global_enabled": True,
                "alpha": {"enabled": True},
                "beta": {"enabled": False},
            }
        }
    )
    result = engine.run({"foo": "bar"}, None)

    assert called == ["alpha"]
    assert len(result.alerts) == 1
    assert result.alerts[0]["type"] == "Regla alpha"


def test_all_rules_enabled_by_default(monkeypatch):
    """Las reglas sin configuración explícita deben estar habilitadas.

    English:
        Rules without explicit config should be enabled by default.
    """
    called: List[str] = []
    monkeypatch.setattr(
        "centinel.core.rules_engine.list_rules",
        lambda: [
            _make_rule_def("no_config_rule", called),
        ],
    )

    engine = RulesEngine(config={"rules": {"global_enabled": True}})
    result = engine.run({}, None)

    assert called == ["no_config_rule"]
    assert len(result.alerts) == 1


def test_all_legacy_rules_registered():
    """Verifica que las 20 reglas (13 originales + 7 legacy) estén registradas.

    English:
        Verify that all 20 rules (13 original + 7 legacy) are registered.
    """
    from centinel.core import rules_engine  # noqa: F401 — triggers imports

    registered_keys = {r.config_key for r in _RULE_REGISTRY}

    expected_legacy = {
        "basic_diff",
        "benford_law",
        "irreversibility",
        "ml_outliers",
        "participation_anomaly",
        "processing_speed",
        "trend_shift",
    }
    for key in expected_legacy:
        assert key in registered_keys, f"Legacy rule {key!r} not registered"

    expected_original = {
        "benford_first_digit",
        "participation_vote_correlation",
        "geographic_dispersion",
        "granular_anomaly",
        "large_numbers_convergence",
        "last_digit_uniformity",
        "mesas_diff",
        "null_blank_votes",
        "participation_anomaly_advanced",
        "runs_test",
        "snapshot_jump",
        "table_consistency",
        "turnout_impossible",
    }
    for key in expected_original:
        assert key in registered_keys, f"Original rule {key!r} not registered"
