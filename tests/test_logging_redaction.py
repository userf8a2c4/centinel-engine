from __future__ import annotations

import logging

from centinel.utils.logging_config import SensitiveLogFilter, redact_sensitive_text


def test_redact_sensitive_text_masks_bearer_and_keys() -> None:
    text = "Authorization: Bearer abc.def.ghi api_key=SUPERSECRET ARBITRUM_PRIVATE_KEY=0x123"
    redacted = redact_sensitive_text(text)
    assert "SUPERSECRET" not in redacted
    assert "0x123" not in redacted
    assert "[REDACTED]" in redacted


def test_sensitive_log_filter_redacts_tuple_args() -> None:
    record = logging.LogRecord(
        name="centinel.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="token leak %s",
        args=("token=abcd",),
        exc_info=None,
    )
    filt = SensitiveLogFilter()
    assert filt.filter(record) is True
    assert "abcd" not in str(record.args)
