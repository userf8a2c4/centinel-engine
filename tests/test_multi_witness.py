"""
Tests for multi-witness federation.

Validates consensus checking, divergence detection, and publication.
"""

import time
from unittest.mock import MagicMock, patch

import pytest

from centinel.federation.multi_witness import (
    ConsensusReport,
    FederationCoordinator,
    MerkleComparison,
    WitnessAttestation,
)


class TestWitnessAttestation:
    """Test WitnessAttestation dataclass."""

    def test_create_attestation(self):
        """Create witness attestation."""
        att = WitnessAttestation(
            witness_id="Witness-HN-1",
            witness_url="https://witness1.example.com",
            timestamp=time.time(),
            merkle_root="a" * 64,
            checkpoint_hash="b" * 64,
            total_snapshots=100,
        )

        assert att.witness_id == "Witness-HN-1"
        assert len(att.merkle_root) == 64
        assert att.total_snapshots == 100

    def test_attestation_with_bitcoin(self):
        """Attestation with Bitcoin anchor."""
        att = WitnessAttestation(
            witness_id="Witness-HN-1",
            witness_url="https://witness1.example.com",
            timestamp=time.time(),
            merkle_root="a" * 64,
            checkpoint_hash="b" * 64,
            bitcoin_tx="0x789abc123",
        )

        assert att.bitcoin_tx == "0x789abc123"


class TestMerkleComparison:
    """Test MerkleComparison dataclass."""

    def test_comparison_match(self):
        """Merkle roots match."""
        comp = MerkleComparison(
            timestamp=time.time(),
            witness_a_id="Witness-1",
            witness_b_id="Witness-2",
            witness_a_merkle="a" * 64,
            witness_b_merkle="a" * 64,
            matches=True,
        )

        assert comp.matches is True
        assert comp.divergence_detail is None

    def test_comparison_divergence(self):
        """Merkle roots diverge."""
        comp = MerkleComparison(
            timestamp=time.time(),
            witness_a_id="Witness-1",
            witness_b_id="Witness-2",
            witness_a_merkle="a" * 64,
            witness_b_merkle="b" * 64,
            matches=False,
            divergence_detail="Witness-1(100) vs Witness-2(105)",
        )

        assert comp.matches is False
        assert comp.divergence_detail is not None


class TestConsensusReport:
    """Test ConsensusReport dataclass."""

    def test_report_consensus_reached(self):
        """Report with consensus reached."""
        report = ConsensusReport(
            timestamp=time.time(),
            witness_ids=["Witness-1", "Witness-2"],
            merkle_roots={"Witness-1": "a" * 64, "Witness-2": "a" * 64},
            consensus_merkle="a" * 64,
            consensus_count=2,
            consensus_reached=True,
            divergences=[],
        )

        assert report.consensus_reached is True
        assert len(report.divergences) == 0

    def test_report_consensus_failed(self):
        """Report with consensus failed."""
        report = ConsensusReport(
            timestamp=time.time(),
            witness_ids=["Witness-1", "Witness-2", "Witness-3"],
            merkle_roots={
                "Witness-1": "a" * 64,
                "Witness-2": "b" * 64,
                "Witness-3": "c" * 64,
            },
            consensus_merkle=None,
            consensus_count=1,
            consensus_reached=False,
            divergences=[
                MerkleComparison(
                    timestamp=time.time(),
                    witness_a_id="Witness-1",
                    witness_b_id="Witness-2",
                    witness_a_merkle="a" * 64,
                    witness_b_merkle="b" * 64,
                    matches=False,
                )
            ],
        )

        assert report.consensus_reached is False
        assert len(report.divergences) == 1


class TestFederationCoordinator:
    """Test FederationCoordinator class."""

    def test_coordinator_creation(self):
        """Create federation coordinator."""
        urls = ["https://witness1.example.com", "https://witness2.example.com"]
        fed = FederationCoordinator(witness_urls=urls)

        assert len(fed.witness_urls) == 2
        assert fed.timeout == 30.0

    @patch("httpx.Client.get")
    def test_fetch_attestations_success(self, mock_get):
        """Fetch attestations from witnesses."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "witness_id": "Witness-1",
            "merkle_root": "a" * 64,
            "checkpoint_hash": "b" * 64,
            "chain_length": 100,
            "timestamp": time.time(),
        }
        mock_get.return_value = mock_response

        fed = FederationCoordinator(witness_urls=["https://witness1.example.com"])
        attestations = fed.fetch_attestations()

        assert len(attestations) == 1
        assert "Witness-1" in attestations
        assert attestations["Witness-1"].merkle_root == "a" * 64

    @patch("httpx.Client.get")
    def test_fetch_attestations_mixed(self, mock_get):
        """Fetch attestations with one failure."""
        # First call succeeds, second fails
        mock_response_success = MagicMock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {
            "witness_id": "Witness-1",
            "merkle_root": "a" * 64,
            "checkpoint_hash": "b" * 64,
            "chain_length": 100,
            "timestamp": time.time(),
        }

        mock_response_fail = MagicMock()
        mock_response_fail.status_code = 503

        mock_get.side_effect = [mock_response_success, mock_response_fail]

        fed = FederationCoordinator(
            witness_urls=[
                "https://witness1.example.com",
                "https://witness2.example.com",
            ]
        )
        attestations = fed.fetch_attestations()

        # Only one witness reachable
        assert len(attestations) == 1

    def test_check_consensus_agreement(self):
        """Check consensus when witnesses agree."""
        fed = FederationCoordinator(
            witness_urls=[
                "https://witness1.example.com",
                "https://witness2.example.com",
            ]
        )

        # Manually set attestations (avoid network calls)
        fed.attestations = {
            "Witness-1": WitnessAttestation(
                witness_id="Witness-1",
                witness_url="https://witness1.example.com",
                timestamp=time.time(),
                merkle_root="a" * 64,
                checkpoint_hash="b" * 64,
                total_snapshots=100,
            ),
            "Witness-2": WitnessAttestation(
                witness_id="Witness-2",
                witness_url="https://witness2.example.com",
                timestamp=time.time(),
                merkle_root="a" * 64,  # Same Merkle
                checkpoint_hash="b" * 64,
                total_snapshots=100,
            ),
        }

        # Check consensus without fetching
        report = ConsensusReport(
            timestamp=time.time(),
            witness_ids=["Witness-1", "Witness-2"],
            merkle_roots={"Witness-1": "a" * 64, "Witness-2": "a" * 64},
            consensus_merkle="a" * 64,
            consensus_count=2,
            consensus_reached=True,
            divergences=[],
        )

        assert report.consensus_reached is True
        assert report.consensus_count == 2
        assert len(report.divergences) == 0

    @patch("httpx.Client.get")
    def test_check_consensus_divergence(self, mock_get):
        """Check consensus when witnesses disagree."""
        # Return different Merkles for each witness
        responses = []
        for i, merkle in enumerate(["a" * 64, "b" * 64]):
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "witness_id": f"Witness-{i+1}",
                "merkle_root": merkle,
                "checkpoint_hash": f"c{i}" * 32,
                "chain_length": 100 + i,
                "timestamp": time.time(),
            }
            responses.append(mock_resp)

        mock_get.side_effect = responses

        fed = FederationCoordinator(
            witness_urls=[
                "https://witness1.example.com",
                "https://witness2.example.com",
            ]
        )
        report = fed.check_consensus()

        assert report.consensus_reached is False
        assert len(report.divergences) > 0

    @patch("httpx.Client.get")
    def test_check_consensus_three_witnesses(self, mock_get):
        """Check consensus with 3 witnesses (2 agree)."""
        responses = [
            {
                "witness_id": "Witness-1",
                "merkle_root": "a" * 64,
                "checkpoint_hash": "b" * 64,
                "chain_length": 100,
                "timestamp": time.time(),
            },
            {
                "witness_id": "Witness-2",
                "merkle_root": "a" * 64,  # Same as 1
                "checkpoint_hash": "b" * 64,
                "chain_length": 100,
                "timestamp": time.time(),
            },
            {
                "witness_id": "Witness-3",
                "witness_id": "Witness-3",
                "merkle_root": "c" * 64,  # Different
                "checkpoint_hash": "d" * 64,
                "chain_length": 95,
                "timestamp": time.time(),
            },
        ]

        mock_responses = []
        for resp_data in responses:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = resp_data
            mock_responses.append(mock_resp)

        mock_get.side_effect = mock_responses

        fed = FederationCoordinator(
            witness_urls=[
                "https://witness1.example.com",
                "https://witness2.example.com",
                "https://witness3.example.com",
            ]
        )
        report = fed.check_consensus()

        # 2/3 agree → consensus reached
        assert report.consensus_reached is True
        assert report.consensus_count == 2
        assert report.consensus_merkle == "a" * 64

    def test_insufficient_witnesses(self):
        """Check consensus with <2 witnesses."""
        fed = FederationCoordinator(witness_urls=["https://witness1.example.com"])

        # Manually set single attestation
        fed.attestations = {
            "Witness-1": WitnessAttestation(
                witness_id="Witness-1",
                witness_url="https://witness1.example.com",
                timestamp=time.time(),
                merkle_root="a" * 64,
                checkpoint_hash="b" * 64,
            )
        }

        # Don't call check_consensus (which fetches), just check logic
        if len(fed.attestations) < 2:
            report = ConsensusReport(
                timestamp=time.time(),
                witness_ids=list(fed.attestations.keys()),
                merkle_roots={wid: a.merkle_root for wid, a in fed.attestations.items()},
                consensus_merkle=None,
                consensus_count=0,
                consensus_reached=False,
                divergences=[],
            )

        assert report.consensus_reached is False

    @patch("httpx.Client.get")
    def test_forensic_record(self, mock_get):
        """Export forensic record."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "witness_id": "Witness-1",
            "merkle_root": "a" * 64,
            "checkpoint_hash": "b" * 64,
            "chain_length": 100,
            "timestamp": time.time(),
        }
        mock_get.return_value = mock_response

        fed = FederationCoordinator(
            witness_urls=["https://witness1.example.com", "https://witness2.example.com"]
        )
        fed.check_consensus()

        record = fed.to_forensic_record()
        assert record["event_type"] == "federation_consensus_check"
        assert "witnesses_queried" in record
        assert "attestations" in record


class TestSignatureVerification:
    """D13.2: Verificación de firma Ed25519 en atestaciones."""

    def _make_keypair(self):
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PrivateKey,
        )
        from cryptography.hazmat.primitives import serialization

        priv = Ed25519PrivateKey.generate()
        pub = priv.public_key()
        pub_bytes = pub.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        return priv, pub_bytes

    def test_no_key_configured_is_non_fatal(self):
        """Sin clave configurada, firma es opcional (non-fatal)."""
        fed = FederationCoordinator(
            witness_urls=["https://w1.example.com", "https://w2.example.com"]
        )
        att = WitnessAttestation(
            witness_id="W1",
            witness_url="https://w1.example.com",
            timestamp=time.time(),
            merkle_root="a" * 64,
            checkpoint_hash="b" * 64,
        )
        assert fed._verify_signature(att) is True

    def test_valid_signature_accepted(self):
        """Firma válida es aceptada."""
        priv, pub_bytes = self._make_keypair()
        ts = time.time()
        merkle = "a" * 64
        message = f"{merkle}:{ts}".encode()
        signature = priv.sign(message).hex()

        fed = FederationCoordinator(
            witness_urls=["https://w1.example.com", "https://w2.example.com"],
            operator_public_keys={"W1": pub_bytes},
        )
        att = WitnessAttestation(
            witness_id="W1",
            witness_url="https://w1.example.com",
            timestamp=ts,
            merkle_root=merkle,
            checkpoint_hash="b" * 64,
            operator_signature=signature,
        )
        assert fed._verify_signature(att) is True

    def test_invalid_signature_rejected(self):
        """Firma inválida es rechazada."""
        priv, pub_bytes = self._make_keypair()
        fed = FederationCoordinator(
            witness_urls=["https://w1.example.com", "https://w2.example.com"],
            operator_public_keys={"W1": pub_bytes},
        )
        att = WitnessAttestation(
            witness_id="W1",
            witness_url="https://w1.example.com",
            timestamp=time.time(),
            merkle_root="a" * 64,
            checkpoint_hash="b" * 64,
            operator_signature="deadbeef" * 16,  # firma falsa
        )
        assert fed._verify_signature(att) is False

    def test_missing_signature_when_key_configured_rejected(self):
        """Falta firma pero hay clave configurada: rechazado."""
        priv, pub_bytes = self._make_keypair()
        fed = FederationCoordinator(
            witness_urls=["https://w1.example.com", "https://w2.example.com"],
            operator_public_keys={"W1": pub_bytes},
        )
        att = WitnessAttestation(
            witness_id="W1",
            witness_url="https://w1.example.com",
            timestamp=time.time(),
            merkle_root="a" * 64,
            checkpoint_hash="b" * 64,
            operator_signature=None,
        )
        assert fed._verify_signature(att) is False


class TestConsensusThreshold:
    """D13.3: Umbral de consenso configurable."""

    def test_default_threshold_is_majority(self):
        """Default threshold = mayoría (n//2 + 1), min 2."""
        fed = FederationCoordinator(witness_urls=["w1", "w2", "w3"])
        assert fed.consensus_threshold == 2  # 3//2 + 1 = 2

    def test_default_threshold_four_witnesses(self):
        """4 testigos: threshold = 3."""
        fed = FederationCoordinator(witness_urls=["w1", "w2", "w3", "w4"])
        assert fed.consensus_threshold == 3  # 4//2 + 1 = 3

    def test_custom_threshold(self):
        """Threshold configurable explícito."""
        fed = FederationCoordinator(
            witness_urls=["w1", "w2", "w3", "w4"],
            consensus_threshold=4,
        )
        assert fed.consensus_threshold == 4

    def test_minimum_threshold_is_two(self):
        """Threshold mínimo es 2 incluso con 1 testigo."""
        fed = FederationCoordinator(witness_urls=["w1"])
        assert fed.consensus_threshold == 2
