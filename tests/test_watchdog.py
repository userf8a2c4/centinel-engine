"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `tests/test_watchdog.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - test_watchdog_snapshot_stale

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `tests/test_watchdog.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - test_watchdog_snapshot_stale

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
"""

import os
import time

from scripts.watchdog import WatchdogConfig, _check_snapshot


def test_watchdog_snapshot_stale(tmp_path) -> None:
    """Español: Marca snapshot viejo como stale.

    English: Marks an old snapshot as stale.
    """
    source_dir = tmp_path / "snapshots" / "test_source"
    source_dir.mkdir(parents=True)
    snapshot = source_dir / "snapshot_1.json"
    snapshot.write_text("{}", encoding="utf-8")

    old = time.time() - 3600
    os.utime(snapshot, (old, old))

    cfg = WatchdogConfig(data_dir=str(tmp_path), max_inactivity_minutes=1)
    ok, message = _check_snapshot(cfg)

    assert ok is False
    assert message.startswith("snapshot_stale")
