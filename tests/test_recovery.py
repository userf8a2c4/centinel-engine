"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `tests/test_recovery.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - test_recovery_checksum_mismatch_reprocess

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `tests/test_recovery.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - test_recovery_checksum_mismatch_reprocess

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
"""

import asyncio
import json

from centinel.recovery import RecoveryDecisionType, RecoveryManager


def test_recovery_checksum_mismatch_reprocess(tmp_path) -> None:
    """Español: Reprocesa último batch ante checksum inválido.

    English: Reprocesses last batch when checksum is invalid.
    """
    checkpoint_dir = tmp_path / "checkpoints"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = checkpoint_dir / "checkpoint.json"

    payload = {
        "acta_id": "A1",
        "offset": 10,
        "batch_id": "B1",
        "created_at": "2025-01-01T00:00:00Z",
        "checksum": "bad-checksum",
    }
    checkpoint_path.write_text(json.dumps(payload), encoding="utf-8")

    manager = RecoveryManager(storage_path=tmp_path)
    decision = asyncio.run(manager.recover())

    assert decision.decision is RecoveryDecisionType.REPROCESS_LAST_BATCH
