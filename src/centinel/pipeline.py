# Pipeline Module
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

"""Arranque del pipeline principal con recuperación.

English:
    Main pipeline startup with recovery.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Optional

from .config import load_config
from .logging import setup_logging
from .recovery import RecoveryDecisionType, RecoveryManager


@dataclass
class PipelineCursor:
    """Cursor simple del pipeline.

    English: Minimal pipeline cursor.
    """

    acta_id: Optional[str] = None
    offset: int = 0
    batch_id: Optional[str] = None

    def reset(self) -> None:
        """Español: Función reset del módulo src/centinel/pipeline.py.

        English: Function reset defined in src/centinel/pipeline.py.
        """
        self.acta_id = None
        self.offset = 0
        self.batch_id = None

    def reprocess_last_batch(self) -> None:
        """Español: Función reprocess_last_batch del módulo src/centinel/pipeline.py.

        English: Function reprocess_last_batch defined in src/centinel/pipeline.py.
        """
        self.offset = 0


async def start_pipeline() -> None:
    """Ejemplo de arranque con RecoveryManager.

    English: Startup example using RecoveryManager.
    """

    settings = load_config()
    logger = setup_logging(settings.LOG_LEVEL, settings.STORAGE_PATH)
    recovery_manager = RecoveryManager(
        storage_path=settings.STORAGE_PATH,
        logger=logger,
        expected_source_format=settings.SOURCES[0].type if settings.SOURCES else None,
        stale_checkpoint_policy="continue",
    )

    decision = await recovery_manager.recover()
    cursor = PipelineCursor()

    if decision.decision is RecoveryDecisionType.CONTINUE_FROM_LAST_ACTA:
        cursor.acta_id = decision.acta_id
        cursor.offset = decision.offset or 0
        cursor.batch_id = decision.batch_id
    elif decision.decision is RecoveryDecisionType.REPROCESS_LAST_BATCH:
        cursor.reprocess_last_batch()
        cursor.acta_id = decision.acta_id
        cursor.batch_id = decision.batch_id
    elif decision.decision is RecoveryDecisionType.START_FROM_BEGINNING:
        cursor.reset()
    elif decision.decision is RecoveryDecisionType.PAUSE_AND_ALERT:
        logger.error("pipeline_paused", reason=decision.reason, alerts=decision.alerts)
        return
    elif decision.decision is RecoveryDecisionType.SKIP_TO_NEXT_VALID:
        logger.warning(
            "pipeline_skip_to_next_valid",
            reason=decision.reason,
            alerts=decision.alerts,
        )

    logger.info(
        "pipeline_ready",
        acta_id=cursor.acta_id,
        offset=cursor.offset,
        batch_id=cursor.batch_id,
    )


if __name__ == "__main__":
    asyncio.run(start_pipeline())
