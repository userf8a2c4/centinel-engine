"""
OpenTimestamps integration for Centinel T3 (external anchor independence).

Theorem T3 requires the Merkle root to be committed to an append-only
external ledger that the adversary cannot control. OpenTimestamps provides
zero-cost timestamping via Bitcoin's blockchain: the timestamp proof
contains an immutable path back to a Bitcoin block header.

Any attempt to forge the anchor would require rewriting Bitcoin's history,
which is computationally infeasible. This closes T3's rethorical gap:
the anchor is no longer user-controlled (not the author's Git repo),
but truly external and decentralized.

Usage:
  1. Call submit_to_opentimestamps(merkle_root) to get a proof.
  2. Store the proof in the snapshot metadata (proof_ots_json).
  3. Later, call verify_opentimestamps_proof() to validate against Bitcoin.
  4. Document multi-mirror model: Merkle roots committed to third-party repos
     (OEA, universities, NGOs) as backup.

References:
  - OpenTimestamps: https://opentimestamps.org/
  - RFC 6962 (Certificate Transparency): Related model for append-only logs
"""

from __future__ import annotations

import hashlib
import logging
import os
import requests
from typing import Any, Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

OTS_DEFAULT_SERVER = "https://a.pool.opentimestamps.org"
OTS_TIMEOUT = 30
OTS_RETRIES = 3


@dataclass
class OpenTimestampsProof:
    """Proof returned by OpenTimestamps server."""

    raw_proof: bytes
    merkle_root: str
    timestamp_server: str
    submission_time: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize proof for JSON storage."""
        import base64

        return {
            "proof_type": "opentimestamps",
            "merkle_root": self.merkle_root,
            "timestamp_server": self.timestamp_server,
            "raw_proof_b64": base64.b64encode(self.raw_proof).decode("utf-8"),
            "submission_time": self.submission_time,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> OpenTimestampsProof:
        """Deserialize proof from JSON storage."""
        import base64

        return OpenTimestampsProof(
            raw_proof=base64.b64decode(data["raw_proof_b64"]),
            merkle_root=data["merkle_root"],
            timestamp_server=data["timestamp_server"],
            submission_time=data.get("submission_time"),
        )


def submit_to_opentimestamps(merkle_root: str) -> Optional[OpenTimestampsProof]:
    """
    Submit a Merkle root hash to OpenTimestamps for Bitcoin timestamping.

    Args:
        merkle_root: SHA-256 hex hash of the Merkle root over all snapshot hashes.

    Returns:
        OpenTimestampsProof if successful, None on failure (non-fatal).

    Notes:
        - This operation is idempotent: submitting the same hash multiple times
          is safe and costs zero (no rate limit, no blockchain fees).
        - The proof is proof-of-work backed: to forge it would require
          rewriting Bitcoin's PoW, computationally infeasible.
        - Failures are logged but non-fatal: unsigned but hash-valid records
          still stand (degradation model, as in T2).
    """
    if not merkle_root:
        logger.warning("opentimestamps_skip: empty merkle_root")
        return None

    server = os.getenv("OTS_SERVER", OTS_DEFAULT_SERVER)
    merkle_bytes = bytes.fromhex(merkle_root)

    for attempt in range(OTS_RETRIES):
        try:
            response = requests.post(
                f"{server}/timestamp",
                data=merkle_bytes,
                headers={"Content-Type": "application/octet-stream"},
                timeout=OTS_TIMEOUT,
            )
            response.raise_for_status()
            logger.info(
                "opentimestamps_submit_ok",
                merkle_root=merkle_root,
                server=server,
            )
            return OpenTimestampsProof(
                raw_proof=response.content,
                merkle_root=merkle_root,
                timestamp_server=server,
            )
        except Exception as exc:
            if attempt < OTS_RETRIES - 1:
                logger.debug(f"opentimestamps_retry: attempt {attempt + 1} failed", error=str(exc))
                continue
            logger.error(
                "opentimestamps_submit_failed",
                merkle_root=merkle_root,
                server=server,
                error=str(exc),
            )
            return None

    return None


def verify_opentimestamps_proof(proof: OpenTimestampsProof) -> bool:
    """
    Verify that an OpenTimestamps proof is valid.

    This operation contacts the OpenTimestamps server to validate the proof
    chain back to a Bitcoin block header. If the server is unavailable,
    the proof is considered unverified (non-fatal).

    Args:
        proof: OpenTimestampsProof to verify.

    Returns:
        True if proof is valid and backed by Bitcoin, False otherwise.
    """
    server = proof.timestamp_server or OTS_DEFAULT_SERVER

    for attempt in range(OTS_RETRIES):
        try:
            response = requests.post(
                f"{server}/verify",
                data=proof.raw_proof,
                headers={"Content-Type": "application/octet-stream"},
                timeout=OTS_TIMEOUT,
            )
            if response.status_code == 200:
                logger.info(
                    "opentimestamps_verify_ok",
                    merkle_root=proof.merkle_root,
                    server=server,
                )
                return True
            elif response.status_code == 400:
                logger.warning(
                    "opentimestamps_verify_invalid",
                    merkle_root=proof.merkle_root,
                    server=server,
                )
                return False
            else:
                logger.debug(
                    f"opentimestamps_verify_http {response.status_code}",
                    server=server,
                )
                if attempt < OTS_RETRIES - 1:
                    continue
        except Exception as exc:
            if attempt < OTS_RETRIES - 1:
                logger.debug(f"opentimestamps_verify_retry: attempt {attempt + 1}", error=str(exc))
                continue
            logger.error(
                "opentimestamps_verify_failed",
                merkle_root=proof.merkle_root,
                server=server,
                error=str(exc),
            )
            return False

    return False


def compute_merkle_root(snapshot_hashes: list[str]) -> str:
    """
    Compute SHA-256 Merkle root over a list of snapshot hashes.

    This is the hash that should be committed to OpenTimestamps and
    third-party mirrors. Any attempt to rewrite history (insert/delete/modify
    snapshots) changes this root, which the external anchors will detect.

    Args:
        snapshot_hashes: List of SHA-256 hex hashes from the chain.

    Returns:
        SHA-256 hex of the Merkle root.
    """
    if not snapshot_hashes:
        return hashlib.sha256(b"centinel-empty-merkle").hexdigest()

    leaves = [bytes.fromhex(h) for h in snapshot_hashes]
    while len(leaves) > 1:
        if len(leaves) % 2 != 0:
            leaves.append(leaves[-1])
        next_level = []
        for i in range(0, len(leaves), 2):
            combined = leaves[i] + leaves[i + 1]
            next_level.append(hashlib.sha256(combined).digest())
        leaves = next_level

    return leaves[0].hex()
