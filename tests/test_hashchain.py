from sentinel.core.hashchain import compute_hash


def test_hash_is_stable():
    data = '{"a":1,"b":2}'
    h1 = compute_hash(data)
    h2 = compute_hash(data)

    assert h1 == h2


def test_hash_chain_changes():
    data = '{"a":1}'
    h1 = compute_hash(data)
    h2 = compute_hash(data, previous_hash=h1)

    assert h1 != h2
