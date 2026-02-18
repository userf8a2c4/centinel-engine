"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `src/centinel/core/rules/registry.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - RuleDefinition
  - rule
  - list_rules

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `src/centinel/core/rules/registry.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - RuleDefinition
  - rule
  - list_rules

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
"""

# Registry Module
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
