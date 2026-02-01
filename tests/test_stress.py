"""Stress tests with outage simulation and recovery checkpoints.

English:
    Stress tests for outage simulation and checkpoint recovery.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import requests

from scripts import download_and_hash


class _DummyResponse:
    def __init__(self, url: str, payload: dict) -> None:
        self.url = url
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self):  # type: ignore[override]
        return self._payload


def _make_payload() -> dict:
    """Genera payload mínimo válido para CNE.

    English:
        Build a minimal valid CNE payload.
    """
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "CNE",
        "results": {"foo": 1},
    }


def test_outage_recovery_with_checkpoint_and_retry(monkeypatch, tmp_path) -> None:
    """Simula outages y valida recuperación con checkpoint y retries.

    /** Falla en 5/19 fuentes, reintenta y recupera. / Fail 5/19 sources, retry and recover. */
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(download_and_hash, "TEMP_DIR", tmp_path / "data" / "temp")
    monkeypatch.setattr(
        download_and_hash,
        "CHECKPOINT_PATH",
        Path(tmp_path / "data" / "temp" / "download_checkpoint.json"),
    )
    download_and_hash.TEMP_DIR.mkdir(parents=True, exist_ok=True)

    sources = [
        {
            "source_id": f"S{i}",
            "endpoint": f"https://cne.hn/snapshot/{i}",
        }
        for i in range(19)
    ]
    endpoints: dict[str, str] = {}
    config = {
        "max_sources_per_cycle": 19,
        "timeout": 0.1,
        "cne_domains": ["cne.hn"],
    }

    failing_endpoints = {f"https://cne.hn/snapshot/{i}" for i in range(5)}
    attempts: dict[str, int] = {}

    def _fake_fetch(url: str, *, timeout: float, session=None):  # type: ignore[override]
        attempts[url] = attempts.get(url, 0) + 1
        if url in failing_endpoints and attempts[url] == 1:
            raise requests.ConnectionError("outage")
        return _DummyResponse(url, _make_payload())

    monkeypatch.setattr(download_and_hash, "fetch_with_retry", _fake_fetch)

    download_and_hash.process_sources(sources, endpoints, config)

    checkpoint_path = download_and_hash.CHECKPOINT_PATH
    assert checkpoint_path.exists()
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    assert len(checkpoint["processed_sources"]) == 14

    download_and_hash.process_sources(sources, endpoints, config)

    assert not checkpoint_path.exists()
    assert sum(attempts.values()) == 24
    for endpoint in failing_endpoints:
        assert attempts[endpoint] == 2

    snapshots = list((tmp_path / "data").glob("snapshot_*.json"))
    hashes = list((tmp_path / "hashes").glob("snapshot_*.sha256"))
    assert len(snapshots) == 19
    assert len(hashes) == 19
