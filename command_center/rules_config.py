"""Configuración de reglas para el centro de comando.

Rules configuration for the command center.
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
    # Aquí se modifican números/variables de la regla (umbrales, ventanas, etc.).
    # This is where rule numbers/variables are modified (thresholds, windows, etc.).
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


def build_rule_parameters_template(
    *,
    threshold: str = "",
    window: str = "",
    notes: str = "",
) -> dict[str, str]:
    """Plantilla explícita para ubicar los valores modificables de una regla.

    Explicit template to locate the modifiable values of a rule.
    """

    # Nota: estos campos son los puntos donde se cambian números/variables.
    # Note: these fields are the points where numbers/variables are changed.
    return {
        "threshold": threshold,
        "window": window,
        "notes": notes,
    }
