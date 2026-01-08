"""Funciones para encadenar hashes de snapshots.

English:
    Helpers to chain snapshot hashes together.
"""

import hashlib
from typing import Optional


def compute_hash(canonical_json: str, previous_hash: Optional[str] = None) -> str:
    """Calcula el hash SHA-256 de un snapshot canónico.

    Si se pasa un hash previo, lo concatena para mantener la cadena.

    Args:
        canonical_json (str): Snapshot en JSON canónico.
        previous_hash (Optional[str]): Hash anterior en la cadena.

    Returns:
        str: Hash SHA-256 resultante.

    English:
        Computes the SHA-256 hash for a canonical snapshot.

        If a previous hash is provided, it is included to keep the chain.

    Args:
        canonical_json (str): Snapshot in canonical JSON.
        previous_hash (Optional[str]): Previous hash in the chain.

    Returns:
        str: Resulting SHA-256 hash.
    """

    hasher = hashlib.sha256()

    if previous_hash:
        hasher.update(previous_hash.encode("utf-8"))

    hasher.update(canonical_json.encode("utf-8"))
    return hasher.hexdigest()
