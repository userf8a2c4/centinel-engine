from sentinel.core.hashchain import compute_hash


def test_compute_hash_is_deterministic() -> None:
    payload = "{\"status\": \"ok\"}"
    first = compute_hash(payload)
    second = compute_hash(payload)
    assert first == second
    assert len(first) == 64


def test_compute_hash_chain_changes_with_previous_hash() -> None:
    payload = "{\"status\": \"ok\"}"
    base_hash = compute_hash(payload)
    chained_hash = compute_hash(payload, previous_hash=base_hash)
    assert base_hash != chained_hash
    assert len(chained_hash) == 64
