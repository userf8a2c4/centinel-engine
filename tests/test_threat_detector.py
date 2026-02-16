from __future__ import annotations

from centinel_engine.threat_detector import (
    THREAT_NONE,
    THREAT_RATE_LIMIT,
    THREAT_SERVER_ERROR,
    THREAT_SUSPICIOUS_HEADER,
    ThreatDetector,
    evaluate_resilience_mode,
)


def test_detect_rate_limit_after_repeated_429_403() -> None:
    detector = ThreatDetector(config={})
    recent = [
        {"status_code": 429, "response_time": 0.2, "headers": {}, "error": "too many"},
        {"status_code": 429, "response_time": 0.2, "headers": {}, "error": "too many"},
        {"status_code": 403, "response_time": 0.2, "headers": {}, "error": "forbidden"},
        {"status_code": 429, "response_time": 0.2, "headers": {}, "error": "too many"},
    ]

    assert detector.detect_threats(recent) == THREAT_RATE_LIMIT


def test_detect_server_error_after_repeated_5xx() -> None:
    detector = ThreatDetector(config={})
    recent = [{"status_code": 503, "response_time": 0.4, "headers": {}, "error": "unavailable"} for _ in range(5)]

    assert detector.detect_threats(recent) == THREAT_SERVER_ERROR


def test_detect_suspicious_header() -> None:
    detector = ThreatDetector(config={})
    recent = [
        {
            "status_code": 200,
            "response_time": 0.1,
            "headers": {"Server": "Cloudflare", "x-note": "blocked"},
            "error": None,
        }
    ]

    assert detector.detect_threats(recent) == THREAT_SUSPICIOUS_HEADER


def test_evaluate_resilience_mode_extends_delay() -> None:
    result = evaluate_resilience_mode(
        metrics={"cpu_percent": 10, "error_rate": 0.01},
        recent_responses=[{"status_code": 503, "response_time": 0.3, "headers": {}, "error": "boom"} for _ in range(5)],
        config={},
    )

    assert result["mode"] == "critical"
    assert result["threat"] == THREAT_SERVER_ERROR
    assert result["delay_seconds"] >= 3600


def test_detect_none_when_clean() -> None:
    detector = ThreatDetector(config={})
    recent = [
        {"status_code": 200, "response_time": 0.1, "headers": {"Server": "nginx"}, "error": None},
        {"status_code": 304, "response_time": 0.1, "headers": {"Server": "nginx"}, "error": None},
    ]

    assert detector.detect_threats(recent) == THREAT_NONE
