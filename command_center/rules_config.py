"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `command_center/rules_config.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - RuleConfig
  - RuleRegistry
  - build_rule_parameters_template

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `command_center/rules_config.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - RuleConfig
  - RuleRegistry
  - build_rule_parameters_template

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
"""

# Rules Config Module
# AUTO-DOC-INDEX
#
# ES: Índice rápido
#   1) Propósito del módulo
#   2) Componentes principales
#   3) Puntos de extensión
#
# EN: Quick index
#   1) Module purpose
#   2) Main components
#   3) Extension points
#
# Secciones / Sections:
#   - Configuración / Configuration
#   - Lógica principal / Core logic
#   - Integraciones / Integrations



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
        """Registra una regla en el catálogo.

        English:
            Register a rule in the catalog.
        """
        self.rules[rule.name] = rule

    def remove(self, name: str) -> None:
        """Elimina una regla por nombre si existe.

        English:
            Remove a rule by name if it exists.
        """
        self.rules.pop(name, None)

    def list_enabled(self) -> Iterable[RuleConfig]:
        """Itera reglas habilitadas en el catálogo.

        English:
            Iterate over enabled rules in the catalog.
        """
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
