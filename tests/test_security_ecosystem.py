"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `tests/test_security_ecosystem.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - test_attack_logbook_flood_sampling_and_callback
  - test_manager_honeypot_flood_triggers_air_gap
  - test_manager_requires_consecutive_anomalies
  - test_integrated_flow_detection_to_backup

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `tests/test_security_ecosystem.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - test_attack_logbook_flood_sampling_and_callback
  - test_manager_honeypot_flood_triggers_air_gap
  - test_manager_requires_consecutive_anomalies
  - test_integrated_flow_detection_to_backup

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
"""

from __future__ import annotations

import time
from pathlib import Path

from core.advanced_security import AdvancedSecurityConfig, AdvancedSecurityManager
from core.attack_logger import AttackForensicsLogbook, AttackLogConfig


def test_attack_logbook_flood_sampling_and_callback(tmp_path: Path) -> None:
    """Flood events should be sampled while callback still receives all events.

    Eventos flood deben muestrearse, pero el callback recibe todos.
    """
    callback_events: list[dict] = []
    cfg = AttackLogConfig(
        log_path=str(tmp_path / "attack_log.jsonl"),
        max_requests_per_ip=1,
        flood_log_sample_ratio=2,
    )
    logbook = AttackForensicsLogbook(cfg, event_callback=lambda event: callback_events.append(event))
    logbook.start()

    for _ in range(4):
        logbook.log_http_request(ip="198.51.100.3", method="GET", route="/debug", headers={"User-Agent": "ua"})

    time.sleep(0.2)
    logbook.stop()

    lines = (tmp_path / "attack_log.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(callback_events) == 4
    assert len(lines) <= 3


def test_manager_honeypot_flood_triggers_air_gap(monkeypatch) -> None:
    """Flood callback threshold should trigger air-gap.

    Umbral de flood por callback debe activar air-gap.
    """
    cfg = AdvancedSecurityConfig(honeypot_flood_trigger_count=2, honeypot_flood_window_seconds=60)
    manager = AdvancedSecurityManager(cfg)
    calls: list[str] = []
    monkeypatch.setattr(manager, "air_gap", lambda reason: calls.append(reason))

    manager.on_attack_event({"classification": "flood", "ip": "198.51.100.2"})
    manager.on_attack_event({"classification": "flood", "ip": "198.51.100.2"})

    assert calls == ["honeypot_flood_threshold"]


def test_manager_requires_consecutive_anomalies(monkeypatch) -> None:
    """Dead-man should wait for configured consecutive anomalies.

    El dead-man debe esperar el número configurado de anomalías consecutivas.
    """
    cfg = AdvancedSecurityConfig(anomaly_consecutive_limit=2)
    manager = AdvancedSecurityManager(cfg)
    calls: list[str] = []
    monkeypatch.setattr(manager, "air_gap", lambda reason: calls.append(reason))
    monkeypatch.setattr(manager, "detect_internal_anomalies", lambda: ["cpu_sustained:99.1"])

    manager.on_poll_cycle()
    manager.on_poll_cycle()

    assert len(calls) == 1


def test_integrated_flow_detection_to_backup(tmp_path: Path, monkeypatch) -> None:
    """Integrated flow should chain anomaly -> alert -> air-gap -> backup.

    El flujo integrado debe encadenar anomalía -> alerta -> air-gap -> backup.
    """
    cfg = AdvancedSecurityConfig(
        anomaly_consecutive_limit=1,
        backup_paths=[str(tmp_path / "*.json")],
        auto_backup_forensic_logs=True,
        deadman_state_path=str(tmp_path / "deadman_state.json"),
    )
    manager = AdvancedSecurityManager(cfg)
    (tmp_path / "snapshot.json").write_text('{"ok": true}', encoding="utf-8")
    calls: list[str] = []
    monkeypatch.setattr(manager, "verify_integrity", lambda: False)
    monkeypatch.setattr(manager.runtime_security, "stop_honeypot", lambda: calls.append("runtime_stop"))
    monkeypatch.setattr(manager.honeypot, "stop", lambda: calls.append("honeypot_stop"))
    monkeypatch.setattr(manager.honeypot, "start", lambda: calls.append("honeypot_start"))
    monkeypatch.setattr(manager.runtime_security, "start_honeypot", lambda: calls.append("runtime_start"))
    monkeypatch.setattr(manager, "detect_internal_anomalies", lambda: ["memory_high:95.0"])
    monkeypatch.setattr("core.advanced_security.time.sleep", lambda _seconds: None)

    manager.on_poll_cycle()

    assert "runtime_stop" in calls
    assert "honeypot_stop" in calls
    assert any(p.name.startswith("advanced_backup_") for p in (Path("data/backups")).glob("advanced_backup_*.json*"))
