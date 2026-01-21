"""Primitivas de configuración del centro de comando.

Command center configuration primitives.
"""

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
