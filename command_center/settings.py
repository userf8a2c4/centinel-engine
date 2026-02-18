# Settings Module
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

"""Objeto de configuración principal para el centro de comando.

Top-level settings object for the command center.
"""

from dataclasses import dataclass, field

from .endpoints import EndpointRegistry
from .master_switch import MasterSwitch
from .rules_config import RuleRegistry


@dataclass
class ScrapingSchedule:
    """Controla el tiempo/intervalo de scraping.

    Controls the scraping timing/interval.
    """

    # Intervalo en segundos entre ejecuciones del scraping.
    # Interval in seconds between scraping runs.
    interval_seconds: int = 900
    # Fuente de datos o job al que aplica el intervalo.
    # Data source or job the interval applies to.
    target: str = "cne_actas"
    # Nota: cambia estos valores aquí para modificar el tiempo de scraping.
    # Note: change these values here to modify the scraping interval.


@dataclass
class CommandCenterSettings:
    """Configuración agregada para el panel del centro de comando.

    Aggregate settings for the command center panel.
    """

    master_switch: MasterSwitch = field(default_factory=MasterSwitch)
    scraping_schedule: ScrapingSchedule = field(default_factory=ScrapingSchedule)
    endpoints: EndpointRegistry = field(default_factory=EndpointRegistry)
    rules: RuleRegistry = field(default_factory=RuleRegistry)
    metadata: dict[str, str] = field(default_factory=dict)

    def is_active(self) -> bool:
        """Indica si el centro de comando está habilitado.

        English:
            Indicate whether the command center is enabled.
        """
        return self.master_switch.enabled
