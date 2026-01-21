"""Controles del interruptor maestro para el centro de comando v5.

Master switch controls for the v5 command center.
"""

from dataclasses import dataclass
from datetime import datetime


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
            updated_at=datetime.utcnow(),
            reason=reason if reason is not None else self.reason,
        )
