"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `core/logger.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - register_attack_logbook
  - log_suspicious_event

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `core/logger.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - register_attack_logbook
  - log_suspicious_event

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
"""

# Logger Module
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



from __future__ import annotations

from typing import Any

from core.attack_logger import AttackForensicsLogbook

_ATTACK_LOGBOOK: AttackForensicsLogbook | None = None


def register_attack_logbook(logbook: AttackForensicsLogbook | None) -> None:
    """Register global attack logbook instance.

    Registra instancia global de bitácora de ataques.
    """
    global _ATTACK_LOGBOOK
    _ATTACK_LOGBOOK = logbook


def log_suspicious_event(event: dict[str, Any]) -> None:
    """Forward suspicious event metadata to forensics logbook.

    Reenvía metadatos sospechosos a la bitácora forense.
    """
    if not _ATTACK_LOGBOOK:
        return
    _ATTACK_LOGBOOK.log_http_request(
        ip=str(event.get("ip", "0.0.0.0")),  # nosec B104 - fallback default, not a bind address
        method=str(event.get("method", "GET")),
        route=str(event.get("route", "/unknown")),
        headers=dict(event.get("headers", {})),
        content_length=int(event.get("content_length", 0)),
    )
