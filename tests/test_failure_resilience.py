"""Tests de resiliencia ante fallos de red.

English:
    Resilience tests for network failure scenarios.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
import requests

from scripts import download_and_hash
from scripts.healthcheck import check_cne_endpoints


class _DummyResponse:
    def __init__(self, url: str, payload: dict) -> None:
        self.url = url
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self):  # type: ignore[override]
        return self._payload


def test_process_sources_handles_connection_error(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        download_and_hash,
        "CHECKPOINT_PATH",
        Path(tmp_path / "download_checkpoint.json"),
    )

    def _raise_error(*_args, **_kwargs):
        raise requests.ConnectionError("network down")

    monkeypatch.setattr(download_and_hash, "fetch_with_retry", _raise_error)

    sources = [{"source_id": "NACIONAL", "endpoint": "https://cne.hn/nacional"}]
    config = {"max_sources_per_cycle": 1}
    download_and_hash.process_sources(sources, {}, config)

    assert not (tmp_path / "download_checkpoint.json").exists()


def test_healthcheck_returns_false_on_failures(monkeypatch) -> None:
    def _fail(*_args, **_kwargs):
        raise requests.ConnectionError("offline")

    monkeypatch.setattr(requests.Session, "get", _fail)
    config = {
        "endpoints": {"nacional": "https://cne.hn/nacional"},
        "sources": [{"scope": "NATIONAL"}],
        "max_sources_per_cycle": 1,
    }

    assert check_cne_endpoints(config) is False


def test_process_sources_saves_snapshot(monkeypatch, tmp_path) -> None:
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
        "fetch_with_retry",
        lambda *_args, **_kwargs: response,
    )

    sources = [{"source_id": "NACIONAL", "endpoint": "https://cne.hn/nacional"}]
    config = {"max_sources_per_cycle": 1}
    download_and_hash.process_sources(sources, {}, config)

    snapshots = list((tmp_path / "data").glob("snapshot_*.json"))
    hashes = list((tmp_path / "hashes").glob("snapshot_*.sha256"))
    assert snapshots
    assert hashes
