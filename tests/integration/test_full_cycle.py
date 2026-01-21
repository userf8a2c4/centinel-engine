from __future__ import annotations

import json
import shutil
from pathlib import Path
from types import SimpleNamespace

import httpx
import responses

from anchor.arbitrum_anchor import anchor_batch
from monitoring.health import get_health_state, reset_health_state
from scripts.download_and_hash import process_sources


def _setup_fake_web3(mocker):
    class FakeAnchorFn:
        def build_transaction(self, params):
            return dict(params)

        def estimate_gas(self, params):
            return 21_000

    class FakeContract:
        def __init__(self):
            self.functions = SimpleNamespace(anchor=lambda _: FakeAnchorFn())

    class FakeEth:
        chain_id = 1
        gas_price = 1

        def contract(self, address, abi):  # noqa: ARG002
            return FakeContract()

        def get_transaction_count(self, address):  # noqa: ARG002
            return 1

        def send_raw_transaction(self, raw_tx):  # noqa: ARG002
            return b"\x12"

    class FakeWeb3:
        eth = FakeEth()

        def is_connected(self):
            return True

        def to_checksum_address(self, address):
            return address

        def to_bytes(self, hexstr):
            return bytes.fromhex(hexstr.replace("0x", ""))

        def to_hex(self, value):  # noqa: ARG002
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

    snapshots = list(Path("data").glob("snapshot_*.json"))
    hashes = list(Path("hashes").glob("snapshot_*.sha256"))
    assert snapshots
    assert hashes

    hash_payload = json.loads(hashes[0].read_text(encoding="utf-8"))
    _setup_fake_web3(mocker)
    result = anchor_batch([hash_payload["hash"]])
    assert result["tx_hash"].startswith("0x")

    fail_requests = []

    def handler(request):
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

    assert any(
        req.method == "POST" and req.url.path.endswith("/fail")
        for req in fail_requests
    )

    shutil.rmtree("data")
    shutil.rmtree("hashes")
    assert not Path("data").exists()
    assert not Path("hashes").exists()
