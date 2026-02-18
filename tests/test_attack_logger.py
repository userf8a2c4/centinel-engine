"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `tests/test_attack_logger.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - _read_jsonl
  - test_log_http_request_classifies_flood
  - test_rotation_creates_gzip_archive
  - test_honeypot_logs_requests_via_flask_client
  - test_external_summary_uses_anonymized_ip
  - test_honeypot_default_firewall_blocks_public_ips

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `tests/test_attack_logger.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - _read_jsonl
  - test_log_http_request_classifies_flood
  - test_rotation_creates_gzip_archive
  - test_honeypot_logs_requests_via_flask_client
  - test_external_summary_uses_anonymized_ip
  - test_honeypot_default_firewall_blocks_public_ips

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
"""

from __future__ import annotations

import gzip
import json
import time
from pathlib import Path

import pytest

from core.attack_logger import AttackForensicsLogbook, AttackLogConfig, HoneypotServer


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_log_http_request_classifies_flood(tmp_path: Path) -> None:
    """English/Spanish: Burst traffic should be classified as flood."""
    cfg = AttackLogConfig(
        log_path=str(tmp_path / "attack_log.jsonl"),
        max_requests_per_ip=2,
        honeypot_enabled=False,
        flood_log_sample_ratio=1,
    )
    logbook = AttackForensicsLogbook(cfg)
    logbook.start()

    for _ in range(3):
        logbook.log_http_request(ip="10.0.0.1", method="GET", route="/debug", headers={"User-Agent": "curl/8.0"})
    time.sleep(0.1)
    logbook.stop()

    entries = _read_jsonl(tmp_path / "attack_log.jsonl")
    assert entries[-1]["classification"] == "flood"
    assert entries[-1]["frequency_count"] >= 3


def test_rotation_creates_gzip_archive(tmp_path: Path) -> None:
    """English/Spanish: Rotation should compress previous JSONL file."""
    cfg = AttackLogConfig(
        log_path=str(tmp_path / "attack_log.jsonl"),
        max_file_size_mb=1,
        rotation_interval_seconds=0,
        honeypot_enabled=False,
    )
    logbook = AttackForensicsLogbook(cfg)
    logbook.start()

    logbook.log_http_request(ip="10.0.0.2", method="GET", route="/admin", headers={"User-Agent": "sqlmap"})
    logbook.log_http_request(ip="10.0.0.2", method="GET", route="/admin2", headers={"User-Agent": "sqlmap"})
    # Allow enough time for the background writer to flush both events to disk
    # and for the rotation to trigger on the second event.
    time.sleep(0.5)
    logbook.stop()

    gz_files = list(tmp_path.glob("attack_log*.gz"))
    assert gz_files, "rotation gzip file was not created"
    with gzip.open(gz_files[0], "rt", encoding="utf-8") as fh:
        lines = [line for line in fh if line.strip()]
    assert lines, "rotated gzip archive is empty — rotation raced before flush"
    payload = json.loads(lines[0])
    assert payload["route"] == "/admin"


def test_honeypot_logs_requests_via_flask_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("flask")
    """English/Spanish: Honeypot endpoint should record request metadata."""
    cfg = AttackLogConfig(log_path=str(tmp_path / "attack_log.jsonl"), honeypot_enabled=True)
    logbook = AttackForensicsLogbook(cfg)
    honeypot = HoneypotServer(cfg, logbook)

    monkeypatch.setattr("core.attack_logger.random.choice", lambda _opts: 404)

    logbook.start()
    client = honeypot.app.test_client()
    response = client.get("/debug", headers={"User-Agent": "nmap"})
    assert response.status_code == 404
    time.sleep(0.1)
    logbook.stop()

    entries = _read_jsonl(tmp_path / "attack_log.jsonl")
    assert entries[-1]["route"] == "/debug"
    assert entries[-1]["classification"] in {"scan", "brute", "flood", "suspicious", "proxy_suspect"}


def test_external_summary_uses_anonymized_ip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """English/Spanish: External summaries should anonymize IP when configured."""
    cfg = AttackLogConfig(
        log_path=str(tmp_path / "attack_log.jsonl"),
        external_summary_enabled=True,
        external_summary_on_critical_only=False,
        webhook_url="https://example.invalid/hook",
    )
    logbook = AttackForensicsLogbook(cfg)

    captured: dict[str, dict] = {}

    def _fake_post(url: str, json: dict, timeout: int):  # noqa: A002
        captured["payload"] = json

        class _Resp:
            status_code = 200

        return _Resp()

    monkeypatch.setattr("core.attack_logger.requests.post", _fake_post)

    logbook.start()
    logbook.log_http_request(ip="198.51.100.10", method="GET", route="/x", headers={"User-Agent": "ua"})
    time.sleep(0.1)
    logbook.stop()

    assert captured["payload"]["ip"].startswith("anon-")


def test_honeypot_default_firewall_blocks_public_ips(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """English/Spanish: Honeypot default firewall should deny non-local clients.

    El firewall por defecto del honeypot debe bloquear clientes no locales.
    """
    pytest.importorskip("flask")
    cfg = AttackLogConfig(log_path=str(tmp_path / "attack_log.jsonl"), honeypot_enabled=True)
    logbook = AttackForensicsLogbook(cfg)
    honeypot = HoneypotServer(cfg, logbook)
    client = honeypot.app.test_client()
    response = client.get("/debug", environ_base={"REMOTE_ADDR": "198.51.100.50"})
    assert response.status_code == 403
