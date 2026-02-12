"""Chaos-style tests for security orchestration.

Pruebas tipo chaos para orquestación de seguridad.
"""

from __future__ import annotations

from pathlib import Path

from core.advanced_security import AdvancedSecurityConfig, AdvancedSecurityManager


def test_chaos_simulated_ddos_generates_single_air_gap(monkeypatch) -> None:
    """Simulated DDoS bursts should converge into one air-gap decision.

    Ráfagas DDoS simuladas deben converger en una sola decisión de air-gap.
    """
    manager = AdvancedSecurityManager(
        AdvancedSecurityConfig(honeypot_flood_trigger_count=3, honeypot_flood_window_seconds=60)
    )
    calls: list[str] = []
    monkeypatch.setattr(manager, "air_gap", lambda reason: calls.append(reason))

    for _ in range(6):
        manager.on_attack_event({"classification": "flood", "ip": "198.51.100.80"})

    assert calls == ["honeypot_flood_threshold", "honeypot_flood_threshold"]


def test_chaos_integrity_tampering_detected(tmp_path: Path) -> None:
    """Unexpected file creation should be captured as integrity anomaly.

    Creación inesperada de archivo debe capturarse como anomalía de integridad.
    """
    manager = AdvancedSecurityManager(AdvancedSecurityConfig(integrity_paths=[str(tmp_path / "*.py")]))
    (tmp_path / "tampered.py").write_text("print('tamper')", encoding="utf-8")

    triggers = manager.detect_internal_anomalies()

    assert "new_file_detected" in triggers
