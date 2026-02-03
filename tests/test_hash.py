"""Pruebas unitarias de hashing encadenado.

Unit tests for chained hashing.
"""

import hashlib

from sentinel.core.hashchain import compute_hash


def test_compute_hash_matches_sha256_for_single_payload():
    """Español: Función test_compute_hash_matches_sha256_for_single_payload del módulo tests/test_hash.py.

    English: Function test_compute_hash_matches_sha256_for_single_payload defined in tests/test_hash.py.
    """
    payload = '{"key": "value"}'
    expected = hashlib.sha256(payload.encode("utf-8")).hexdigest()

    assert compute_hash(payload) == expected


def test_compute_hash_is_deterministic():
    """Español: Función test_compute_hash_is_deterministic del módulo tests/test_hash.py.

    English: Function test_compute_hash_is_deterministic defined in tests/test_hash.py.
    """
    payload = '{"id": 123, "status": "ok"}'

    assert compute_hash(payload) == compute_hash(payload)


def test_compute_hash_includes_previous_hash():
    """Español: Función test_compute_hash_includes_previous_hash del módulo tests/test_hash.py.

    English: Function test_compute_hash_includes_previous_hash defined in tests/test_hash.py.
    """
    payload = '{"key": "value"}'
    previous_hash = compute_hash(payload)
    chained_hash = compute_hash(payload, previous_hash=previous_hash)

    assert chained_hash != previous_hash
    assert chained_hash == compute_hash(payload, previous_hash=previous_hash)
