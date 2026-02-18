# Master Switch Module
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

"""Controles del interruptor maestro para el centro de comando.

Master switch controls for the command center.
"""

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class MasterSwitch:
    """Interruptor global (kill-switch) del centro de comando.

    Global kill-switch for the command center.
    """

    enabled: bool = True
    updated_at: datetime | None = None
    reason: str | None = None

    def with_update(self, *, enabled: bool | None = None, reason: str | None = None) -> "MasterSwitch":
        """Devuelve una copia del interruptor con el estado actualizado.

        Return a copy of the switch with updated state.
        """

        return MasterSwitch(
            enabled=self.enabled if enabled is None else enabled,
            updated_at=datetime.now(timezone.utc),
            reason=reason if reason is not None else self.reason,
        )
