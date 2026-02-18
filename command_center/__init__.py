"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `command_center/__init__.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - (sin componentes de nivel de módulo / no top-level components)

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `command_center/__init__.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - (sin componentes de nivel de módulo / no top-level components)

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
"""

#   Init   Module
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



from pathlib import Path

from dotenv import load_dotenv

_COMMAND_CENTER_ENV = Path(__file__).resolve().parent / ".env"
# Seguridad: Cargar variables sensibles del centro de comando. / Security: Load command center sensitive env vars.
load_dotenv(_COMMAND_CENTER_ENV, override=False)

from .master_switch import MasterSwitch  # noqa: E402
from .endpoints import Endpoint, EndpointRegistry  # noqa: E402
from .rules_config import RuleConfig, RuleRegistry  # noqa: E402
from .settings import CommandCenterSettings  # noqa: E402

__all__ = [
    "CommandCenterSettings",
    "Endpoint",
    "EndpointRegistry",
    "MasterSwitch",
    "RuleConfig",
    "RuleRegistry",
]
