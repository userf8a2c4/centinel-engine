"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `tests/test_security.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - _Mem
  - test_detect_hostile_by_memory_and_http
  - test_activate_defensive_mode_persists_state
  - test_supervisor_sends_alert_after_max_retries
  - test_collector_rejects_unsafe_urls
  - test_hash_manifest_skips_symlink

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `tests/test_security.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - _Mem
  - test_detect_hostile_by_memory_and_http
  - test_activate_defensive_mode_persists_state
  - test_supervisor_sends_alert_after_max_retries
  - test_collector_rejects_unsafe_urls
  - test_hash_manifest_skips_symlink

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

pytest.importorskip("psutil")

from core import security
from core.security import DefensiveSecurityManager, DefensiveShutdown, SecurityConfig
from scripts import supervisor


class _Mem:
    def __init__(self, percent: float) -> None:
        self.percent = percent


def test_detect_hostile_by_memory_and_http(monkeypatch: pytest.MonkeyPatch) -> None:
    """English/Spanish: Memory + HTTP flood should trigger hostile detection."""
    cfg = SecurityConfig(memory_threshold_percent=80, http_errors_limit=1)
    manager = DefensiveSecurityManager(cfg)

    monkeypatch.setattr(security.psutil, "cpu_percent", lambda interval=0.1: 10.0)
    monkeypatch.setattr(security.psutil, "virtual_memory", lambda: _Mem(91.0))
    monkeypatch.setattr(security.psutil, "net_connections", lambda kind="inet": [])

    manager.record_http_error(timeout=True)
    manager.record_http_error(status_code=429)
    triggers = manager.detect_hostile_conditions()

    assert any(t.startswith("memory_high") for t in triggers)
    assert "http_errors_flood" in triggers


def test_activate_defensive_mode_persists_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """English/Spanish: Defensive activation must write flag + state artifacts."""
    safe_dir = tmp_path / "safe"
    flag = safe_dir / "defensive.flag"
    cfg = SecurityConfig(safe_state_dir=str(safe_dir), defensive_flag_file=str(flag))
    manager = DefensiveSecurityManager(cfg)

    monkeypatch.setattr(security.psutil, "cpu_percent", lambda interval=0.1: 12.0)
    monkeypatch.setattr(security.psutil, "virtual_memory", lambda: _Mem(20.0))
    monkeypatch.setattr(security.psutil, "net_connections", lambda kind="inet": [])

    with pytest.raises(DefensiveShutdown):
        manager.activate_defensive_mode(["signal_SIGTERM"], snapshot_state={"k": "v"})

    assert flag.exists()
    payload = json.loads(flag.read_text(encoding="utf-8"))
    state_dir = Path(payload["state_dir"])
    assert (state_dir / "health.json").exists()
    assert (state_dir / "state_snapshot.json").exists()


def test_supervisor_sends_alert_after_max_retries(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """English/Spanish: Supervisor should send admin alert after bounded failed retries."""
    logger = logging.getLogger("test.supervisor")
    cfg = SecurityConfig(
        max_restart_attempts=2,
        cooldown_min_minutes=0,
        cooldown_max_minutes=0,
        defensive_flag_file=str(tmp_path / "defensive.flag"),
    )

    monkeypatch.setattr(supervisor, "CONFIG_PATH", tmp_path / "security_config.yaml")
    monkeypatch.setattr(supervisor.SecurityConfig, "from_yaml", classmethod(lambda cls, path: cfg))

    class _Proc:
        returncode = 1

    monkeypatch.setattr(supervisor.subprocess, "run", lambda *a, **k: _Proc())
    monkeypatch.setattr(supervisor, "_host_still_hostile", lambda _cfg: False)
    monkeypatch.setattr(supervisor, "random_cooldown_seconds", lambda *a, **k: 0)
    monkeypatch.setattr(supervisor.time, "sleep", lambda _s: None)

    called = {"alert": 0}

    def _fake_alert(**kwargs):
        called["alert"] += 1

    monkeypatch.setattr(supervisor, "send_admin_alert", _fake_alert)

    code = supervisor.run_supervisor(["python", "scripts/run_pipeline.py"], logger)
    assert code == 1
    assert called["alert"] == 1


def test_collector_rejects_unsafe_urls() -> None:
    """English: unsafe URL schemes must be rejected. Español: se rechazan esquemas inseguros."""
    from scripts.collector import is_safe_http_url

    assert is_safe_http_url("https://cne.example/api")
    assert not is_safe_http_url("file:///etc/passwd")
    assert not is_safe_http_url("ftp://example.com/data")
    assert not is_safe_http_url("https://user:pass@example.com/secret")


def test_hash_manifest_skips_symlink(tmp_path: Path) -> None:
    """English: symlink snapshots are excluded from manifest. Español: se excluyen symlinks del manifiesto."""
    from scripts.hash import build_manifest

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    source_dir = data_dir / "snapshots" / "test_source"
    source_dir.mkdir(parents=True)
    real_file = source_dir / "snapshot_a.json"
    real_file.write_text('{"ok": true}', encoding="utf-8")
    # English/Spanish: symlink candidate should be ignored for safety / el symlink debe ignorarse por seguridad.
    (source_dir / "snapshot_b.json").symlink_to(real_file)

    manifest = build_manifest(data_dir)
    names = {entry["file"] for entry in manifest}
    assert any("snapshot_a.json" in f for f in names)
    assert not any("snapshot_b.json" in f for f in names)
