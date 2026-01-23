"""Integrity engine for running configured rules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Type

from ..rules.base_rule import BaseRule
from ..rules.benford_law import BenfordLawRule
from ..rules.change_threshold import ChangeThresholdRule
from ..rules.last_digit_uniformity import LastDigitUniformityRule
from ..rules.update_time import UpdateTimeRule

RULES_REGISTRY: Dict[str, Type[BaseRule]] = {
    "change_threshold": ChangeThresholdRule,
    "benford_law": BenfordLawRule,
    "last_digit_uniformity": LastDigitUniformityRule,
    "update_time": UpdateTimeRule,
}


@dataclass
class RuleResult:
    """Result of a rule evaluation."""

    name: str
    status: str
    details: Dict[str, Any]


@dataclass
class IntegrityReport:
    """Aggregated integrity report for a snapshot."""

    results: List[RuleResult]

    @property
    def status(self) -> str:
        if any(result.status == "fail" for result in self.results):
            return "fail"
        if any(result.status == "warn" for result in self.results):
            return "warn"
        return "pass"


class IntegrityEngine:
    """Runs integrity rules configured in YAML."""

    def __init__(self, rules_config: List[Dict[str, Any]]) -> None:
        self.rules = self._build_rules(rules_config)

    def _build_rules(self, rules_config: List[Dict[str, Any]]) -> List[BaseRule]:
        rules: List[BaseRule] = []
        for rule_cfg in rules_config:
            name = rule_cfg.get("name")
            params = rule_cfg.get("params", {})
            rule_cls = RULES_REGISTRY.get(name)
            if not rule_cls:
                continue
            rules.append(rule_cls(params))
        return rules

    def evaluate(
        self,
        current_data: Dict[str, Any],
        previous_data: Optional[Dict[str, Any]],
    ) -> IntegrityReport:
        results: List[RuleResult] = []
        for rule in self.rules:
            status, details = rule.evaluate(previous_data, current_data)
            results.append(RuleResult(rule.name, status, details))
        return IntegrityReport(results=results)
