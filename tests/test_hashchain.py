"""Pruebas básicas de la cadena de hashes.

Basic tests for the hash chain.
"""

from centinel.core.hashchain import compute_hash


def test_hash_is_stable():
    """Español: Función test_hash_is_stable del módulo tests/test_hashchain.py.

    English: Function test_hash_is_stable defined in tests/test_hashchain.py.
    """
    data = '{"a":1,"b":2}'
    h1 = compute_hash(data)
    h2 = compute_hash(data)

    assert h1 == h2


def test_hash_chain_changes():
    """Español: Función test_hash_chain_changes del módulo tests/test_hashchain.py.

    English: Function test_hash_chain_changes defined in tests/test_hashchain.py.
    """
    data = '{"a":1}'
    h1 = compute_hash(data)
    h2 = compute_hash(data, previous_hash=h1)

    assert h1 != h2
