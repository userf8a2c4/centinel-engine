from anchor.arbitrum_anchor import _obfuscate_identifier


def test_obfuscate_identifier_short_values_passthrough() -> None:
    assert _obfuscate_identifier("abc123") == "abc123"


def test_obfuscate_identifier_long_values_redacted() -> None:
    value = "0x1234567890abcdef"
    masked = _obfuscate_identifier(value)
    assert masked.startswith("0x1234")
    assert masked.endswith("cdef")
    assert "…" in masked
