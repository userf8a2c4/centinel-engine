"""Tests for integrated advanced security module.

Pruebas para módulo integrado de seguridad avanzada.
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
    contract.write_text("pragma solidity ^0.8.20; contract Vote { function x() public { tx.origin; } }", encoding="utf-8")
    cfg = AdvancedSecurityConfig(solidity_contract_paths=[str(contracts_dir / "*.sol")])
    manager = AdvancedSecurityManager(cfg)
    triggers = manager.detect_internal_anomalies()
    assert any(t.startswith("solidity_blocked_pattern") for t in triggers)
