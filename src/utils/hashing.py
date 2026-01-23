"""Hashing helpers for chained snapshot hashing."""

from __future__ import annotations

import hashlib


def compute_hash(payload: str, previous_hash: str | None = None) -> str:
    """Compute a SHA-256 hash from a payload and optional previous hash.

    Args:
        payload: Canonical JSON string or other payload.
        previous_hash: Previous hash in the chain.

    Returns:
        Hex-encoded SHA-256 hash.
    """
    hasher = hashlib.sha256()
    if previous_hash:
        hasher.update(previous_hash.encode("utf-8"))
    hasher.update(payload.encode("utf-8"))
    return hasher.hexdigest()
