"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `command_center/master_switch.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - MasterSwitch

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `command_center/master_switch.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - MasterSwitch

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
"""

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
