"""
Multi-Witness Federation for Centinel Engine.

ES: Federación de Múltiples Testigos para Centinel Engine.

Coordina ≥2 testigos para verificar datos de elecciones.
Detecta si CNE bloquea/manipula un testigo (sibling witnesses comparan Merkle roots).

EN: Coordinates ≥2 witnesses to verify election data.
Detects if CNE blocks/manipulates one witness (sibling witnesses compare Merkle roots).

Design:
- Symmetric federation: no central authority
- Consensus via Merkle root comparison (gossip protocol)
- Forensic logging: all divergences recorded
- Non-fatal: if sibling unreachable, continue independently
- Attestation: each witness publishes its Merkle root + signature

References:
  - Merkle tree consensus (Bitcoin SPV)
  - Byzantine Fault Tolerance (1/3 faulty tolerance with 3+ witnesses)
  - Gossip protocol (epidemic protocol, eventual consistency)
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, asdict
from typing import Any, Optional

import httpx

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    from cryptography.exceptions import InvalidSignature

    _CRYPTO_AVAILABLE = True
except ImportError:  # pragma: no cover
    _CRYPTO_AVAILABLE = False

logger = logging.getLogger("centinel.federation.multi_witness")


@dataclass
class WitnessAttestation:
    """Attestation published by a witness.

    ES: Atestación publicada por un testigo.
    """
    witness_id: str  # Identifier (e.g., "Witness-HN-1")
    witness_url: str  # Base URL (e.g., "https://witness1.example.com")
    timestamp: float
    merkle_root: str  # SHA256 of snapshot chain (64-char hex)
    checkpoint_hash: str  # SHA256 of latest checkpoint (64-char hex)
    endpoint_schema_merkle: Optional[str] = None  # Schema Merkle root
    total_snapshots: int = 0
    bitcoin_tx: Optional[str] = None  # From OTS anchor
    operator_signature: Optional[str] = None  # Ed25519 signature (optional)


@dataclass
class MerkleComparison:
    """Result of comparing two witness Merkle roots.

    ES: Resultado de comparar Merkles de dos testigos.
    """
    timestamp: float
    witness_a_id: str
    witness_b_id: str
    witness_a_merkle: str
    witness_b_merkle: str
    matches: bool
    divergence_detail: Optional[str] = None


@dataclass
class ConsensusReport:
    """Summary of consensus check across witnesses.

    ES: Resumen de consenso entre testigos.
    """
    timestamp: float
    witness_ids: list[str]
    merkle_roots: dict[str, str]  # witness_id → merkle_root
    consensus_merkle: Optional[str]  # Root if ≥2 agree (None if all differ)
    consensus_count: int  # How many witnesses agree on consensus_merkle
    consensus_reached: bool  # ≥ 2 witnesses in agreement
    divergences: list[MerkleComparison]


class FederationCoordinator:
    """Coordinates consensus checks across witnesses.

    ES: Coordina verificaciones de consenso entre testigos.

    Usage:
        fed = FederationCoordinator(
            witness_urls=["https://witness1.example.com", "https://witness2.example.com"]
        )
        report = fed.check_consensus()
        if report.consensus_reached:
            print("Consensus OK")
        else:
            print("Divergence detected:", report.divergences)
    """

    def __init__(
        self,
        witness_urls: list[str],
        timeout: float = 30.0,
        enable_logging: bool = True,
        consensus_threshold: Optional[int] = None,
        operator_public_keys: Optional[dict[str, bytes]] = None,
    ) -> None:
        """Initialize federation coordinator.

        Args:
            witness_urls: List of witness base URLs
            timeout: HTTP request timeout (seconds)
            enable_logging: Enable forensic logging
            consensus_threshold: Min witnesses that must agree (default:
                majority = n//2 + 1). Allows 2/3, 3/4, etc.
            operator_public_keys: dict witness_id → Ed25519 public key bytes
                (32 raw bytes). If provided, attestation signatures are
                verified before counting toward consensus.
        """
        self.witness_urls = witness_urls
        self.timeout = timeout
        self.enable_logging = enable_logging
        self.attestations: dict[str, WitnessAttestation] = {}
        self.comparisons: list[MerkleComparison] = []
        # D13.3: configurable threshold (default majority, min 2)
        if consensus_threshold is not None:
            self.consensus_threshold = consensus_threshold
        else:
            self.consensus_threshold = max(2, len(witness_urls) // 2 + 1)
        # D13.2: operator public keys for signature verification
        self.operator_public_keys = operator_public_keys or {}
        logger.info(
            "federation_init witnesses=%d threshold=%d sig_verify=%s",
            len(witness_urls),
            self.consensus_threshold,
            bool(self.operator_public_keys),
        )

    def _verify_signature(self, attestation: WitnessAttestation) -> bool:
        """Verify Ed25519 operator signature on an attestation (D13.2).

        ES: Verifica firma Ed25519 del operador sobre la atestación.

        Message signed: "{merkle_root}:{timestamp}". Returns True if no
        public key is configured for the witness (signature optional,
        non-fatal) OR if the signature is valid. Returns False only if a
        key IS configured and the signature is missing/invalid.
        """
        pubkey_bytes = self.operator_public_keys.get(attestation.witness_id)
        if pubkey_bytes is None:
            # No key configured → signature optional (non-fatal)
            return True

        if not _CRYPTO_AVAILABLE:
            logger.warning("signature_verify_skipped reason=cryptography_unavailable")
            return True

        if not attestation.operator_signature:
            logger.error(
                "signature_missing witness=%s (key configured but no signature)",
                attestation.witness_id,
            )
            return False

        try:
            pubkey = Ed25519PublicKey.from_public_bytes(pubkey_bytes)
            message = f"{attestation.merkle_root}:{attestation.timestamp}".encode()
            signature = bytes.fromhex(attestation.operator_signature)
            pubkey.verify(signature, message)
            return True
        except (InvalidSignature, ValueError) as e:
            logger.error(
                "signature_invalid witness=%s error=%s",
                attestation.witness_id,
                str(e),
            )
            return False

    def fetch_attestations(self) -> dict[str, WitnessAttestation]:
        """Fetch latest checkpoint attestations from all witnesses.

        Returns dict of witness_id → WitnessAttestation.
        Unreachable witnesses omitted (non-fatal).
        """
        attestations = {}

        for url in self.witness_urls:
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    # Standardized endpoint: GET /api/checkpoint
                    resp = client.get(f"{url.rstrip('/')}/api/checkpoint")

                    if resp.status_code == 200:
                        data = resp.json()
                        witness_id = data.get("witness_id", url)

                        attestation = WitnessAttestation(
                            witness_id=witness_id,
                            witness_url=url,
                            timestamp=data.get("timestamp", time.time()),
                            merkle_root=data.get("merkle_root", ""),
                            checkpoint_hash=data.get("checkpoint_hash", ""),
                            endpoint_schema_merkle=data.get("endpoint_schema_merkle"),
                            total_snapshots=data.get("chain_length", 0),
                            bitcoin_tx=data.get("bitcoin_tx"),
                        )
                        attestations[witness_id] = attestation
                        logger.info(
                            "witness_attestation_fetched witness=%s merkle=%s",
                            witness_id,
                            attestation.merkle_root[:16],
                        )
                    else:
                        logger.warning(
                            "witness_attestation_http_error witness=%s status=%d",
                            url,
                            resp.status_code,
                        )

            except (httpx.RequestError, httpx.TimeoutException) as e:
                logger.warning(
                    "witness_attestation_fetch_failed witness=%s error=%s",
                    url,
                    str(e),
                )
                continue

        self.attestations = attestations
        return attestations

    def check_consensus(self) -> ConsensusReport:
        """Check consensus across all witnesses.

        Returns ConsensusReport with merkle comparison and consensus status.
        """
        # Fetch fresh attestations
        self.fetch_attestations()

        # D13.2: filter out attestations with invalid signatures
        if self.operator_public_keys:
            verified = {}
            for wid, att in self.attestations.items():
                if self._verify_signature(att):
                    verified[wid] = att
                else:
                    logger.error(
                        "attestation_rejected witness=%s reason=invalid_signature",
                        wid,
                    )
            self.attestations = verified

        if len(self.attestations) < 2:
            logger.warning(
                "insufficient_witnesses_for_consensus count=%d",
                len(self.attestations),
            )
            return ConsensusReport(
                timestamp=time.time(),
                witness_ids=list(self.attestations.keys()),
                merkle_roots={wid: a.merkle_root for wid, a in self.attestations.items()},
                consensus_merkle=None,
                consensus_count=0,
                consensus_reached=False,
                divergences=[],
            )

        # Compare all pairs
        witness_ids = list(self.attestations.keys())
        comparisons = []

        for i in range(len(witness_ids)):
            for j in range(i + 1, len(witness_ids)):
                wid_a = witness_ids[i]
                wid_b = witness_ids[j]
                att_a = self.attestations[wid_a]
                att_b = self.attestations[wid_b]

                matches = att_a.merkle_root == att_b.merkle_root
                comparison = MerkleComparison(
                    timestamp=time.time(),
                    witness_a_id=wid_a,
                    witness_b_id=wid_b,
                    witness_a_merkle=att_a.merkle_root,
                    witness_b_merkle=att_b.merkle_root,
                    matches=matches,
                    divergence_detail=(
                        None
                        if matches
                        else f"{wid_a}({att_a.total_snapshots}) vs {wid_b}({att_b.total_snapshots})"
                    ),
                )
                comparisons.append(comparison)

                if not matches:
                    logger.error(
                        "witness_merkle_divergence witness_a=%s merkle_a=%s witness_b=%s merkle_b=%s",
                        wid_a,
                        att_a.merkle_root[:16],
                        wid_b,
                        att_b.merkle_root[:16],
                    )
                else:
                    logger.info(
                        "witness_merkle_agreement witness_a=%s witness_b=%s merkle=%s",
                        wid_a,
                        wid_b,
                        att_a.merkle_root[:16],
                    )

        self.comparisons = comparisons

        # Determine consensus (Byzantine: 2/3 or majority)
        merkle_counts = {}
        for wid, att in self.attestations.items():
            merkle_counts[att.merkle_root] = merkle_counts.get(att.merkle_root, 0) + 1

        consensus_merkle = None
        consensus_count = 0
        for merkle, count in merkle_counts.items():
            if count > consensus_count:
                consensus_count = count
                consensus_merkle = merkle

        # D13.3: require configurable threshold agreement (default majority)
        consensus_reached = consensus_count >= self.consensus_threshold

        report = ConsensusReport(
            timestamp=time.time(),
            witness_ids=witness_ids,
            merkle_roots={wid: a.merkle_root for wid, a in self.attestations.items()},
            consensus_merkle=consensus_merkle if consensus_reached else None,
            consensus_count=consensus_count,
            consensus_reached=consensus_reached,
            divergences=[c for c in comparisons if not c.matches],
        )

        logger.info(
            "consensus_check_complete witnesses=%d consensus=%s divergences=%d",
            len(witness_ids),
            "OK" if consensus_reached else "FAILED",
            len(report.divergences),
        )

        return report

    def publish_consensus(self, report: ConsensusReport, output_file: str) -> None:
        """Publish consensus report to file (for git, mirrors, etc.).

        Args:
            report: ConsensusReport to publish
            output_file: Path to write JSON
        """
        with open(output_file, "w") as f:
            json.dump(asdict(report), f, indent=2)

        logger.info(
            "consensus_published file=%s consensus=%s",
            output_file,
            "OK" if report.consensus_reached else "FAILED",
        )

    def to_forensic_record(self) -> dict[str, Any]:
        """Export federation consensus check as forensic record.

        Returns dict suitable for attack_log.jsonl.
        """
        return {
            "event_type": "federation_consensus_check",
            "timestamp": time.time(),
            "witnesses_queried": len(self.witness_urls),
            "witnesses_responding": len(self.attestations),
            "attestations": [asdict(a) for a in self.attestations.values()],
            "comparisons": [asdict(c) for c in self.comparisons],
            "consensus_reached": len([c for c in self.comparisons if c.matches])
            > 0,
        }


class WitnessPublisher:
    """Publishes witness attestations to mirrors (git repos).

    ES: Publica atestaciones de testigos en repos espejo (git).

    Design:
    - Each witness publishes its checkpoint to git mirror
    - Mirror repos are distributed (GitHub, GitLab, self-hosted)
    - Auditor can clone mirrors and verify locally
    """

    def __init__(self, mirror_path: str) -> None:
        """Initialize publisher.

        Args:
            mirror_path: Local git mirror directory
        """
        self.mirror_path = mirror_path

    def publish_checkpoint(self, checkpoint: dict, filename: str) -> None:
        """Publish checkpoint to mirror repo.

        Args:
            checkpoint: Checkpoint dict
            filename: e.g., "checkpoint-2026-05-16T00-00-00.json"
        """
        import subprocess

        checkpoint_file = f"{self.mirror_path}/{filename}"

        # Write checkpoint
        with open(checkpoint_file, "w") as f:
            json.dump(checkpoint, f, indent=2)

        # Git add, commit, push
        try:
            subprocess.run(
                ["git", "-C", self.mirror_path, "add", filename],
                check=True,
            )
            subprocess.run(
                ["git", "-C", self.mirror_path, "commit", "-m", f"Checkpoint: {filename}"],
                check=True,
            )
            subprocess.run(
                ["git", "-C", self.mirror_path, "push", "origin", "main"],
                check=True,
                timeout=30,
            )
            logger.info("checkpoint_published file=%s", filename)
        except subprocess.CalledProcessError as e:
            logger.error("checkpoint_publication_failed error=%s", str(e))
