"""Pruebas para la cadena de custodia verificable — FASE 2.

Tests for the verifiable custody chain — PHASE 2.
"""

import hashlib
import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sentinel.core.custody import (
    ChainVerificationResult,
    SignatureResult,
    StartupVerificationReport,
    _compute_expected_hash,
    generate_operator_keypair,
    run_startup_verification,
    sign_hash_record,
    sign_snapshot,
    verify_chain,
    verify_chain_from_entries,
    verify_hash_record_signature,
    verify_snapshot_signature,
)


# ---------------------------------------------------------------------------
# verify_chain tests
# ---------------------------------------------------------------------------

class TestVerifyChain:
    """Pruebas de verify_chain."""

    def test_empty_directory(self, tmp_path):
        """Directorio vacío retorna válido con 0 eslabones."""
        result = verify_chain(tmp_path)
        assert result.valid is True
        assert result.total_links == 0
        assert result.verified_links == 0

    def test_single_link(self, tmp_path):
        """Un solo eslabón sin previous_hash es válido."""
        data_payload = {"hash": "abc123", "timestamp": "2026-01-01T00:00:00Z"}
        data_bytes = json.dumps(
            data_payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")
        expected = _compute_expected_hash(None, data_bytes)

        record = {**data_payload, "chained_hash": expected}
        hash_file = tmp_path / "link_001.sha256"
        hash_file.write_text(json.dumps(record), encoding="utf-8")

        result = verify_chain(tmp_path)
        assert result.valid is True
        assert result.total_links == 1
        assert result.verified_links == 1

    def test_valid_chain(self, tmp_path):
        """Cadena de 3 eslabones válida."""
        previous = None
        for i in range(3):
            data_payload = {"hash": f"data_{i}", "index": i}
            data_bytes = json.dumps(
                data_payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")
            ).encode("utf-8")
            chained = _compute_expected_hash(previous, data_bytes)

            record = {**data_payload, "chained_hash": chained}
            if previous:
                record["previous_hash"] = previous

            hash_file = tmp_path / f"link_{i:03d}.sha256"
            hash_file.write_text(json.dumps(record, sort_keys=True), encoding="utf-8")
            previous = chained

        result = verify_chain(tmp_path)
        assert result.valid is True
        assert result.total_links == 3
        assert result.verified_links == 3

    def test_broken_chain(self, tmp_path):
        """Cadena con hash manipulado se detecta como rota."""
        import time as _time

        previous = None
        for i in range(3):
            data_payload = {"hash": f"data_{i}", "index": i}
            data_bytes = json.dumps(
                data_payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")
            ).encode("utf-8")
            chained = _compute_expected_hash(previous, data_bytes)

            # Corromper el segundo eslabón
            if i == 1:
                chained = "0" * 64

            record = {**data_payload, "chained_hash": chained}
            if previous:
                record["previous_hash"] = previous

            hash_file = tmp_path / f"link_{i:03d}.sha256"
            hash_file.write_text(json.dumps(record, sort_keys=True), encoding="utf-8")
            # Ensure distinct mtime ordering
            _time.sleep(0.05)
            previous = chained

        result = verify_chain(tmp_path)
        assert result.valid is False
        assert result.broken_at is not None

    def test_corrupted_json(self, tmp_path):
        """Archivo JSON corrupto se reporta como error."""
        hash_file = tmp_path / "link_000.sha256"
        hash_file.write_text("{corrupted", encoding="utf-8")

        result = verify_chain(tmp_path)
        assert len(result.errors) > 0


class TestVerifyChainFromEntries:
    """Pruebas de verify_chain_from_entries."""

    def test_empty(self):
        result = verify_chain_from_entries([])
        assert result.valid is True
        assert result.total_links == 0

    def test_valid_entries(self):
        entries = []
        previous = None
        for i in range(5):
            data = f"entry_{i}"
            h = _compute_expected_hash(previous, data.encode("utf-8"))
            entries.append({"hash": h, "data": data})
            previous = h

        result = verify_chain_from_entries(entries)
        assert result.valid is True
        assert result.verified_links == 5

    def test_tampered_entry(self):
        entries = []
        previous = None
        for i in range(3):
            data = f"entry_{i}"
            h = _compute_expected_hash(previous, data.encode("utf-8"))
            entries.append({"hash": h, "data": data})
            previous = h

        # Tamper with middle entry
        entries[1]["hash"] = "deadbeef" * 8
        result = verify_chain_from_entries(entries)
        assert result.valid is False
        assert result.broken_at == 1


# ---------------------------------------------------------------------------
# Ed25519 signature tests
# ---------------------------------------------------------------------------

class TestOperatorSignature:
    """Pruebas de firma Ed25519 del operador."""

    def test_generate_keypair(self, tmp_path):
        """Genera par de claves Ed25519."""
        result = generate_operator_keypair(key_dir=tmp_path, operator_id="test-op")
        assert result["operator_id"] == "test-op"
        assert (tmp_path / "operator_private.pem").exists()
        assert (tmp_path / "operator_public.pem").exists()
        assert len(result["public_key_hex"]) == 64  # 32 bytes hex

    def test_sign_and_verify_snapshot(self, tmp_path):
        """Firma y verifica un snapshot."""
        generate_operator_keypair(key_dir=tmp_path, operator_id="test-op")
        data = b'{"votes":100,"candidate":"Alice"}'

        sig_result = sign_snapshot(
            data, key_path=tmp_path / "operator_private.pem", operator_id="test-op"
        )
        assert sig_result.operator_id == "test-op"
        assert sig_result.signature_hex
        assert sig_result.public_key_hex

        # Verificar con clave pública
        valid = verify_snapshot_signature(
            data, sig_result.signature_hex,
            public_key_path=tmp_path / "operator_public.pem",
        )
        assert valid is True

        # Verificar con hex directo
        valid_hex = verify_snapshot_signature(
            data, sig_result.signature_hex,
            public_key_hex=sig_result.public_key_hex,
        )
        assert valid_hex is True

    def test_invalid_signature_rejected(self, tmp_path):
        """Firma manipulada se rechaza."""
        generate_operator_keypair(key_dir=tmp_path)
        data = b"original data"

        sig_result = sign_snapshot(
            data, key_path=tmp_path / "operator_private.pem"
        )

        # Manipular firma
        bad_sig = "00" * 64
        valid = verify_snapshot_signature(
            data, bad_sig, public_key_hex=sig_result.public_key_hex
        )
        assert valid is False

    def test_different_data_fails(self, tmp_path):
        """Datos diferentes producen verificación fallida."""
        generate_operator_keypair(key_dir=tmp_path)

        sig_result = sign_snapshot(
            b"data A", key_path=tmp_path / "operator_private.pem"
        )

        valid = verify_snapshot_signature(
            b"data B", sig_result.signature_hex,
            public_key_hex=sig_result.public_key_hex,
        )
        assert valid is False

    def test_missing_key_raises(self, tmp_path):
        """Falta de clave privada lanza FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            sign_snapshot(b"data", key_path=tmp_path / "nonexistent.pem")


class TestHashRecordSignature:
    """Pruebas de firma de registros de hash."""

    def test_sign_and_verify_record(self, tmp_path):
        """Firma un registro de hash y lo verifica."""
        generate_operator_keypair(key_dir=tmp_path, operator_id="audit-op")
        record = {
            "hash": "abc123def456",
            "chained_hash": "789012345678",
            "timestamp": "2026-01-15T00:00:00Z",
        }

        signed = sign_hash_record(
            record, key_path=tmp_path / "operator_private.pem", operator_id="audit-op"
        )
        assert "operator_signature" in signed
        assert signed["operator_signature"]["algorithm"] == "Ed25519"
        assert signed["operator_signature"]["operator_id"] == "audit-op"

        assert verify_hash_record_signature(signed) is True

    def test_tampered_record_fails(self, tmp_path):
        """Registro alterado post-firma falla verificación."""
        generate_operator_keypair(key_dir=tmp_path)
        record = {"hash": "aaa", "chained_hash": "bbb"}

        signed = sign_hash_record(
            record, key_path=tmp_path / "operator_private.pem"
        )

        signed["hash"] = "MANIPULATED"
        assert verify_hash_record_signature(signed) is False

    def test_record_without_signature(self):
        """Registro sin firma retorna False."""
        record = {"hash": "abc", "chained_hash": "def"}
        assert verify_hash_record_signature(record) is False


# ---------------------------------------------------------------------------
# _compute_expected_hash tests
# ---------------------------------------------------------------------------

class TestComputeExpectedHash:
    """Pruebas de _compute_expected_hash."""

    def test_without_previous(self):
        data = b"hello"
        expected = hashlib.sha256(b"hello").hexdigest()
        assert _compute_expected_hash(None, data) == expected

    def test_with_previous(self):
        prev = "abc123"
        data = b"hello"
        expected = hashlib.sha256(b"abc123hello").hexdigest()
        assert _compute_expected_hash(prev, data) == expected

    def test_deterministic(self):
        h1 = _compute_expected_hash("prev", b"data")
        h2 = _compute_expected_hash("prev", b"data")
        assert h1 == h2

    def test_different_previous_different_hash(self):
        h1 = _compute_expected_hash("prev_a", b"data")
        h2 = _compute_expected_hash("prev_b", b"data")
        assert h1 != h2


# ---------------------------------------------------------------------------
# verify_anchor tests (mocked)
# ---------------------------------------------------------------------------

class TestVerifyAnchor:
    """Pruebas de verify_anchor con Web3 mockeado."""

    def test_missing_rpc_url(self):
        from sentinel.core.custody import verify_anchor

        result = verify_anchor("0x123", rpc_url="", contract_address="0xc")
        assert result.valid is False
        assert result.error == "missing_rpc_url"

    def _build_mock_web3(self, receipt):
        """Helper para construir un Web3 mock."""
        mock_instance = MagicMock()
        mock_instance.is_connected.return_value = True
        mock_instance.keccak.return_value = b"\x01" * 32
        mock_instance.eth.get_transaction_receipt.return_value = receipt
        mock_module = MagicMock()
        mock_module.Web3.return_value = mock_instance
        mock_module.Web3.HTTPProvider.return_value = MagicMock()
        return mock_module, mock_instance

    def test_successful_verification(self):
        import importlib
        import sys

        expected_root = "0x" + "ab" * 32
        event_sig = b"\x01" * 32

        mock_receipt = {
            "status": 1,
            "blockNumber": 12345,
            "logs": [
                {
                    "topics": [event_sig, bytes.fromhex("ab" * 32)],
                    "data": (0).to_bytes(32, "big"),
                }
            ],
        }

        mock_web3_mod, mock_inst = self._build_mock_web3(mock_receipt)
        mock_inst.keccak.return_value = event_sig

        with patch.dict(sys.modules, {"web3": mock_web3_mod}):
            # Re-import to pick up mock
            import sentinel.core.custody as custody_mod
            importlib.reload(custody_mod)

            result = custody_mod.verify_anchor(
                "0xtx123", expected_root,
                rpc_url="https://rpc", contract_address="0xcontract",
            )

        assert result.valid is True
        assert result.block_number == 12345

        # Restore module
        importlib.reload(custody_mod)

    def test_root_mismatch(self):
        import importlib
        import sys

        event_sig = b"\x01" * 32

        mock_receipt = {
            "status": 1,
            "blockNumber": 100,
            "logs": [
                {
                    "topics": [event_sig, bytes.fromhex("cc" * 32)],
                    "data": (0).to_bytes(32, "big"),
                }
            ],
        }

        mock_web3_mod, mock_inst = self._build_mock_web3(mock_receipt)
        mock_inst.keccak.return_value = event_sig

        with patch.dict(sys.modules, {"web3": mock_web3_mod}):
            import sentinel.core.custody as custody_mod
            importlib.reload(custody_mod)

            result = custody_mod.verify_anchor(
                "0xtx", "0x" + "dd" * 32,
                rpc_url="https://rpc", contract_address="0xcontract",
            )

        assert result.valid is False
        assert result.error == "root_mismatch"

        importlib.reload(custody_mod)


# ---------------------------------------------------------------------------
# Startup verification tests
# ---------------------------------------------------------------------------

class TestStartupVerification:
    """Pruebas de verificación al arranque."""

    def test_no_hash_dir(self, tmp_path):
        """Sin directorio de hashes retorna válido vacío."""
        report = run_startup_verification(
            hash_dir=tmp_path / "nonexistent",
            anchor_log_dir=tmp_path / "no_anchors",
        )
        assert report.overall_valid is True
        assert report.chain_result is not None

    def test_valid_chain_startup(self, tmp_path):
        """Cadena válida al arranque pasa verificación."""
        hash_dir = tmp_path / "hashes"
        hash_dir.mkdir()

        previous = None
        for i in range(3):
            data_payload = {"hash": f"h{i}", "idx": i}
            data_bytes = json.dumps(
                data_payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")
            ).encode("utf-8")
            chained = _compute_expected_hash(previous, data_bytes)
            record = {**data_payload, "chained_hash": chained}
            if previous:
                record["previous_hash"] = previous
            (hash_dir / f"link_{i:03d}.sha256").write_text(
                json.dumps(record, sort_keys=True), encoding="utf-8"
            )
            previous = chained

        report = run_startup_verification(
            hash_dir=hash_dir,
            anchor_log_dir=tmp_path / "anchors",
            verify_signatures=False,
        )
        assert report.overall_valid is True
        assert report.chain_result.verified_links == 3

    def test_report_serializable(self, tmp_path):
        """El reporte se serializa correctamente a JSON."""
        report = run_startup_verification(
            hash_dir=tmp_path,
            anchor_log_dir=tmp_path,
        )
        d = report.to_dict()
        serialized = json.dumps(d)
        assert "overall_valid" in serialized

    def test_signature_verification_at_startup(self, tmp_path):
        """Firmas válidas pasan verificación al arranque."""
        hash_dir = tmp_path / "hashes"
        hash_dir.mkdir()
        key_dir = tmp_path / "keys"

        generate_operator_keypair(key_dir=key_dir, operator_id="startup-op")

        data_payload = {"hash": "test", "idx": 0}
        data_bytes = json.dumps(
            data_payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")
        chained = _compute_expected_hash(None, data_bytes)

        record = {**data_payload, "chained_hash": chained}
        sign_hash_record(
            record,
            key_path=key_dir / "operator_private.pem",
            operator_id="startup-op",
        )
        (hash_dir / "link_000.sha256").write_text(
            json.dumps(record, sort_keys=True), encoding="utf-8"
        )

        report = run_startup_verification(
            hash_dir=hash_dir,
            anchor_log_dir=tmp_path / "anchors",
            verify_signatures=True,
        )
        assert report.overall_valid is True
        assert len(report.signature_failures) == 0
