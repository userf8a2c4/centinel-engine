"""CNE-specific chaos testing helpers for polling simulations."""

from __future__ import annotations

import json
import logging
import random
from typing import Callable, Dict, Tuple

import requests

ScenarioResponse = Tuple[int, Dict[str, str], str]

SCENARIOS = (
    "rate_limit_429",
    "timeout_503",
    "malformed_json",
    "hash_altered",
    "proxy_fail",
    "server_error_503",
)


def select_scenario(rng: random.Random, level: str) -> str:
    """Select a chaos scenario for the given scope."""
    _ = level
    return rng.choice(SCENARIOS)


def build_polling_payload(scope: str, attempt: int) -> Dict[str, str]:
    """Build a polling payload with deterministic fields."""
    return {
        "scope": scope,
        "attempt": str(attempt),
        "hash": f"hash-{attempt}",
    }


def create_mock_callback(
    *,
    rng: random.Random,
    level: str,
    scope: str,
    attempt_counter: Dict[str, int],
    logger: logging.Logger,
) -> Callable[[requests.PreparedRequest], ScenarioResponse]:
    """Create a callback that simulates server behaviors without recording metrics."""

    def _callback(request: requests.PreparedRequest) -> ScenarioResponse:
        attempt_counter["count"] += 1
        scenario = select_scenario(rng, level)
        if scenario == "rate_limit_429":
            logger.warning("scenario=rate_limit_429 url=%s", request.url)
            return 429, {"Retry-After": "5"}, json.dumps({"error": "rate limit"})
        if scenario == "timeout_503":
            logger.warning("scenario=timeout_503 url=%s", request.url)
            raise requests.Timeout("simulated_timeout")
        if scenario == "malformed_json":
            logger.warning("scenario=malformed_json url=%s", request.url)
            return 200, {}, "{invalid-json"
        if scenario == "hash_altered":
            logger.warning("scenario=hash_altered url=%s", request.url)
            payload = build_polling_payload(scope, attempt_counter["count"])
            payload["hash"] = "tampered"
            return 200, {}, json.dumps(payload)
        if scenario == "proxy_fail":
            logger.warning("scenario=proxy_fail url=%s", request.url)
            raise requests.ProxyError("simulated_proxy_failure")
        if scenario == "server_error_503":
            logger.warning("scenario=server_error_503 url=%s", request.url)
            return 503, {}, json.dumps({"error": "server_error"})
        payload = build_polling_payload(scope, attempt_counter["count"])
        return 200, {}, json.dumps(payload)

    return _callback
