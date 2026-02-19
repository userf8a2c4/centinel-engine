"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `tests/test_rules_orchestrator.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - _make_rule_def
  - test_engine_respects_global_enabled
  - test_engine_filters_enabled_rules
  - test_all_rules_enabled_by_default
  - test_all_legacy_rules_registered

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `tests/test_rules_orchestrator.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - _make_rule_def
  - test_engine_respects_global_enabled
  - test_engine_filters_enabled_rules
  - test_all_rules_enabled_by_default
  - test_all_legacy_rules_registered

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
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
            _make_rule_def("turnout_impossible", called),
        ],
    )

    engine = RulesEngine(config={"rules": {"global_enabled": True}})
    result = engine.run({}, None)

    assert called == ["turnout_impossible"]
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



def test_research_rules_disabled_by_default(monkeypatch):
    """Las reglas research deben quedar behind-flag por defecto.

    English:
        Research rules should be behind a flag by default.
    """
    called: List[str] = []
    monkeypatch.setattr(
        "centinel.core.rules_engine.list_rules",
        lambda: [
            _make_rule_def("basic_diff", called),
            _make_rule_def("turnout_impossible", called),
        ],
    )

    engine = RulesEngine(config={"rules": {"global_enabled": True}})
    result = engine.run({}, None)

    assert called == ["turnout_impossible"]
    assert len(result.alerts) == 1


def test_research_rules_enabled_with_flag(monkeypatch):
    """Con enable_research_rules=true las research pueden ejecutarse.

    English:
        With enable_research_rules=true, research rules can execute.
    """
    called: List[str] = []
    monkeypatch.setattr(
        "centinel.core.rules_engine.list_rules",
        lambda: [
            _make_rule_def("basic_diff", called),
            _make_rule_def("turnout_impossible", called),
        ],
    )

    engine = RulesEngine(config={"rules": {"global_enabled": True, "enable_research_rules": True}})
    result = engine.run({}, None)

    assert called == ["basic_diff", "turnout_impossible"]
    assert len(result.alerts) == 2
