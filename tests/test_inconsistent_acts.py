"""Tests for the inconsistent acts forensic tracker.

Pruebas para el rastreador forense de actas inconsistentes.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from auditor.inconsistent_acts import InconsistentActsTracker


def _build_payload(*, inconsistent_count: int, votes: dict[str, int], source: str = "synthetic_test") -> dict:
    """Build a generic election payload for rule-based tests.

    Construye un payload electoral genérico para pruebas basadas en reglas.
    """
    return {
        "meta": {"source": source},
        "totals": {"actasInconsistentes": inconsistent_count, "total_votes": sum(votes.values())},
        "candidates": [{"candidate_id": candidate, "votes": value} for candidate, value in votes.items()],
    }


def test_detects_inconsistent_key_and_persists(tmp_path: Path) -> None:
    """Tracker must detect and persist inconsistent key.

    El tracker debe detectar y persistir la clave de inconsistentes.
    """
    tracker = InconsistentActsTracker(config_path=tmp_path / "inconsistent_key.json")
    payload = _build_payload(inconsistent_count=2773, votes={"cand_1": 510000, "cand_2": 430000, "cand_3": 260000})

    tracker.load_snapshot(payload, datetime(2025, 11, 30, 23, 0, tzinfo=timezone.utc))

    assert tracker.detected_inconsistent_key == "totals.actasInconsistentes"
    persisted = json.loads((tmp_path / "inconsistent_key.json").read_text(encoding="utf-8"))
    assert persisted["inconsistent_key"] == "totals.actasInconsistentes"


def test_separates_normal_and_special_scrutiny_votes(tmp_path: Path) -> None:
    """Votes must be split into normal and special layers.

    Los votos deben separarse en capas normal y especial.
    """
    tracker = InconsistentActsTracker(config_path=tmp_path / "inconsistent_key.json")
    start = _build_payload(inconsistent_count=2773, votes={"cand_1": 510000, "cand_2": 430000, "cand_3": 260000})
    plateau = _build_payload(inconsistent_count=2773, votes={"cand_1": 517500, "cand_2": 435100, "cand_3": 262400})
    final = _build_payload(inconsistent_count=1920, votes={"cand_1": 556500, "cand_2": 470100, "cand_3": 278400})

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
    payloads = [
        _build_payload(inconsistent_count=2773, votes={"cand_1": 510000, "cand_2": 430000, "cand_3": 260000}),
        _build_payload(inconsistent_count=2773, votes={"cand_1": 517500, "cand_2": 435100, "cand_3": 262400}),
        _build_payload(inconsistent_count=1920, votes={"cand_1": 556500, "cand_2": 470100, "cand_3": 278400}),
    ]

    for index, payload in enumerate(payloads):
        tracker.load_snapshot(payload, datetime(2025, 11, 30, 23, index * 5, tzinfo=timezone.utc))

    stats = tracker.run_statistical_tests()
    anomalies = tracker.detect_anomalies()
    report = tracker.generate_forensic_report()

    assert stats["status"] == "ok"
    assert "chi_square_goodness_of_fit" in stats
    assert any(anomaly.kind == "high_impact_resolution" for anomaly in anomalies)
    assert "Source hashes SHA-256" in report
    assert "\\chi^2" in report


def test_detects_progressive_injection_pattern_rule_based(tmp_path: Path) -> None:
    """Tracker must flag progressive controlled injections using generic rule windows.

    El tracker debe marcar inyecciones progresivas controladas usando ventanas genéricas de reglas.
    """
    runtime_config = tmp_path / "config.json"
    runtime_config.write_text(
        json.dumps(
            {
                "inconsistent_acts": {
                    "progressive_injection_threshold": 800,
                    "min_consecutive_injections": 5,
                    "high_inconsistent_threshold": 1000,
                    "run_test_pvalue_threshold": 0.05,
                }
            }
        ),
        encoding="utf-8",
    )
    tracker = InconsistentActsTracker(
        config_path=tmp_path / "inconsistent_key.json",
        runtime_config_path=runtime_config,
    )

    payloads = [
        _build_payload(inconsistent_count=1600, votes={"cand_a": 500000, "cand_b": 480000}),
        _build_payload(inconsistent_count=1598, votes={"cand_a": 500380, "cand_b": 480010}),
        _build_payload(inconsistent_count=1596, votes={"cand_a": 500760, "cand_b": 480020}),
        _build_payload(inconsistent_count=1594, votes={"cand_a": 501140, "cand_b": 480030}),
        _build_payload(inconsistent_count=1592, votes={"cand_a": 501520, "cand_b": 480040}),
        _build_payload(inconsistent_count=1590, votes={"cand_a": 501900, "cand_b": 480050}),
    ]

    for index, payload in enumerate(payloads):
        tracker.load_snapshot(payload, datetime(2026, 1, 1, 0, index * 5, tzinfo=timezone.utc))

    progressive = tracker.detect_progressive_injection()
    report = tracker.generate_forensic_report()

    assert progressive is not None
    assert progressive["detected"] is True
    assert progressive["cycles_count"] >= 5
    assert progressive["avg_delta_per_cycle"] < 800
    assert "## 5. Detección de Inyección Progresiva Controlada" in report
