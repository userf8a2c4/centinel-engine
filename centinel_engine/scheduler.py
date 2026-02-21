"""Scheduler bootstrap helpers.

Bilingual: Utilidades de arranque del scheduler.
"""

from __future__ import annotations

import logging
import sys

from centinel_engine import secure_backup

logger = logging.getLogger(__name__)


def verify_backup_integrity_on_startup() -> None:
    """Verify full backup chain before scheduler main loop starts.

    Bilingual: Verifica la cadena completa de backup antes de iniciar el loop principal.
    """
    # Full chain verification on startup / # Verificación completa de cadena al arranque
    if not secure_backup.verify_last_bundle():
        logger.critical("Backup chain corrupted - halting")
        sys.exit(1)
