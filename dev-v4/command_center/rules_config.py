"""Configuración de reglas para el centro de comando dev-v4.

Rules configuration for dev-v4 command center.
"""

from dataclasses import dataclass, field
from typing import Iterable


@dataclass(frozen=True)
class RuleConfig:
    """Configuración para una regla individual.

    Configuration for a single rule.
    """

    name: str
    description: str
    enabled: bool = True
    parameters: dict[str, str] = field(default_factory=dict)


@dataclass
class RuleRegistry:
    """Registro de configuraciones de reglas.

    Registry for rule configurations.
    """

    rules: dict[str, RuleConfig] = field(default_factory=dict)

    def add(self, rule: RuleConfig) -> None:
        self.rules[rule.name] = rule

    def remove(self, name: str) -> None:
        self.rules.pop(name, None)

    def list_enabled(self) -> Iterable[RuleConfig]:
        return (rule for rule in self.rules.values() if rule.enabled)
