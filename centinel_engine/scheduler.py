"""Scheduler bootstrap helpers.

Bilingual: Utilidades de arranque del scheduler.
"""

from __future__ import annotations

import logging
import sys

from centinel_engine import secure_backup

logger = logging.getLogger(__name__)


def verify_backup_integrity_on_startup() -> None:
    """Verify backup integrity before scheduler main loop starts.

    Bilingual: Verifica integridad del backup antes de iniciar el loop principal.
    """
    # Verify backup integrity on startup / Verificar integridad backup al arranque
    if not secure_backup.verify_last_bundle():
        logger.critical("Last backup corrupted - halting")
        sys.exit(1)
