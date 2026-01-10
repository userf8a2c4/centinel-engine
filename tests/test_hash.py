import hashlib

from sentinel.core.hashchain import compute_hash


def test_compute_hash_matches_sha256_for_single_payload():
    payload = '{"key": "value"}'
    expected = hashlib.sha256(payload.encode("utf-8")).hexdigest()

    assert compute_hash(payload) == expected


def test_compute_hash_is_deterministic():
    payload = '{"id": 123, "status": "ok"}'

    assert compute_hash(payload) == compute_hash(payload)


def test_compute_hash_includes_previous_hash():
    payload = '{"key": "value"}'
    previous_hash = compute_hash(payload)
    chained_hash = compute_hash(payload, previous_hash=previous_hash)

    assert chained_hash != previous_hash
    assert chained_hash == compute_hash(payload, previous_hash=previous_hash)
