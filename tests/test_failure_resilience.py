"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `tests/test_failure_resilience.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - _DummyResponse
  - test_process_sources_handles_connection_error
  - test_healthcheck_returns_false_on_failures
  - test_process_sources_saves_snapshot

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `tests/test_failure_resilience.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - _DummyResponse
  - test_process_sources_handles_connection_error
  - test_healthcheck_returns_false_on_failures
  - test_process_sources_saves_snapshot

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import requests

from scripts import download_and_hash
from scripts.healthcheck import check_cne_endpoints


class _DummyResponse:
    """Español: Clase _DummyResponse del módulo tests/test_failure_resilience.py.

    English: _DummyResponse class defined in tests/test_failure_resilience.py.
    """

    def __init__(self, url: str, payload: dict) -> None:
        """Español: Función __init__ del módulo tests/test_failure_resilience.py.

        English: Function __init__ defined in tests/test_failure_resilience.py.
        """
        self.url = url
        self._payload = payload

    def raise_for_status(self) -> None:
        """Español: Función raise_for_status del módulo tests/test_failure_resilience.py.

        English: Function raise_for_status defined in tests/test_failure_resilience.py.
        """
        return None

    def json(self):  # type: ignore[override]
        """Español: Función json del módulo tests/test_failure_resilience.py.

        English: Function json defined in tests/test_failure_resilience.py.
        """
        return self._payload


def test_process_sources_handles_connection_error(monkeypatch, tmp_path) -> None:
    """Español: Función test_process_sources_handles_connection_error del módulo tests/test_failure_resilience.py.

    English: Function test_process_sources_handles_connection_error defined in tests/test_failure_resilience.py.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        download_and_hash,
        "CHECKPOINT_PATH",
        Path(tmp_path / "download_checkpoint.json"),
    )

    def _raise_error(*_args, **_kwargs):
        """Español: Función _raise_error del módulo tests/test_failure_resilience.py.

        English: Function _raise_error defined in tests/test_failure_resilience.py.
        """
        raise requests.ConnectionError("network down")

    monkeypatch.setattr(download_and_hash, "request_json_with_retry", _raise_error)

    sources = [{"source_id": "NACIONAL", "endpoint": "https://cne.hn/nacional"}]
    config = {"max_sources_per_cycle": 1}
    download_and_hash.process_sources(sources, {}, config)

    assert not (tmp_path / "download_checkpoint.json").exists()


def test_healthcheck_returns_false_on_failures(monkeypatch) -> None:
    """Español: Función test_healthcheck_returns_false_on_failures del módulo tests/test_failure_resilience.py.

    English: Function test_healthcheck_returns_false_on_failures defined in tests/test_failure_resilience.py.
    """

    def _fail(*_args, **_kwargs):
        """Español: Función _fail del módulo tests/test_failure_resilience.py.

        English: Function _fail defined in tests/test_failure_resilience.py.
        """
        raise requests.ConnectionError("offline")

    monkeypatch.setattr(requests.Session, "get", _fail)
    config = {
        "endpoints": {"nacional": "https://cne.hn/nacional"},
        "sources": [{"scope": "NATIONAL"}],
        "max_sources_per_cycle": 1,
    }

    assert check_cne_endpoints(config) is False


def test_process_sources_saves_snapshot(monkeypatch, tmp_path) -> None:
    """Español: Función test_process_sources_saves_snapshot del módulo tests/test_failure_resilience.py.

    English: Function test_process_sources_saves_snapshot defined in tests/test_failure_resilience.py.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        download_and_hash,
        "CHECKPOINT_PATH",
        Path(tmp_path / "download_checkpoint.json"),
    )

    response = _DummyResponse(
        "https://cne.hn/nacional",
        {"timestamp": datetime.now(timezone.utc).isoformat(), "source": "CNE"},
    )

    monkeypatch.setattr(
        download_and_hash,
        "request_json_with_retry",
        lambda *_args, **_kwargs: (response, response.json()),
    )

    sources = [{"source_id": "NACIONAL", "endpoint": "https://cne.hn/nacional"}]
    config = {"max_sources_per_cycle": 1}
    download_and_hash.process_sources(sources, {}, config)

    snapshots = list((tmp_path / "data" / "snapshots" / "NACIONAL").glob("snapshot_*.json"))
    hashes = list((tmp_path / "hashes" / "NACIONAL").glob("snapshot_*.sha256"))
    assert snapshots
    assert hashes
