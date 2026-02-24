"""Tests for the inconsistent acts forensic tracker.

Pruebas para el rastreador forense de actas inconsistentes.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
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
    assert "Hashes de fuente SHA-256" in report
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


# ---------------------------------------------------------------------------
# Tests para velocidad de resolución anómala
# ---------------------------------------------------------------------------


def test_detects_anomalous_resolution_velocity(tmp_path: Path) -> None:
    """Detect when actas are resolved faster than humanly possible.

    Detecta cuando las actas se resuelven más rápido de lo humanamente posible.
    """
    tracker = InconsistentActsTracker(
        config_path=tmp_path / "inconsistent_key.json",
        max_resolution_rate=5.0,
    )
    base_time = datetime(2025, 12, 8, 14, 0, tzinfo=timezone.utc)

    # Snapshot 1: 2000 actas inconsistentes.
    tracker.load_snapshot(
        _build_payload(inconsistent_count=2000, votes={"X": 500000, "Y": 480000}),
        base_time,
    )
    # Snapshot 2: 1 minuto después, se resolvieron 500 actas (500/min >> 5/min).
    tracker.load_snapshot(
        _build_payload(inconsistent_count=1500, votes={"X": 510000, "Y": 490000}),
        base_time + timedelta(minutes=1),
    )

    velocity_anomalies = tracker.detect_resolution_velocity_anomalies()

    assert len(velocity_anomalies) == 1
    assert velocity_anomalies[0]["rate_per_minute"] == 500.0
    assert velocity_anomalies[0]["delta_actas"] == 500


def test_no_velocity_anomaly_under_threshold(tmp_path: Path) -> None:
    """Normal resolution rates must not trigger velocity anomaly.

    Tasas normales de resolución no deben disparar anomalía de velocidad.
    """
    tracker = InconsistentActsTracker(
        config_path=tmp_path / "inconsistent_key.json",
        max_resolution_rate=10.0,
    )
    base_time = datetime(2025, 12, 8, 14, 0, tzinfo=timezone.utc)

    tracker.load_snapshot(
        _build_payload(inconsistent_count=2000, votes={"X": 500000, "Y": 480000}),
        base_time,
    )
    # 5 actas en 10 minutos = 0.5/min, well under threshold.
    tracker.load_snapshot(
        _build_payload(inconsistent_count=1995, votes={"X": 500500, "Y": 480500}),
        base_time + timedelta(minutes=10),
    )

    assert len(tracker.detect_resolution_velocity_anomalies()) == 0


# ---------------------------------------------------------------------------
# Tests para beneficio asimétrico
# ---------------------------------------------------------------------------


def test_detects_asymmetric_benefit(tmp_path: Path) -> None:
    """Detect disproportionate benefit to one candidate in special scrutiny.

    Detecta beneficio desproporcionado a un candidato en escrutinio especial.
    """
    tracker = InconsistentActsTracker(config_path=tmp_path / "inconsistent_key.json")
    base_time = datetime(2025, 12, 8, 14, 0, tzinfo=timezone.utc)

    # Snapshot inicial: candidatos parejos.
    tracker.load_snapshot(
        _build_payload(inconsistent_count=2000, votes={"A": 500000, "B": 500000}),
        base_time,
    )
    # Voto normal: proporciones iguales (no hay resolución de AI).
    tracker.load_snapshot(
        _build_payload(inconsistent_count=2000, votes={"A": 505000, "B": 505000}),
        base_time + timedelta(minutes=5),
    )
    # Resolución masiva: A recibe 80%, B recibe 20% → sesgo claro.
    tracker.load_snapshot(
        _build_payload(inconsistent_count=1000, votes={"A": 545000, "B": 515000}),
        base_time + timedelta(minutes=10),
    )

    result = tracker.detect_asymmetric_benefit()

    assert result is not None
    assert result["beneficiary"] == "A"
    assert result["swing_pp"] > 0
    assert result["significant"] is True


def test_no_asymmetric_benefit_when_proportions_match(tmp_path: Path) -> None:
    """No asymmetric benefit when normal and special proportions are similar.

    Sin beneficio asimétrico cuando las proporciones normal y especial son similares.
    """
    tracker = InconsistentActsTracker(config_path=tmp_path / "inconsistent_key.json")
    base_time = datetime(2025, 12, 8, 14, 0, tzinfo=timezone.utc)

    tracker.load_snapshot(
        _build_payload(inconsistent_count=2000, votes={"A": 500000, "B": 500000}),
        base_time,
    )
    # Voto normal con proporciones iguales.
    tracker.load_snapshot(
        _build_payload(inconsistent_count=2000, votes={"A": 510000, "B": 510000}),
        base_time + timedelta(minutes=5),
    )
    # Resolución con proporciones iguales.
    tracker.load_snapshot(
        _build_payload(inconsistent_count=1500, votes={"A": 520000, "B": 520000}),
        base_time + timedelta(minutes=10),
    )

    result = tracker.detect_asymmetric_benefit()
    # Sin datos suficientes o swing < 2% → None.
    assert result is None or not result["significant"]


# ---------------------------------------------------------------------------
# Tests para patrón hold-and-release
# ---------------------------------------------------------------------------


def test_detects_hold_and_release_pattern(tmp_path: Path) -> None:
    """Detect stagnation followed by bulk resolution.

    Detecta estancamiento seguido de resolución masiva.
    """
    tracker = InconsistentActsTracker(
        config_path=tmp_path / "inconsistent_key.json",
        stagnation_cycles_threshold=3,
        bulk_resolution_threshold=200,
    )
    base_time = datetime(2025, 12, 8, 10, 0, tzinfo=timezone.utc)

    # Primer snapshot.
    tracker.load_snapshot(
        _build_payload(inconsistent_count=2000, votes={"X": 500000, "Y": 450000}),
        base_time,
    )

    # 6 ciclos de estancamiento (AI no cambia).
    for i in range(1, 7):
        tracker.load_snapshot(
            _build_payload(inconsistent_count=2000, votes={"X": 500000 + i * 100, "Y": 450000 + i * 100}),
            base_time + timedelta(minutes=i * 5),
        )

    # Resolución masiva tras el estancamiento.
    tracker.load_snapshot(
        _build_payload(inconsistent_count=1500, votes={"X": 520000, "Y": 460000}),
        base_time + timedelta(minutes=40),
    )

    patterns = tracker.detect_hold_and_release()

    assert len(patterns) >= 1
    assert patterns[0]["stagnation_cycles"] >= 3
    assert patterns[0]["released_actas"] == 500


# ---------------------------------------------------------------------------
# Tests para Benford's Law
# ---------------------------------------------------------------------------


def test_benford_insufficient_data(tmp_path: Path) -> None:
    """Benford test returns None when insufficient data.

    El test de Benford retorna None con datos insuficientes.
    """
    tracker = InconsistentActsTracker(config_path=tmp_path / "inconsistent_key.json")
    base_time = datetime(2025, 12, 8, 14, 0, tzinfo=timezone.utc)

    tracker.load_snapshot(
        _build_payload(inconsistent_count=2000, votes={"A": 500000, "B": 400000}),
        base_time,
    )
    tracker.load_snapshot(
        _build_payload(inconsistent_count=1990, votes={"A": 500500, "B": 400500}),
        base_time + timedelta(minutes=5),
    )

    result = tracker.detect_benford_special_scrutiny()
    assert result is None


def test_benford_with_sufficient_data(tmp_path: Path) -> None:
    """Benford test runs when enough resolution events exist.

    El test de Benford se ejecuta con suficientes eventos de resolución.
    """
    tracker = InconsistentActsTracker(config_path=tmp_path / "inconsistent_key.json")
    base_time = datetime(2025, 12, 8, 14, 0, tzinfo=timezone.utc)

    # Crear snapshot inicial.
    tracker.load_snapshot(
        _build_payload(inconsistent_count=2000, votes={"A": 500000, "B": 400000, "C": 200000}),
        base_time,
    )

    # Generar 12 resoluciones con deltas positivos variados para tener >= 10 muestras.
    for i in range(1, 13):
        tracker.load_snapshot(
            _build_payload(
                inconsistent_count=2000 - i * 10,
                votes={
                    "A": 500000 + i * 1500,
                    "B": 400000 + i * 1200,
                    "C": 200000 + i * 300,
                },
            ),
            base_time + timedelta(minutes=i * 5),
        )

    result = tracker.detect_benford_special_scrutiny()

    assert result is not None
    assert "chi2_statistic" in result
    assert "chi2_pvalue" in result
    assert result["n_samples"] >= 10
    assert "digit_analysis" in result


# ---------------------------------------------------------------------------
# Tests para detección de apagón comunicacional
# ---------------------------------------------------------------------------


def test_detects_blackout_window(tmp_path: Path) -> None:
    """Detect communication blackout with trend shift.

    Detecta apagón comunicacional con cambio de tendencia.
    """
    tracker = InconsistentActsTracker(
        config_path=tmp_path / "inconsistent_key.json",
        blackout_gap_minutes=20,
    )
    base_time = datetime(2025, 12, 8, 14, 0, tzinfo=timezone.utc)

    # Snapshot antes del apagón: A lidera.
    tracker.load_snapshot(
        _build_payload(inconsistent_count=2000, votes={"A": 520000, "B": 480000}),
        base_time,
    )
    # Snapshot 1 hora después (gap > 20 min) con cambio de tendencia.
    tracker.load_snapshot(
        _build_payload(inconsistent_count=1800, votes={"A": 530000, "B": 510000}),
        base_time + timedelta(hours=1),
    )

    blackouts = tracker.detect_blackout_windows()

    assert len(blackouts) == 1
    assert blackouts[0]["gap_minutes"] == 60.0
    assert len(blackouts[0]["trend_shifts_pp"]) > 0


def test_no_blackout_with_normal_gap(tmp_path: Path) -> None:
    """No blackout detected when gaps are within normal range.

    No se detecta apagón cuando los gaps están dentro del rango normal.
    """
    tracker = InconsistentActsTracker(
        config_path=tmp_path / "inconsistent_key.json",
        blackout_gap_minutes=30,
    )
    base_time = datetime(2025, 12, 8, 14, 0, tzinfo=timezone.utc)

    tracker.load_snapshot(
        _build_payload(inconsistent_count=2000, votes={"A": 520000, "B": 480000}),
        base_time,
    )
    # Gap de solo 5 minutos.
    tracker.load_snapshot(
        _build_payload(inconsistent_count=1990, votes={"A": 521000, "B": 481000}),
        base_time + timedelta(minutes=5),
    )

    assert len(tracker.detect_blackout_windows()) == 0


# ---------------------------------------------------------------------------
# Tests para anomalías integradas en detect_anomalies
# ---------------------------------------------------------------------------


def test_detect_anomalies_includes_velocity(tmp_path: Path) -> None:
    """detect_anomalies must include velocity anomalies.

    detect_anomalies debe incluir anomalías de velocidad.
    """
    tracker = InconsistentActsTracker(
        config_path=tmp_path / "inconsistent_key.json",
        max_resolution_rate=5.0,
    )
    base_time = datetime(2025, 12, 8, 14, 0, tzinfo=timezone.utc)

    tracker.load_snapshot(
        _build_payload(inconsistent_count=2000, votes={"X": 500000, "Y": 480000}),
        base_time,
    )
    tracker.load_snapshot(
        _build_payload(inconsistent_count=1000, votes={"X": 530000, "Y": 500000}),
        base_time + timedelta(minutes=1),
    )

    anomalies = tracker.detect_anomalies()
    kinds = [a.kind for a in anomalies]
    assert "anomalous_resolution_velocity" in kinds


def test_detect_anomalies_includes_blackout(tmp_path: Path) -> None:
    """detect_anomalies must include blackout anomalies with trend shifts.

    detect_anomalies debe incluir anomalías de apagón con cambio de tendencia.
    """
    tracker = InconsistentActsTracker(
        config_path=tmp_path / "inconsistent_key.json",
        blackout_gap_minutes=20,
    )
    base_time = datetime(2025, 12, 8, 14, 0, tzinfo=timezone.utc)

    tracker.load_snapshot(
        _build_payload(inconsistent_count=2000, votes={"A": 520000, "B": 480000}),
        base_time,
    )
    tracker.load_snapshot(
        _build_payload(inconsistent_count=1800, votes={"A": 530000, "B": 515000}),
        base_time + timedelta(hours=2),
    )

    anomalies = tracker.detect_anomalies()
    kinds = [a.kind for a in anomalies]
    assert "blackout_with_trend_shift" in kinds


# ---------------------------------------------------------------------------
# Test del reporte forense completo
# ---------------------------------------------------------------------------


def test_forensic_report_contains_all_sections(tmp_path: Path) -> None:
    """Full forensic report must contain all analysis sections.

    El reporte forense completo debe contener todas las secciones de análisis.
    """
    tracker = InconsistentActsTracker(
        config_path=tmp_path / "inconsistent_key.json",
        max_resolution_rate=5.0,
        blackout_gap_minutes=10,
    )
    base_time = datetime(2025, 12, 8, 14, 0, tzinfo=timezone.utc)

    tracker.load_snapshot(
        _build_payload(inconsistent_count=2000, votes={"A": 500000, "B": 450000, "C": 200000}),
        base_time,
    )
    for i in range(1, 8):
        tracker.load_snapshot(
            _build_payload(
                inconsistent_count=2000 - i * 50,
                votes={
                    "A": 500000 + i * 2000,
                    "B": 450000 + i * 1000,
                    "C": 200000 + i * 500,
                },
            ),
            base_time + timedelta(minutes=i * 5),
        )

    report = tracker.generate_forensic_report()

    assert "## 1. Clave detectada" in report
    assert "## 2. Acumulado escrutinio especial" in report
    assert "## 3. Pruebas estadísticas" in report
    assert "## 4. Anomalías detectadas" in report
    assert "## 5. Detección de Inyección Progresiva" in report
    assert "## 6. Velocidad de Resolución" in report
    assert "## 7. Beneficio Asimétrico" in report
    assert "## 8. Patrón Hold-and-Release" in report
    assert "## 9. Ley de Benford" in report
    assert "## 10. Apagones Comunicacionales" in report
    assert "Hashes de fuente SHA-256" in report
