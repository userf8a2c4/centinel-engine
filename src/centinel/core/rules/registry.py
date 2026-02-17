"""Registro y decorador para reglas avanzadas.

Registry and decorator for advanced rules.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional

RuleFunc = Callable[[dict, Optional[dict], dict], List[dict]]


@dataclass(frozen=True)
class RuleDefinition:
    """Metadatos de una regla registrada.

    Metadata for a registered rule.
    """

    name: str
    severity: str
    description: str
    config_key: str
    func: RuleFunc


_RULE_REGISTRY: List[RuleDefinition] = []


def rule(*, name: str, severity: str, description: str, config_key: str) -> Callable:
    """Decorador para registrar reglas con metadatos.

    Decorator to register rules with metadata.
    """

    def decorator(func: RuleFunc) -> RuleFunc:
        """Registra la función con sus metadatos y devuelve la original.

        English:
            Register the function with its metadata and return the original.
        """
        _RULE_REGISTRY.append(
            RuleDefinition(
                name=name,
                severity=severity,
                description=description,
                config_key=config_key,
                func=func,
            )
        )
        return func

    return decorator


def list_rules() -> List[RuleDefinition]:
    """Devuelve las reglas registradas.

    Returns the registered rules.
    """

    return list(_RULE_REGISTRY)
