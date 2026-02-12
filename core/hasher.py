"""Hasher post-processing security hook.

Hook de seguridad post-procesamiento de hashes.
"""

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
