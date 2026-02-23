"""Tests for the inconsistent acts forensic tracker.

Pruebas para el rastreador forense de actas inconsistentes.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from auditor.inconsistent_acts import InconsistentActsTracker


def _load(path: Path) -> dict:
    """Read JSON fixture from disk.

    Lee fixture JSON desde disco.
    """
    return json.loads(path.read_text(encoding="utf-8"))


def test_detects_inconsistent_key_and_persists(tmp_path: Path) -> None:
    """Tracker must detect and persist inconsistent key.

    El tracker debe detectar y persistir la clave de inconsistentes.
    """
    tracker = InconsistentActsTracker(config_path=tmp_path / "inconsistent_key.json")
    snapshot = _load(Path("tests/fixtures/inconsistent_acts_2025/snapshot_inicio.json"))

    tracker.load_snapshot(snapshot, datetime(2025, 11, 30, 23, 0, tzinfo=timezone.utc))

    assert tracker.detected_inconsistent_key == "totals.actasInconsistentes"
    persisted = json.loads((tmp_path / "inconsistent_key.json").read_text(encoding="utf-8"))
    assert persisted["inconsistent_key"] == "totals.actasInconsistentes"


def test_separates_normal_and_special_scrutiny_votes(tmp_path: Path) -> None:
    """Votes must be split into normal and special layers.

    Los votos deben separarse en capas normal y especial.
    """
    tracker = InconsistentActsTracker(config_path=tmp_path / "inconsistent_key.json")
    start = _load(Path("tests/fixtures/inconsistent_acts_2025/snapshot_inicio.json"))
    plateau = _load(Path("tests/fixtures/inconsistent_acts_2025/snapshot_pico_estancado.json"))
    final = _load(Path("tests/fixtures/inconsistent_acts_2025/snapshot_resolucion_final.json"))

    tracker.load_snapshot(start, datetime(2025, 11, 30, 23, 0, tzinfo=timezone.utc))
    tracker.load_snapshot(plateau, datetime(2025, 11, 30, 23, 5, tzinfo=timezone.utc))
    tracker.load_snapshot(final, datetime(2025, 12, 1, 0, 10, tzinfo=timezone.utc))

    cumulative = tracker.get_special_scrutiny_cumulative()

    assert tracker.normal_votes == {"cand_1": 7500, "cand_2": 5100, "cand_3": 2400}
    assert cumulative["votes_by_candidate"] == {"cand_1": 39000, "cand_2": 35000, "cand_3": 16000}


def test_statistical_suite_and_report(tmp_path: Path) -> None:
    """Statistical output and markdown report must be reproducible.

    La salida estadística y reporte markdown deben ser reproducibles.
    """
    tracker = InconsistentActsTracker(config_path=tmp_path / "inconsistent_key.json")
    fixtures = [
        "snapshot_inicio.json",
        "snapshot_pico_estancado.json",
        "snapshot_resolucion_final.json",
    ]

    for index, fixture_name in enumerate(fixtures):
        payload = _load(Path("tests/fixtures/inconsistent_acts_2025") / fixture_name)
        tracker.load_snapshot(payload, datetime(2025, 11, 30, 23, index * 5, tzinfo=timezone.utc))

    stats = tracker.run_statistical_tests()
    anomalies = tracker.detect_anomalies()
    report = tracker.generate_forensic_report()

    assert stats["status"] == "ok"
    assert "chi_square_goodness_of_fit" in stats
    assert any(anomaly.kind == "high_impact_resolution" for anomaly in anomalies)
    assert "Source hashes SHA-256" in report
    assert "\\chi^2" in report
