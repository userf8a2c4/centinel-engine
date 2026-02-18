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

"""Primitivas de configuración del centro de comando.

Command center configuration primitives.
"""

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
