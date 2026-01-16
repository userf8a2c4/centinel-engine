"""Primitivas de configuración del centro de comando para dev-v4.

Command center configuration primitives for dev-v4.
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
