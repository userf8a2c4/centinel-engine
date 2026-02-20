"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `tests/test_advanced_security.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - test_identity_rotator_uses_v1_user_agents
  - test_honeypot_logs_request_metadata
  - test_alert_level_1_does_not_call_external
  - test_detect_internal_anomalies_new_file
  - test_adaptive_cpu_ignores_brief_spike
  - test_solidity_runtime_checks_detect_blocked_pattern
  - test_honeypot_encrypts_events_file

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `tests/test_advanced_security.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - test_identity_rotator_uses_v1_user_agents
  - test_honeypot_logs_request_metadata
  - test_alert_level_1_does_not_call_external
  - test_detect_internal_anomalies_new_file
  - test_adaptive_cpu_ignores_brief_spike
  - test_solidity_runtime_checks_detect_blocked_pattern
  - test_honeypot_encrypts_events_file

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.advanced_security import (
    AdvancedSecurityConfig,
    AdvancedSecurityManager,
    AlertManager,
    HoneypotService,
)


def test_identity_rotator_uses_v1_user_agents(tmp_path: Path) -> None:
    cfg = AdvancedSecurityConfig(
        user_agents_list=[
            "Mozilla/5.0 (compatible; Centinel-Engine/1.0)",
            "Centinel-AuditoriaHN/1.0 bot",
        ]
    )
    manager = AdvancedSecurityManager(cfg)
    headers, _ = manager.get_request_profile()
    assert "/1.0" in headers["User-Agent"]


def test_honeypot_logs_request_metadata(tmp_path: Path) -> None:
    pytest.importorskip("flask")
    cfg = AdvancedSecurityConfig(honeypot_enabled=True, honeypot_endpoints=["/admin"])
    honeypot = HoneypotService(cfg)
    honeypot.events_path = tmp_path / "honeypot.jsonl"
    client = honeypot.app.test_client()
    response = client.get("/admin", headers={"User-Agent": "scanner"})
    assert response.status_code in {403, 404, 500}
    payload = json.loads(honeypot.events_path.read_text(encoding="utf-8").strip())
    assert payload["route"] == "/admin"
    assert payload["user_agent"] == "scanner"


def test_alert_level_1_does_not_call_external(monkeypatch: pytest.MonkeyPatch) -> None:
    manager = AlertManager()
    called = {"email": 0, "tg": 0}

    monkeypatch.setattr(manager, "_send_email", lambda payload: called.__setitem__("email", called["email"] + 1))
    monkeypatch.setattr(manager, "_send_telegram", lambda payload: called.__setitem__("tg", called["tg"] + 1) or True)

    manager.send(1, "minor_event")
    assert called == {"email": 0, "tg": 0}


def test_detect_internal_anomalies_new_file(tmp_path: Path) -> None:
    cfg = AdvancedSecurityConfig(integrity_paths=[str(tmp_path / "*.py")])
    manager = AdvancedSecurityManager(cfg)
    (tmp_path / "new.py").write_text("print('x')", encoding="utf-8")
    triggers = manager.detect_internal_anomalies()
    assert "new_file_detected" in triggers


def test_adaptive_cpu_ignores_brief_spike(monkeypatch: pytest.MonkeyPatch) -> None:
    """English/Spanish: brief CPU spikes should not immediately trigger dead-man.

    Picos breves de CPU no deben disparar inmediatamente el dead-man.
    """
    cfg = AdvancedSecurityConfig(cpu_threshold_percent=20, cpu_sustain_seconds=60, cpu_spike_grace_seconds=5)
    manager = AdvancedSecurityManager(cfg)
    monkeypatch.setattr("core.advanced_security.psutil.cpu_percent", lambda interval=0.1: 95.0)
    monkeypatch.setattr("core.advanced_security.psutil.virtual_memory", lambda: type("vm", (), {"percent": 10.0})())
    monkeypatch.setattr(manager.runtime_security, "detect_hostile_conditions", lambda: [])

    triggers = manager.detect_internal_anomalies()

    assert "cpu_sustained:95.0" not in triggers


def test_solidity_runtime_checks_detect_blocked_pattern(tmp_path: Path) -> None:
    """English/Spanish: runtime check should detect risky Solidity primitives.

    El chequeo runtime debe detectar primitivas riesgosas en Solidity.
    """
    contracts_dir = tmp_path / "contracts"
    contracts_dir.mkdir(parents=True)
    contract = contracts_dir / "Vote.sol"
    contract.write_text(
        "pragma solidity ^0.8.20; contract Vote { function x() public { tx.origin; } }", encoding="utf-8"
    )
    cfg = AdvancedSecurityConfig(solidity_contract_paths=[str(contracts_dir / "*.sol")])
    manager = AdvancedSecurityManager(cfg)
    triggers = manager.detect_internal_anomalies()
    assert any(t.startswith("solidity_blocked_pattern") for t in triggers)


def test_honeypot_encrypts_events_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    pytest.importorskip("flask")

    class FakeFernet:
        def __init__(self, key: bytes) -> None:
            self.key = key

        def encrypt(self, data: bytes) -> bytes:
            return b"enc:" + data[::-1]

    monkeypatch.setenv("HONEYPOT_LOG_KEY", "unit-test-key")
    monkeypatch.setattr("core.advanced_security.Fernet", FakeFernet)

    cfg = AdvancedSecurityConfig(
        honeypot_enabled=True,
        honeypot_endpoints=["/admin"],
        honeypot_encrypt_events=True,
        honeypot_events_path=str(tmp_path / "honeypot.enc"),
    )
    honeypot = HoneypotService(cfg)
    client = honeypot.app.test_client()
    response = client.get("/admin", headers={"User-Agent": "scanner"})

    assert response.status_code in {403, 404, 500}
    raw_line = honeypot.events_path.read_text(encoding="utf-8").strip()
    assert raw_line.startswith("enc:")
    assert "/admin" not in raw_line


def test_honeypot_encrypt_requires_key(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    pytest.importorskip("flask")
    monkeypatch.delenv("HONEYPOT_LOG_KEY", raising=False)

    cfg = AdvancedSecurityConfig(
        honeypot_enabled=True,
        honeypot_endpoints=["/admin"],
        honeypot_encrypt_events=True,
        honeypot_events_path=str(tmp_path / "honeypot.enc"),
    )
    with pytest.raises(RuntimeError, match="honeypot_encrypt_key_missing"):
        HoneypotService(cfg)


def test_air_gap_is_rate_limited(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = AdvancedSecurityConfig(deadman_min_interval_seconds=600)
    manager = AdvancedSecurityManager(cfg)
    calls: list[tuple[int, str]] = []
    monkeypatch.setattr(manager, "verify_integrity", lambda: False)
    monkeypatch.setattr("core.advanced_security.time.sleep", lambda _s: None)
    monkeypatch.setattr(manager, "_safe_alert", lambda level, event, metrics: calls.append((level, event)))

    manager.air_gap("flood")
    manager.air_gap("flood")

    assert (3, "air_gap_enter") in calls
    assert (1, "air_gap_rate_limited") in calls
