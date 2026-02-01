"""Primitivas de configuración del centro de comando.

Command center configuration primitives.
"""

from pathlib import Path

from dotenv import load_dotenv

_COMMAND_CENTER_ENV = Path(__file__).resolve().parent / ".env"
# Seguridad: Cargar variables sensibles del centro de comando. / Security: Load command center sensitive env vars.
load_dotenv(_COMMAND_CENTER_ENV, override=False)

from .master_switch import MasterSwitch
from .endpoints import Endpoint, EndpointRegistry
from .rules_config import RuleConfig, RuleRegistry
from .settings import CommandCenterSettings

__all__ = [
    "CommandCenterSettings",
    "Endpoint",
    "EndpointRegistry",
    "MasterSwitch",
    "RuleConfig",
    "RuleRegistry",
]
