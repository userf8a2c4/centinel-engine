"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `tests/test_collector.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - _Response
  - test_fetch_json_with_retry_recovers_after_one_failure
  - test_validate_collected_payloads_warns_when_count_is_not_96
  - test_run_collection_writes_report
  - test_is_safe_http_url_blocks_unsafe_schemes_and_credentials

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `tests/test_collector.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - _Response
  - test_fetch_json_with_retry_recovers_after_one_failure
  - test_validate_collected_payloads_warns_when_count_is_not_96
  - test_run_collection_writes_report
  - test_is_safe_http_url_blocks_unsafe_schemes_and_credentials

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
"""

from __future__ import annotations

from pathlib import Path

import requests

from scripts import collector


class _Response:
    """Simple mocked response object.

    Objeto de respuesta simulado.
    """

    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_fetch_json_with_retry_recovers_after_one_failure(monkeypatch):
    """Fetch should retry and then return JSON.

    Fetch debe reintentar y luego retornar JSON.
    """
    state = {"calls": 0}

    def fake_get(self, *args, **kwargs):
        state["calls"] += 1
        if state["calls"] == 1:
            raise requests.ConnectionError("boom")
        return _Response({"ok": True})

    monkeypatch.setattr(requests.Session, "get", fake_get)

    payload = collector.fetch_json_with_retry(
        requests.Session(),
        "https://example.test/json",
        timeout_seconds=1.0,
        max_attempts=2,
        backoff_base=0,
    )

    assert payload == {"ok": True}
    assert state["calls"] == 2




def test_fetch_json_with_retry_uses_isolated_session(monkeypatch) -> None:
    session = requests.Session()

    def _blocked_get(*_args, **_kwargs):
        raise AssertionError("shared session should not be used")

    monkeypatch.setattr(session, "get", _blocked_get)
    monkeypatch.setattr(requests.Session, "get", lambda self, *a, **k: _Response({"ok": True}))

    payload = collector.fetch_json_with_retry(
        session,
        "https://cne.hn/api",
        timeout_seconds=1,
        max_attempts=1,
        backoff_base=0,
    )

    assert payload == {"ok": True}


def test_validate_collected_payloads_warns_when_count_is_not_96(caplog):
    """Validation logs mismatch if expected count is not met.

    La validación registra mismatch si no se cumple el conteo esperado.
    """
    valid_payload = {
        "meta": {
            "election": "general",
            "year": 2025,
            "source": "cne",
            "scope": "national",
            "department_code": "01",
            "timestamp_utc": "2025-01-01T00:00:00Z",
        },
        "totals": {
            "registered_voters": 100,
            "total_votes": 50,
            "valid_votes": 45,
            "null_votes": 3,
            "blank_votes": 2,
        },
        "candidates": [{"slot": 0, "votes": 30}],
    }

    with caplog.at_level("WARNING"):
        valid, invalid = collector.validate_collected_payloads([valid_payload], expected_count=96)

    assert len(valid) == 1
    assert invalid == 0
    assert "collector_expected_count_mismatch" in caplog.text


def test_run_collection_writes_report(tmp_path: Path, monkeypatch):
    """run_collection should write a report even with empty sources.

    run_collection debe escribir un reporte incluso con fuentes vacías.
    """
    config_path = tmp_path / "config.yaml"
    retry_path = tmp_path / "retry.yaml"
    config_path.write_text("sources: []\nexpected_json_count: 96\n", encoding="utf-8")
    retry_path.write_text("default:\n  max_attempts: 1\ntimeout_seconds: 1\n", encoding="utf-8")

    output_path = tmp_path / "collector_latest.json"
    monkeypatch.setattr(collector, "DEFAULT_OUTPUT_PATH", output_path)

    class _Rotator:
        def get_proxy_for_request(self):
            return None

        def mark_success(self, _proxy):
            return None

        def mark_failure(self, _proxy, _reason):
            return None

    monkeypatch.setattr(collector, "get_proxy_rotator", lambda _logger: _Rotator())

    code = collector.run_collection(config_path=config_path, retry_path=retry_path)

    assert code == 0
    assert output_path.exists()


def test_is_safe_http_url_blocks_unsafe_schemes_and_credentials():
    """English: URL validator blocks unsafe schemes and credentials. Español: bloquea esquemas inseguros y credenciales."""
    assert collector.is_safe_http_url("https://cne.example/api")
    assert not collector.is_safe_http_url("file:///etc/passwd")
    assert not collector.is_safe_http_url("https://user:pass@example.com/private")


def test_is_safe_http_url_enforces_allowed_domains() -> None:
    assert collector.is_safe_http_url("https://cne.hn/api", allowed_domains={"cne.hn"})
    assert not collector.is_safe_http_url("https://evil.example/api", allowed_domains={"cne.hn"})


def test_is_safe_http_url_supports_public_resolution_flag(monkeypatch) -> None:
    captured = {"enforce": None}

    def _fake_is_safe(url: str, **kwargs):
        captured["enforce"] = kwargs.get("enforce_public_ip_resolution")
        return True

    monkeypatch.setattr(collector, "is_safe_outbound_url", _fake_is_safe)
    assert collector.is_safe_http_url("https://cne.hn/api", enforce_public_ip_resolution=True)
    assert captured["enforce"] is True


def test_fetch_json_with_retry_uses_dns_pinning_and_connection_close(monkeypatch) -> None:
    called = {"pin": 0, "conn": None}

    class _Target:
        pass

    def _fake_get(self, *_args, **kwargs):
        called["conn"] = kwargs["headers"].get("Connection")
        return _Response({"ok": True})

    class _Ctx:
        def __enter__(self):
            called["pin"] += 1
            return None

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(requests.Session, "get", _fake_get)
    monkeypatch.setattr(collector, "resolve_outbound_target", lambda *a, **k: _Target())
    monkeypatch.setattr(collector, "pin_dns_resolution", lambda _target: _Ctx())

    payload = collector.fetch_json_with_retry(
        requests.Session(),
        "https://cne.hn/api",
        timeout_seconds=1,
        max_attempts=1,
        backoff_base=0,
        enforce_public_ip_resolution=True,
    )

    assert payload == {"ok": True}
    assert called["pin"] == 1
    assert called["conn"] == "close"
