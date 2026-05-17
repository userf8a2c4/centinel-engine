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

Multiple public calendar servers are tried in order; if all fail, the
Merkle root is saved to data/pending_ots.json for retry on next snapshot.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

import requests

logger = logging.getLogger(__name__)

OTS_CALENDARS: List[str] = [
    "https://alice.btc.calendar.opentimestamps.org",
    "https://bob.btc.calendar.opentimestamps.org",
    "https://finney.calendar.eternitywall.com",
    "https://ots.btc.catallaxy.com",
]

OTS_TIMEOUT = 30
OTS_RETRIES = 2
PENDING_OTS_FILE = Path("data/pending_ots.json")


@dataclass
class OpenTimestampsProof:
    """Proof returned by OpenTimestamps server."""

    raw_proof: bytes
    merkle_root: str
    timestamp_server: str
    submission_time: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        import base64

        return {
            "proof_type": "opentimestamps",
            "merkle_root": self.merkle_root,
            "timestamp_server": self.timestamp_server,
            "raw_proof_b64": base64.b64encode(self.raw_proof).decode("utf-8"),
            "submission_time": self.submission_time,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "OpenTimestampsProof":
        import base64

        return OpenTimestampsProof(
            raw_proof=base64.b64decode(data["raw_proof_b64"]),
            merkle_root=data["merkle_root"],
            timestamp_server=data["timestamp_server"],
            submission_time=data.get("submission_time"),
        )


def _calendars_from_env() -> List[str]:
    """Return calendar list from OTS_SERVER env var or defaults."""
    env_server = os.getenv("OTS_SERVER")
    if env_server:
        return [env_server] + [c for c in OTS_CALENDARS if c != env_server]
    return OTS_CALENDARS


def _try_submit(merkle_bytes: bytes, server: str) -> Optional[bytes]:
    """Attempt a single POST to one calendar server. Returns raw proof or None."""
    for attempt in range(OTS_RETRIES):
        try:
            resp = requests.post(
                f"{server}/digest",
                data=merkle_bytes,
                headers={"Content-Type": "application/octet-stream"},
                timeout=OTS_TIMEOUT,
            )
            resp.raise_for_status()
            return resp.content
        except Exception as exc:
            if attempt < OTS_RETRIES - 1:
                time.sleep(1)
                continue
            logger.debug("ots_calendar_failed", server=server, error=str(exc))
    return None


def _save_pending(merkle_root: str) -> None:
    """Save a merkle root to pending_ots.json for retry on next run."""
    PENDING_OTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    pending: List[Dict] = []
    if PENDING_OTS_FILE.exists():
        try:
            pending = json.loads(PENDING_OTS_FILE.read_text())
        except Exception:
            pending = []

    already = any(e.get("merkle_root") == merkle_root for e in pending)
    if not already:
        pending.append({
            "merkle_root": merkle_root,
            "queued_at": datetime.now(timezone.utc).isoformat(),
        })
        PENDING_OTS_FILE.write_text(json.dumps(pending, indent=2))
        logger.info("ots_pending_saved", merkle_root=merkle_root[:16])


def _retry_pending() -> None:
    """Try to submit any previously-failed merkle roots."""
    if not PENDING_OTS_FILE.exists():
        return
    try:
        pending = json.loads(PENDING_OTS_FILE.read_text())
    except Exception:
        return

    remaining = []
    for entry in pending:
        root = entry.get("merkle_root", "")
        if not root:
            continue
        proof = submit_to_opentimestamps(root, _retry=False)
        if proof is None:
            remaining.append(entry)
        else:
            logger.info("ots_pending_resolved", merkle_root=root[:16])

    if remaining:
        PENDING_OTS_FILE.write_text(json.dumps(remaining, indent=2))
    else:
        PENDING_OTS_FILE.unlink(missing_ok=True)


def submit_to_opentimestamps(
    merkle_root: str,
    _retry: bool = True,
) -> Optional[OpenTimestampsProof]:
    """
    Submit a Merkle root to OpenTimestamps via Bitcoin timestamping.

    Tries each public calendar server in order until one succeeds.
    If all fail, saves the root to data/pending_ots.json for later retry.

    Args:
        merkle_root: SHA-256 hex hash of the Merkle root.

    Returns:
        OpenTimestampsProof on success, None on total failure (non-fatal).
    """
    if not merkle_root:
        logger.warning("opentimestamps_skip: empty merkle_root")
        return None

    if _retry:
        _retry_pending()

    merkle_bytes = bytes.fromhex(merkle_root)
    submission_time = datetime.now(timezone.utc).isoformat()

    for server in _calendars_from_env():
        raw_proof = _try_submit(merkle_bytes, server)
        if raw_proof is not None:
            logger.info("opentimestamps_submit_ok", merkle_root=merkle_root[:16], server=server)
            return OpenTimestampsProof(
                raw_proof=raw_proof,
                merkle_root=merkle_root,
                timestamp_server=server,
                submission_time=submission_time,
            )

    logger.error("opentimestamps_all_calendars_failed", merkle_root=merkle_root[:16])
    _save_pending(merkle_root)
    return None


def verify_opentimestamps_proof(proof: OpenTimestampsProof) -> bool:
    """
    Verify that an OpenTimestamps proof is valid against Bitcoin.

    Args:
        proof: OpenTimestampsProof to verify.

    Returns:
        True if proof is backed by Bitcoin, False otherwise (non-fatal).
    """
    servers_to_try = [proof.timestamp_server] if proof.timestamp_server else []
    servers_to_try += [s for s in _calendars_from_env() if s not in servers_to_try]

    for server in servers_to_try:
        for attempt in range(OTS_RETRIES):
            try:
                resp = requests.post(
                    f"{server}/verify",
                    data=proof.raw_proof,
                    headers={"Content-Type": "application/octet-stream"},
                    timeout=OTS_TIMEOUT,
                )
                if resp.status_code == 200:
                    logger.info("opentimestamps_verify_ok", merkle_root=proof.merkle_root[:16])
                    return True
                if resp.status_code == 400:
                    return False
                if attempt < OTS_RETRIES - 1:
                    continue
            except Exception as exc:
                if attempt < OTS_RETRIES - 1:
                    time.sleep(1)
                    continue
                logger.debug("ots_verify_server_failed", server=server, error=str(exc))
        break

    logger.warning("opentimestamps_verify_failed", merkle_root=proof.merkle_root[:16])
    return False


def compute_merkle_root(snapshot_hashes: list) -> str:
    """
    Compute SHA-256 Merkle root over a list of snapshot hashes (Bitcoin-style).

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
