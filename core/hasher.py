"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `core/hasher.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - trigger_post_hash_backup

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `core/hasher.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - trigger_post_hash_backup

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
"""

# Hasher Module
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

import logging
from pathlib import Path

from core.advanced_security import load_manager

LOGGER = logging.getLogger("centinel.hasher.security")


def trigger_post_hash_backup(snapshot_file: Path, hash_file: Path) -> None:
    """Trigger non-blocking backup attempt after hash persistence.

    Dispara intento no bloqueante de backup tras persistir hash.
    """
    try:
        manager = load_manager()
        manager.backups.maybe_backup(force=False)
        LOGGER.info("post_hash_backup_checked snapshot=%s hash=%s", snapshot_file.name, hash_file.name)
    except Exception as exc:  # noqa: BLE001
        LOGGER.warning("post_hash_backup_failed error=%s", exc)
