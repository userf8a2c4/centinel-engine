"""Pruebas de integración del ciclo completo de descarga y anclaje.

Integration tests for the full download and anchoring cycle.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from anchor.arbitrum_anchor import anchor_batch
from monitoring.health import get_health_state, reset_health_state
from scripts.download_and_hash import process_sources

responses = pytest.importorskip("responses")


def _setup_fake_web3(mocker):
    """Español: Función _setup_fake_web3 del módulo tests/integration/test_full_cycle.py.

    English: Function _setup_fake_web3 defined in tests/integration/test_full_cycle.py.
    """

    class FakeAnchorFn:
        """Español: Clase FakeAnchorFn del módulo tests/integration/test_full_cycle.py.

        English: FakeAnchorFn class defined in tests/integration/test_full_cycle.py.
        """

        def build_transaction(self, params):
            """Español: Función build_transaction del módulo tests/integration/test_full_cycle.py.

            English: Function build_transaction defined in tests/integration/test_full_cycle.py.
            """
            return dict(params)

        def estimate_gas(self, params):
            """Español: Función estimate_gas del módulo tests/integration/test_full_cycle.py.

            English: Function estimate_gas defined in tests/integration/test_full_cycle.py.
            """
            return 21_000

    class FakeContract:
        """Español: Clase FakeContract del módulo tests/integration/test_full_cycle.py.

        English: FakeContract class defined in tests/integration/test_full_cycle.py.
        """

        def __init__(self):
            """Español: Función __init__ del módulo tests/integration/test_full_cycle.py.

            English: Function __init__ defined in tests/integration/test_full_cycle.py.
            """
            self.functions = SimpleNamespace(anchor=lambda _: FakeAnchorFn())

    class FakeEth:
        """Español: Clase FakeEth del módulo tests/integration/test_full_cycle.py.

        English: FakeEth class defined in tests/integration/test_full_cycle.py.
        """

        chain_id = 1
        gas_price = 1

        def contract(self, address, abi):  # noqa: ARG002
            """Español: Función contract del módulo tests/integration/test_full_cycle.py.

            English: Function contract defined in tests/integration/test_full_cycle.py.
            """
            return FakeContract()

        def get_transaction_count(self, address):  # noqa: ARG002
            """Español: Función get_transaction_count del módulo tests/integration/test_full_cycle.py.

            English: Function get_transaction_count defined in tests/integration/test_full_cycle.py.
            """
            return 1

        def send_raw_transaction(self, raw_tx):  # noqa: ARG002
            """Español: Función send_raw_transaction del módulo tests/integration/test_full_cycle.py.

            English: Function send_raw_transaction defined in tests/integration/test_full_cycle.py.
            """
            return b"\x12"

    class FakeWeb3:
        """Español: Clase FakeWeb3 del módulo tests/integration/test_full_cycle.py.

        English: FakeWeb3 class defined in tests/integration/test_full_cycle.py.
        """

        eth = FakeEth()

        def is_connected(self):
            """Español: Función is_connected del módulo tests/integration/test_full_cycle.py.

            English: Function is_connected defined in tests/integration/test_full_cycle.py.
            """
            return True

        def to_checksum_address(self, address):
            """Español: Función to_checksum_address del módulo tests/integration/test_full_cycle.py.

            English: Function to_checksum_address defined in tests/integration/test_full_cycle.py.
            """
            return address

        def to_bytes(self, hexstr):
            """Español: Función to_bytes del módulo tests/integration/test_full_cycle.py.

            English: Function to_bytes defined in tests/integration/test_full_cycle.py.
            """
            return bytes.fromhex(hexstr.replace("0x", ""))

        def to_hex(self, value):  # noqa: ARG002
            """Español: Función to_hex del módulo tests/integration/test_full_cycle.py.

            English: Function to_hex defined in tests/integration/test_full_cycle.py.
            """
            return "0xabc"

    mocker.patch("anchor.arbitrum_anchor._build_web3_client", return_value=FakeWeb3())
    mocker.patch(
        "anchor.arbitrum_anchor._load_arbitrum_settings",
        return_value={
            "enabled": True,
            "rpc_url": "https://arb.example/rpc",
            "private_key": "0x" + "1" * 64,
            "contract_address": "0x" + "2" * 40,
        },
    )
    mocker.patch(
        "anchor.arbitrum_anchor.Account.from_key",
        return_value=SimpleNamespace(address="0xabc"),
    )
    mocker.patch(
        "anchor.arbitrum_anchor.Account.sign_transaction",
        return_value=SimpleNamespace(rawTransaction=b"\x01"),
    )


@responses.activate
def test_full_cycle(tmp_path, monkeypatch, mocker):
    """Español: Función test_full_cycle del módulo tests/integration/test_full_cycle.py.

    English: Function test_full_cycle defined in tests/integration/test_full_cycle.py.
    """
    monkeypatch.chdir(tmp_path)
    Path("data").mkdir()
    Path("hashes").mkdir()

    endpoint = "https://cne.example/api"
    responses.add(responses.GET, endpoint, json={"ok": True}, status=200)

    sources = [
        {
            "name": "Nacional",
            "source_id": "NACIONAL",
            "scope": "NATIONAL",
        }
    ]
    process_sources(sources, {"nacional": endpoint})

    snapshots = list(Path("data/snapshots/NACIONAL").glob("snapshot_*.json"))
    hashes = list(Path("hashes/NACIONAL").glob("snapshot_*.sha256"))
    assert snapshots
    assert hashes

    hash_payload = json.loads(hashes[0].read_text(encoding="utf-8"))
    _setup_fake_web3(mocker)
    result = anchor_batch([hash_payload["hash"]])
    assert result["tx_hash"].startswith("0x")

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
    for _ in range(4):
        responses.add(responses.GET, fail_endpoint, status=500)
        process_sources(sources, {"nacional": fail_endpoint})

    assert any(req.method == "POST" and req.url.path.endswith("/fail") for req in fail_requests)

    shutil.rmtree("data")
    shutil.rmtree("hashes")
    assert not Path("data").exists()
    assert not Path("hashes").exists()
