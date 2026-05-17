"""Tests for the Supabase forensics publisher.

Pruebas para el publicador forense de Supabase.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from centinel.sync import forensics_publisher as fp


def _cne_snapshot(inconsistentes: str, votos: dict[str, str]) -> dict:
    return {
        "resultados": [
            {"partido": f"P{n}", "candidato": n, "votos": v, "porcentaje": "0.0"}
            for n, v in votos.items()
        ],
        "estadisticas": {
            "estado_actas_divulgadas": {"actas_inconsistentes": inconsistentes},
        },
    }


def test_parse_snapshot_timestamp() -> None:
    """Filename timestamp must parse to a UTC datetime.

    La marca del nombre de archivo debe parsear a datetime UTC.
    """
    ts = fp.parse_snapshot_timestamp(Path("snapshot_2025-12-03_22-00-40.json"))
    assert ts == datetime(2025, 12, 3, 22, 0, 40, tzinfo=timezone.utc)
    assert fp.parse_snapshot_timestamp(Path("not_a_snapshot.json")) is None


def test_build_coverage_flags_gap() -> None:
    """A gap beyond 2x cadence lowers coverage and is recorded.

    Un hueco mayor a 2x la cadencia baja la cobertura y se registra.
    """
    base = datetime(2025, 12, 3, 12, 0, tzinfo=timezone.utc)
    timestamps = [
        base,
        base + timedelta(minutes=5),
        base + timedelta(minutes=10),
        base + timedelta(hours=13),  # 13h blackout
        base + timedelta(hours=13, minutes=5),
    ]
    cov = fp.build_coverage(
        timestamps, target_cadence_minutes=5.0, now=base + timedelta(hours=13, minutes=6)
    )
    assert cov["gaps_count"] == 1
    assert cov["coverage_pct"] < 100.0
    assert cov["monitoring_since"] == timestamps[0].isoformat()
    assert cov["open_gap_minutes"] == 0.0


def test_build_coverage_open_gap_when_stale() -> None:
    """If last capture is far in the past, an open gap is flagged.

    Si la última captura es vieja, se marca un hueco abierto.
    """
    base = datetime(2025, 12, 3, 12, 0, tzinfo=timezone.utc)
    cov = fp.build_coverage(
        [base, base + timedelta(minutes=5)],
        target_cadence_minutes=5.0,
        now=base + timedelta(hours=4),
    )
    assert cov["open_gap_minutes"] > 0.0


def test_build_forensics_block_shape() -> None:
    """Forensics block must expose every key the panel renders.

    El bloque forense debe exponer cada clave que el panel renderiza.
    """
    tracker = fp.InconsistentActsTracker()
    base = datetime(2025, 12, 3, 22, 0, tzinfo=timezone.utc)
    tracker.load_snapshot(
        _cne_snapshot("2,189", {"CANDIDATO_A": "1,027,090", "CANDIDATO_B": "1,013,050"}), base
    )
    tracker.load_snapshot(
        _cne_snapshot("2,773", {"CANDIDATO_A": "1,256,428", "CANDIDATO_B": "1,298,835"}),
        base + timedelta(hours=13),
    )
    block = fp.build_forensics_block(tracker)
    for key in (
        "progressive_injection",
        "velocity_anomaly",
        "asymmetric_benefit",
        "hold_and_release",
        "benford",
        "zscore",
        "blackout",
    ):
        assert key in block
    assert "pvalue" in block["benford"]
    assert isinstance(block["blackout"]["gaps"], list)


def test_run_and_publish_emits_coverage_alerts(monkeypatch, tmp_path: Path) -> None:
    """Capture gaps must be pushed as alerts even without trend shifts.

    Los huecos de captura deben emitirse como alertas aunque no haya cambio
    de tendencia.
    """
    snap_dir = tmp_path / "snapshots" / "NACIONAL"
    snap_dir.mkdir(parents=True)
    base = datetime(2025, 12, 3, 12, 0, tzinfo=timezone.utc)
    stamps = [base, base + timedelta(minutes=5), base + timedelta(hours=13)]
    for i, ts in enumerate(stamps):
        name = ts.strftime("snapshot_%Y-%m-%d_%H-%M-%S.json")
        (snap_dir / name).write_text(
            json.dumps(
                _cne_snapshot(
                    str(2000 + i * 50),
                    {"CANDIDATO_A": str(1_000_000 + i), "CANDIDATO_B": str(1_010_000 + i * 9)},
                )
            ),
            encoding="utf-8",
        )

    alerts: list[dict] = []
    monkeypatch.setattr(fp.supabase_sync, "is_configured", lambda: True)
    monkeypatch.setattr(
        fp.supabase_sync,
        "push_snapshot",
        lambda **kw: 42,
    )
    monkeypatch.setattr(
        fp.supabase_sync,
        "push_alert",
        lambda **kw: alerts.append(kw) or 1,
    )

    snapshot_id = fp.run_and_publish(
        sorted(snap_dir.glob("snapshot_*.json")),
        captured_at=base.isoformat(),
        chain_hash="deadbeef",
        merkle_root="cafe",
        chain_length=3,
        target_cadence_minutes=5.0,
    )

    assert snapshot_id == 42
    assert any(a["kind"] == "capture_gap" for a in alerts)
