"""Primitivas de configuración del centro de comando para v5.

Command center configuration primitives for v5.
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
