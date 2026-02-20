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
  - test_identity_rotator_uses_configured_user_agents
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
  - test_identity_rotator_uses_configured_user_agents
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


def test_identity_rotator_uses_configured_user_agents(tmp_path: Path) -> None:
    cfg = AdvancedSecurityConfig(
        user_agents_list=[
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0",
        ]
    )
    manager = AdvancedSecurityManager(cfg)
    headers, _ = manager.get_request_profile()
    assert headers["User-Agent"] in cfg.user_agents_list


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


def test_air_gap_is_rate_limited(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    cfg = AdvancedSecurityConfig(
        deadman_min_interval_seconds=600,
        deadman_state_path=str(tmp_path / "deadman_state.json"),
    )
    manager = AdvancedSecurityManager(cfg)
    calls: list[tuple[int, str]] = []
    monkeypatch.setattr(manager, "verify_integrity", lambda: False)
    monkeypatch.setattr("core.advanced_security.time.sleep", lambda _s: None)
    monkeypatch.setattr(manager, "_safe_alert", lambda level, event, metrics: calls.append((level, event)))

    manager.air_gap("flood")
    manager.air_gap("flood")

    assert (3, "air_gap_enter") in calls
    assert (1, "air_gap_rate_limited") in calls


def test_backup_github_requires_allowlist(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    cfg = AdvancedSecurityConfig(backup_provider="github")
    manager = AdvancedSecurityManager(cfg)
    archive = tmp_path / "backup.json"
    archive.write_text("{}", encoding="utf-8")

    monkeypatch.setenv("BACKUP_GIT_REPO", "origin")
    monkeypatch.delenv("BACKUP_GIT_REMOTE_ALLOWLIST", raising=False)

    called = {"run": 0}

    def _fake_run(*_args, **_kwargs):
        called["run"] += 1
        return None

    monkeypatch.setattr("core.advanced_security.subprocess.run", _fake_run)
    manager.backups._upload(archive)
    assert called["run"] == 0




def test_backup_github_resolves_remote_url_before_allowlist(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    cfg = AdvancedSecurityConfig(backup_provider="github")
    manager = AdvancedSecurityManager(cfg)
    archive = tmp_path / "backup.json"
    archive.write_text("{}", encoding="utf-8")

    monkeypatch.setenv("BACKUP_GIT_REPO", "origin")
    monkeypatch.setenv("BACKUP_GIT_REMOTE_ALLOWLIST", "https://github.com/trusted/repo.git")
    monkeypatch.setattr(
        "core.advanced_security.subprocess.check_output",
        lambda *_args, **_kwargs: "https://github.com/trusted/repo.git\n",
    )

    calls: list[list[str]] = []

    def _fake_run(args, **_kwargs):
        calls.append(args)
        return None

    monkeypatch.setattr("core.advanced_security.subprocess.run", _fake_run)
    manager.backups._upload(archive)

    assert ["git", "push", "origin"] in calls


def test_backup_github_blocks_remote_alias_when_url_not_allowlisted(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cfg = AdvancedSecurityConfig(backup_provider="github")
    manager = AdvancedSecurityManager(cfg)
    archive = tmp_path / "backup.json"
    archive.write_text("{}", encoding="utf-8")

    monkeypatch.setenv("BACKUP_GIT_REPO", "origin")
    monkeypatch.setenv("BACKUP_GIT_REMOTE_ALLOWLIST", "https://github.com/trusted/repo.git")
    monkeypatch.setattr(
        "core.advanced_security.subprocess.check_output",
        lambda *_args, **_kwargs: "https://evil.example/repo.git\n",
    )

    called = {"run": 0}

    def _fake_run(*_args, **_kwargs):
        called["run"] += 1
        return None

    monkeypatch.setattr("core.advanced_security.subprocess.run", _fake_run)
    manager.backups._upload(archive)

    assert called["run"] == 0

def test_air_gap_rate_limit_persists_across_restarts(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    cfg = AdvancedSecurityConfig(
        deadman_min_interval_seconds=600,
        deadman_state_path=str(tmp_path / "deadman_state.json"),
    )
    monkeypatch.setattr("core.advanced_security.time.sleep", lambda _s: None)

    manager = AdvancedSecurityManager(cfg)
    monkeypatch.setattr(manager, "verify_integrity", lambda: False)
    monkeypatch.setattr(manager, "_safe_alert", lambda *_args, **_kwargs: None)
    manager.air_gap("flood")

    manager2 = AdvancedSecurityManager(cfg)
    calls: list[tuple[int, str]] = []
    monkeypatch.setattr(manager2, "verify_integrity", lambda: False)
    monkeypatch.setattr(manager2, "_safe_alert", lambda level, event, metrics: calls.append((level, event)))
    manager2.air_gap("flood")

    assert (1, "air_gap_rate_limited") in calls
