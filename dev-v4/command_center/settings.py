"""Objeto de configuración principal para el centro de comando dev-v4.

Top-level settings object for dev-v4 command center.
"""

from dataclasses import dataclass, field

from .endpoints import EndpointRegistry
from .master_switch import MasterSwitch
from .rules_config import RuleRegistry


@dataclass
class CommandCenterSettings:
    """Configuración agregada para el panel del centro de comando.

    Aggregate settings for the command center panel.
    """

    master_switch: MasterSwitch = field(default_factory=MasterSwitch)
    endpoints: EndpointRegistry = field(default_factory=EndpointRegistry)
    rules: RuleRegistry = field(default_factory=RuleRegistry)
    metadata: dict[str, str] = field(default_factory=dict)

    def is_active(self) -> bool:
        return self.master_switch.enabled
