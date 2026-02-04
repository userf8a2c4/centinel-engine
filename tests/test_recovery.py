"""Pruebas de recuperación para checkpoints corruptos.

Recovery tests for corrupt checkpoints.
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
