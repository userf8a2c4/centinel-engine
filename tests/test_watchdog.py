"""Pruebas básicas del watchdog de resiliencia.

Basic watchdog tests.
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
