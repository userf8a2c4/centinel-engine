"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `tests/integration/test_full_cycle.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - _setup_fake_web3
  - test_full_cycle

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `tests/integration/test_full_cycle.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - _setup_fake_web3
  - test_full_cycle

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest

from monitoring.health import get_health_state, reset_health_state
from scripts.download_and_hash import process_sources

responses = pytest.importorskip("responses")


@responses.activate
def test_full_cycle(tmp_path, monkeypatch, mocker):
    """Español: Función test_full_cycle del módulo tests/integration/test_full_cycle.py.

    English: Function test_full_cycle defined in tests/integration/test_full_cycle.py.
    """
    monkeypatch.chdir(tmp_path)
    Path("data").mkdir()
    Path("hashes").mkdir()

    endpoint = "https://cne.example/api"
    # Realistic CNE payload: recent timestamp + CNE source metadata so the
    # real-payload validator accepts it.
    cne_payload = {
        "ok": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "meta": {"source": "CNE"},
    }
    responses.add(responses.GET, endpoint, json=cne_payload, status=200)

    sources = [
        {
            "name": "Nacional",
            "source_id": "NACIONAL",
            "scope": "NATIONAL",
        }
    ]
    # Allow the synthetic test domain through the SSRF allowlist and skip
    # public-IP resolution (network is blocked in tests by conftest).
    test_config = {
        "cne_domains": ["cne.example"],
        "enforce_public_ip_resolution": False,
        "require_https": True,
    }
    process_sources(sources, {"nacional": endpoint}, test_config)

    snapshots = list(Path("data/snapshots/NACIONAL").glob("snapshot_*.json"))
    hashes = list(Path("hashes/NACIONAL").glob("snapshot_*.sha256"))
    assert snapshots
    assert hashes

    fail_requests = []

    def handler(request):
        """Español: Función handler del módulo tests/integration/test_full_cycle.py.

        English: Function handler defined in tests/integration/test_full_cycle.py.
        """
        fail_requests.append(request)
        return httpx.Response(200)

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    mocker.patch("monitoring.health.httpx.get", side_effect=client.get)
    mocker.patch("monitoring.health.httpx.post", side_effect=client.post)

    monkeypatch.setenv("HEALTHCHECKS_UUID", "test-uuid")
    reset_health_state()
    get_health_state()

    fail_endpoint = "https://cne.example/fail"
    from scripts.download_and_hash import CHECKPOINT_PATH

    for _ in range(4):
        # Each iteration simulates an independent failure cycle; clear the
        # resume checkpoint so the source isn't skipped as "already
        # processed" (checkpoint resumption was added after this test).
        if CHECKPOINT_PATH.exists():
            CHECKPOINT_PATH.unlink()
        responses.add(responses.GET, fail_endpoint, status=500)
        process_sources(sources, {"nacional": fail_endpoint}, test_config)

    assert any(req.method == "POST" and req.url.path.endswith("/fail") for req in fail_requests)

    shutil.rmtree("data")
    shutil.rmtree("hashes")
    assert not Path("data").exists()
    assert not Path("hashes").exists()
