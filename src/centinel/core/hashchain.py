# Hashchain Module
# AUTO-DOC-INDEX
#
# ES: Índice rápido
#   1) Propósito del módulo
#   2) Componentes principales
#   3) Puntos de extensión
#
# EN: Quick index
#   1) Module purpose
#   2) Main components
#   3) Extension points
#
# Secciones / Sections:
#   - Configuración / Configuration
#   - Lógica principal / Core logic
#   - Integraciones / Integrations

"""Funciones para encadenar hashes de snapshots.

English:
    Helpers to chain snapshot hashes together.
"""

import hashlib
import logging
import string
from typing import Optional

logger = logging.getLogger(__name__)


def _is_valid_hex_hash(value: str) -> bool:
    if len(value) != 64:
        return False
    hex_chars = set(string.hexdigits.lower())
    return all(char in hex_chars for char in value)


def _build_hash_payload(canonical_json: str, previous_hash: Optional[str]) -> bytes:
    previous_hash_bytes = b""
    if previous_hash:
        normalized = previous_hash.strip().lower()
        previous_hash_bytes = normalized.encode("utf-8")
        if not _is_valid_hex_hash(normalized):
            logger.warning("hashchain_previous_hash_invalid value=%s", normalized)

    canonical_bytes = canonical_json.encode("utf-8")
    parts = [
        b"centinel-hashchain-v1",
        b"prev",
        str(len(previous_hash_bytes)).encode("utf-8"),
        previous_hash_bytes,
        b"payload",
        str(len(canonical_bytes)).encode("utf-8"),
        canonical_bytes,
    ]
    return b"|".join(parts)


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
    hasher.update(_build_hash_payload(canonical_json, previous_hash))
    return hasher.hexdigest()
