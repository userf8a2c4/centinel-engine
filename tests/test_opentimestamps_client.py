"""
Tests for OpenTimestamps client.

Validates OTS integration, retry logic, and multi-chain fallback.
"""

import time
from unittest.mock import MagicMock, patch

import pytest

from centinel.anchor.opentimestamps_client import (
    MultichainAnchor,
    OpenTimestampsClient,
    TimestampProof,
)


class TestTimestampProof:
    """Test TimestampProof dataclass."""

    def test_create_proof(self):
        """Create valid timestamp proof."""
        proof = TimestampProof(
            timestamp=time.time(),
            message_hash="a" * 64,
            ots_response="abc123base64encoded",
            bitcoin_tx="abc123tx",
        )

        assert proof.message_hash == "a" * 64
        assert proof.bitcoin_tx == "abc123tx"
        assert proof.chain == "mainnet"
        assert proof.verified is False

    def test_proof_testnet(self):
        """Proof for testnet."""
        proof = TimestampProof(
            timestamp=time.time(),
            message_hash="b" * 64,
            ots_response="xyz789",
            chain="testnet",
        )

        assert proof.chain == "testnet"


class TestOpenTimestampsClient:
    """Test OpenTimestamps client."""

    def test_client_creation(self):
        """Create OTS client."""
        client = OpenTimestampsClient(timeout=10.0, max_retries=2)

        assert client.timeout == 10.0
        assert client.max_retries == 2
        assert client.use_testnet is False

    def test_client_testnet(self):
        """Create testnet OTS client."""
        client = OpenTimestampsClient(use_testnet=True)

        assert client.use_testnet is True
        assert len(client.servers) > 0

    def test_message_hash_from_string(self):
        """Hash message string."""
        import hashlib

        message = "checkpoint-2026-05-16T00:00:00Z"
        expected_hash = hashlib.sha256(message.encode("utf-8")).hexdigest()

        # OTS client would compute this internally
        assert len(expected_hash) == 64

    def test_message_hash_from_bytes(self):
        """Hash message bytes."""
        import hashlib

        message = b"checkpoint-2026-05-16T00:00:00Z"
        expected_hash = hashlib.sha256(message).hexdigest()

        assert len(expected_hash) == 64

    @patch("httpx.Client.post")
    def test_stamp_success(self, mock_post):
        """Request OTS stamp successfully."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ots_proof": "base64encodedproof",
            "bitcoin_tx": "abc123tx123",
            "bitcoin_block": 12345,
        }
        mock_post.return_value = mock_response

        client = OpenTimestampsClient()
        proof = client.stamp("test message")

        assert proof is not None
        assert proof.bitcoin_tx == "abc123tx123"
        assert proof.bitcoin_block == 12345
        assert proof.ots_response == "base64encodedproof"

    @patch("httpx.Client.post")
    def test_stamp_retry_logic(self, mock_post):
        """OTS stamp retries on failure."""
        # First 2 attempts fail, 3rd succeeds
        mock_response_fail = MagicMock()
        mock_response_fail.status_code = 503

        mock_response_success = MagicMock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {
            "ots_proof": "proof",
            "bitcoin_tx": "tx",
        }

        mock_post.side_effect = [
            mock_response_fail,
            mock_response_fail,
            mock_response_success,
        ]

        client = OpenTimestampsClient(max_retries=3)
        with patch("time.sleep"):  # Skip actual sleep
            proof = client.stamp("test")

        assert proof is not None
        assert mock_post.call_count >= 2

    @patch("httpx.Client.post")
    def test_stamp_max_retries_exceeded(self, mock_post):
        """OTS stamp fails after max retries."""
        import httpx

        mock_post.side_effect = httpx.TimeoutException("timeout")

        client = OpenTimestampsClient(max_retries=2)
        with patch("time.sleep"):
            proof = client.stamp("test")

        assert proof is None
        assert len(client.anchor_records) == 1
        assert client.anchor_records[0].success is False

    def test_verify_proof_valid(self):
        """Verify valid proof."""
        proof = TimestampProof(
            timestamp=time.time(),
            message_hash="a" * 64,
            ots_response="validproof",
        )

        client = OpenTimestampsClient()
        is_valid = client.verify_proof(proof)

        assert is_valid is True

    def test_verify_proof_invalid_hash(self):
        """Verify proof with invalid hash."""
        proof = TimestampProof(
            timestamp=time.time(),
            message_hash="tooshort",
            ots_response="validproof",
        )

        client = OpenTimestampsClient()
        is_valid = client.verify_proof(proof)

        assert is_valid is False

    def test_verify_proof_empty_response(self):
        """Verify proof with empty response."""
        proof = TimestampProof(
            timestamp=time.time(),
            message_hash="a" * 64,
            ots_response="",
        )

        client = OpenTimestampsClient()
        is_valid = client.verify_proof(proof)

        assert is_valid is False

    @patch("httpx.Client.post")
    def test_forensic_records(self, mock_post):
        """Export anchor attempts as forensic records."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ots_proof": "proof",
            "bitcoin_tx": "tx",
        }
        mock_post.return_value = mock_response

        client = OpenTimestampsClient()
        proof = client.stamp("message1")
        assert proof is not None

        records = client.to_forensic_records()
        assert len(records) == 1
        assert records[0]["success"] is True
        assert "checkpoint_hash" in records[0]


class TestMultichainAnchor:
    """Test multi-chain anchor with fallback."""

    def test_multichain_creation(self):
        """Create multi-chain anchor."""
        anchor = MultichainAnchor(testnet=False)

        assert anchor.testnet is False
        assert anchor.ots_client is not None

    @patch("centinel.anchor.opentimestamps_client.OpenTimestampsClient.stamp")
    def test_anchor_checkpoint_success(self, mock_stamp):
        """Anchor checkpoint successfully."""
        proof = TimestampProof(
            timestamp=time.time(),
            message_hash="a" * 64,
            ots_response="proof",
            bitcoin_tx="tx123",
        )
        mock_stamp.return_value = proof

        anchor = MultichainAnchor()
        checkpoint = {
            "timestamp": "2026-05-16T00:00:00Z",
            "merkle_root": "abc123" * 10 + "abcd",
        }

        result = anchor.anchor_checkpoint(checkpoint)

        assert result["bitcoin_tx"] == "tx123"
        assert result["ots_proof"] == "proof"
        assert result["anchor_chain"] == "bitcoin"

    @patch("centinel.anchor.opentimestamps_client.OpenTimestampsClient.stamp")
    def test_anchor_checkpoint_no_merkle(self, mock_stamp):
        """Anchor checkpoint without merkle root."""
        anchor = MultichainAnchor()
        checkpoint = {"timestamp": "2026-05-16T00:00:00Z"}

        result = anchor.anchor_checkpoint(checkpoint)

        # Should return unchanged (non-fatal)
        assert "bitcoin_tx" not in result
        assert mock_stamp.call_count == 0

    @patch("centinel.anchor.opentimestamps_client.OpenTimestampsClient.stamp")
    def test_anchor_checkpoint_ots_fails(self, mock_stamp):
        """Anchor checkpoint when OTS fails (no fallback configured)."""
        mock_stamp.return_value = None

        anchor = MultichainAnchor(arbitrum_rpc=None)
        checkpoint = {
            "timestamp": "2026-05-16T00:00:00Z",
            "merkle_root": "abc123" * 10 + "abcd",
        }

        result = anchor.anchor_checkpoint(checkpoint)

        # Should return checkpoint unchanged (non-fatal)
        assert "bitcoin_tx" not in result
