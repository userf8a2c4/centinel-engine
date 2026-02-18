# Downloader Module
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

"""Downloader resiliente con reintentos configurables.

Resilient downloader with configurable retries.
"""

from __future__ import annotations

import importlib.util
import json
import logging
import os
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

import requests
import yaml
from tenacity import Retrying, retry_if_exception_type

structlog = None
if importlib.util.find_spec("structlog"):
    import structlog as _structlog

    structlog = _structlog


DEFAULT_RETRY_CONFIG_PATH = Path("config/prod/retry_config.yaml")
DEFAULT_FAILED_REQUESTS_PATH = Path("failed_requests.jsonl")
DEFAULT_TIMEOUT_SECONDS = 30.0
_secure_random = secrets.SystemRandom()


@dataclass(frozen=True)
class RetryPolicy:
    """Retry policy definition per status/exception.

    English: Defines max attempts and backoff/jitter behavior for retries.
    """

    max_attempts: int = 5
    backoff_base: float = 2.0
    backoff_multiplier: float = 2.0
    max_delay: float = 300.0
    jitter_min: float = 0.0
    jitter_max: float = 0.0
    action: str = "retry"

    def compute_delay(self, attempt_number: int) -> float:
        """Compute exponential delay with jitter.

        English: Exponential delay with randomized jitter for backoff.
        """
        exponential = self.backoff_base * (self.backoff_multiplier ** (attempt_number - 1))
        capped = min(exponential, self.max_delay)
        if self.jitter_max <= 0:
            return capped
        jitter_fraction = _secure_random.uniform(self.jitter_min, self.jitter_max)
        jitter_multiplier = _secure_random.uniform(1.0 - jitter_fraction, 1.0 + jitter_fraction)
        return max(0.0, capped * jitter_multiplier)


@dataclass
class RetryConfig:
    """Runtime retry configuration loaded from YAML.

    English: Holds default/per-status/per-exception policies and metadata.
    """

    default_policy: RetryPolicy
    per_status: dict[str, RetryPolicy] = field(default_factory=dict)
    per_exception: dict[str, RetryPolicy] = field(default_factory=dict)
    other_status: RetryPolicy | None = None
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    failed_requests_path: Path = DEFAULT_FAILED_REQUESTS_PATH
    recent_snapshot_seconds: int = 0
    idempotency_mode: str = "timestamp"
    log_payload_bytes: int = 2_000

    def policy_for_status(self, status_code: int) -> RetryPolicy:
        """Resolve policy for a given HTTP status code.

        English: Uses exact match first, then class (e.g., 5xx), then fallback.
        """
        exact_key = str(status_code)
        if exact_key in self.per_status:
            return self.per_status[exact_key]
        if 500 <= status_code <= 599 and "5xx" in self.per_status:
            return self.per_status["5xx"]
        if 400 <= status_code <= 499 and "4xx" in self.per_status:
            return self.per_status["4xx"]
        if self.other_status:
            return self.other_status
        return self.default_policy

    def policy_for_exception(self, exc: BaseException) -> RetryPolicy:
        """Resolve policy based on exception type.

        English: Matches by class name for YAML-friendly configuration.
        """
        exc_name = exc.__class__.__name__
        return self.per_exception.get(exc_name, self.default_policy)


class RetryableError(Exception):
    """Base class for retryable errors used by tenacity.

    English: Wraps a policy so wait/stop decisions can be dynamic.
    """

    def __init__(
        self,
        message: str,
        policy: RetryPolicy,
        *,
        context: dict[str, Any] | None = None,
    ):
        """Español: Función __init__ del módulo src/centinel/downloader.py.

        English: Function __init__ defined in src/centinel/downloader.py.
        """
        super().__init__(message)
        self.policy = policy
        self.context = context or {}


class RetryableStatusError(RetryableError):
    """Retryable HTTP status error."""

    def __init__(
        self,
        status_code: int,
        policy: RetryPolicy,
        response_text: str | None = None,
        *,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Español: Función __init__ del módulo src/centinel/downloader.py.

        English: Function __init__ defined in src/centinel/downloader.py.
        """
        message = f"retryable_status={status_code}"
        super().__init__(message, policy, context=context)
        self.status_code = status_code
        self.response_text = response_text


class RetryableExceptionError(RetryableError):
    """Retryable transport/timeout error."""


class RetryableParsingError(RetryableError):
    """Retryable JSON parsing error."""

    def __init__(
        self,
        message: str,
        policy: RetryPolicy,
        response_text: str | None = None,
        *,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Español: Función __init__ del módulo src/centinel/downloader.py.

        English: Function __init__ defined in src/centinel/downloader.py.
        """
        super().__init__(message, policy, context=context)
        self.response_text = response_text


class NonRetryableStatusError(Exception):
    """Non-retryable HTTP status error."""

    def __init__(self, status_code: int, response_text: str | None = None) -> None:
        """Español: Función __init__ del módulo src/centinel/downloader.py.

        English: Function __init__ defined in src/centinel/downloader.py.
        """
        super().__init__(f"non_retryable_status={status_code}")
        self.status_code = status_code
        self.response_text = response_text


class PolicyWait:
    """Dynamic wait strategy driven by policy attached to exceptions."""

    def __call__(self, retry_state) -> float:
        """Español: Función __call__ del módulo src/centinel/downloader.py.

        English: Function __call__ defined in src/centinel/downloader.py.
        """
        outcome = retry_state.outcome
        if outcome is None or not outcome.failed:
            return 0.0
        exc = outcome.exception()
        if isinstance(exc, RetryableError):
            return exc.policy.compute_delay(retry_state.attempt_number)
        return 0.0


class PolicyStop:
    """Dynamic stop strategy based on per-error max_attempts."""

    def __call__(self, retry_state) -> bool:
        """Español: Función __call__ del módulo src/centinel/downloader.py.

        English: Function __call__ defined in src/centinel/downloader.py.
        """
        outcome = retry_state.outcome
        if outcome is None:
            return False
        if not outcome.failed:
            return False
        exc = outcome.exception()
        if isinstance(exc, RetryableError):
            return retry_state.attempt_number >= exc.policy.max_attempts
        return True


class StructuredLogger:
    """Lightweight wrapper to support structlog or stdlib logging."""

    def __init__(self, name: str) -> None:
        """Español: Función __init__ del módulo src/centinel/downloader.py.

        English: Function __init__ defined in src/centinel/downloader.py.
        """
        if structlog is not None:
            self._logger = structlog.get_logger(name)
            self._use_structlog = True
        else:
            self._logger = logging.getLogger(name)
            self._use_structlog = False

    def info(self, event: str, **fields: Any) -> None:
        """Español: Función info del módulo src/centinel/downloader.py.

        English: Function info defined in src/centinel/downloader.py.
        """
        if self._use_structlog:
            self._logger.info(event, **fields)
        else:
            self._logger.info("%s %s", event, fields)

    def warning(self, event: str, **fields: Any) -> None:
        """Español: Función warning del módulo src/centinel/downloader.py.

        English: Function warning defined in src/centinel/downloader.py.
        """
        if self._use_structlog:
            self._logger.warning(event, **fields)
        else:
            self._logger.warning("%s %s", event, fields)

    def error(self, event: str, **fields: Any) -> None:
        """Español: Función error del módulo src/centinel/downloader.py.

        English: Function error defined in src/centinel/downloader.py.
        """
        if self._use_structlog:
            self._logger.error(event, **fields)
        else:
            self._logger.error("%s %s", event, fields)

    def debug(self, event: str, **fields: Any) -> None:
        """Español: Función debug del módulo src/centinel/downloader.py.

        English: Function debug defined in src/centinel/downloader.py.
        """
        if self._use_structlog:
            self._logger.debug(event, **fields)
        else:
            self._logger.debug("%s %s", event, fields)


def _parse_jitter(value: Any) -> tuple[float, float]:
    """Parse jitter configuration to a min/max range.

    English: Accepts float, list/tuple, or dict with min/max.
    """
    if value is None:
        return 0.0, 0.0
    if isinstance(value, (list, tuple)) and len(value) == 2:
        return float(value[0]), float(value[1])
    if isinstance(value, Mapping):
        return float(value.get("min", 0.0)), float(value.get("max", 0.0))
    return float(value), float(value)


def _parse_policy(raw: Mapping[str, Any], fallback: RetryPolicy) -> RetryPolicy:
    """Create RetryPolicy from YAML fragment.

    English: Missing keys fall back to the default policy.
    """
    jitter_min, jitter_max = _parse_jitter(raw.get("jitter"))
    return RetryPolicy(
        max_attempts=int(raw.get("max_attempts", fallback.max_attempts)),
        backoff_base=float(raw.get("backoff_base", fallback.backoff_base)),
        backoff_multiplier=float(raw.get("backoff_multiplier", fallback.backoff_multiplier)),
        max_delay=float(raw.get("max_delay", fallback.max_delay)),
        jitter_min=jitter_min,
        jitter_max=jitter_max,
        action=str(raw.get("action", fallback.action)),
    )


def load_retry_config(path: str | Path | None = None) -> RetryConfig:
    """Load retry configuration from YAML.

    English: Falls back to built-in defaults when file is missing.
    """
    config_path = Path(path) if path else Path(os.getenv("RETRY_CONFIG_PATH", ""))
    if not config_path or str(config_path).strip() == "":
        config_path = DEFAULT_RETRY_CONFIG_PATH

    payload: dict[str, Any] = {}
    if config_path.exists():
        payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}

    default_raw = payload.get("default", {}) if isinstance(payload, dict) else {}
    default_policy = _parse_policy(default_raw, RetryPolicy())

    per_status: dict[str, RetryPolicy] = {}
    for key, value in (payload.get("per_status") or {}).items():
        if isinstance(value, Mapping):
            per_status[str(key)] = _parse_policy(value, default_policy)

    per_exception: dict[str, RetryPolicy] = {}
    for key, value in (payload.get("per_exception") or {}).items():
        if isinstance(value, Mapping):
            per_exception[str(key)] = _parse_policy(value, default_policy)

    other_status = None
    if isinstance(payload.get("other_status"), Mapping):
        other_status = _parse_policy(payload["other_status"], default_policy)

    timeout_seconds = float(payload.get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS))
    failed_requests_path = Path(payload.get("failed_requests_path", DEFAULT_FAILED_REQUESTS_PATH))
    recent_snapshot_seconds = int(payload.get("recent_snapshot_seconds", 0))
    idempotency_mode = str(payload.get("idempotency_mode", "timestamp"))
    log_payload_bytes = int(payload.get("log_payload_bytes", 2_000))

    return RetryConfig(
        default_policy=default_policy,
        per_status=per_status,
        per_exception=per_exception,
        other_status=other_status,
        timeout_seconds=timeout_seconds,
        failed_requests_path=failed_requests_path,
        recent_snapshot_seconds=recent_snapshot_seconds,
        idempotency_mode=idempotency_mode,
        log_payload_bytes=log_payload_bytes,
    )


def _write_failed_request(config: RetryConfig, payload: dict[str, Any]) -> None:
    """Append failed request payload to JSONL.

    English: This is best-effort and should never raise.
    """
    try:
        config.failed_requests_path.parent.mkdir(parents=True, exist_ok=True)
        with config.failed_requests_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False))
            handle.write("\n")
    except Exception as exc:
        logging.getLogger("centinel.downloader").warning(
            "failed_requests_write_failed",
            extra={"path": str(config.failed_requests_path), "error": str(exc)},
        )


def _build_failed_payload(
    *,
    url: str,
    method: str,
    attempts: int,
    error: str,
    status_code: int | None = None,
    response_text: str | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build JSONL payload for failed requests file."""
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "url": url,
        "method": method,
        "attempts": attempts,
        "status_code": status_code,
        "error": error,
        "response_text": response_text,
        "context": context or {},
    }


def _extract_response_text(response: requests.Response | None, limit: int) -> str | None:
    """Safely extract a bounded response body for logs."""
    if response is None:
        return None
    try:
        text = response.text
    except Exception:
        return None
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def _log_before_sleep(logger: StructuredLogger, retry_state) -> None:
    """Log retry sleep with attempt metadata."""
    outcome = retry_state.outcome
    if outcome is None or not outcome.failed:
        return
    exc = outcome.exception()
    if isinstance(exc, RetryableError):
        wait_seconds = getattr(getattr(retry_state, "next_action", None), "sleep", None)
        if wait_seconds is None:
            wait_seconds = exc.policy.compute_delay(retry_state.attempt_number)
        logger.warning(
            "retry_sleep",
            attempt=retry_state.attempt_number,
            max_attempts=exc.policy.max_attempts,
            wait_seconds=wait_seconds,
            error=str(exc),
            context=exc.context,
        )


def _perform_request(
    session: requests.Session,
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None,
    timeout: float,
    retry_config: RetryConfig,
    logger: StructuredLogger,
    context: dict[str, Any],
    alert_hook: Callable[[str, dict[str, Any]], None] | None,
) -> requests.Response:
    """Perform a single HTTP request and map failures to retryable errors."""
    try:
        request_kwargs = {"timeout": timeout}
        if headers:
            request_kwargs["headers"] = headers
        if method.upper() == "GET":
            response = session.get(url, **request_kwargs)
        else:
            response = session.request(method, url, **request_kwargs)
    except (
        requests.exceptions.ConnectionError,
        requests.exceptions.ReadTimeout,
        requests.exceptions.SSLError,
    ) as exc:
        policy = retry_config.policy_for_exception(exc)
        raise RetryableExceptionError(str(exc), policy, context=context) from exc
    except requests.exceptions.RequestException as exc:
        policy = retry_config.policy_for_exception(exc)
        raise RetryableExceptionError(str(exc), policy, context=context) from exc

    if response.status_code >= 400:
        policy = retry_config.policy_for_status(response.status_code)
        if policy.action == "alert_only" and alert_hook:
            alert_hook(
                "retry_alert",
                {
                    "status_code": response.status_code,
                    "url": url,
                    "context": context,
                },
            )
        response_text = _extract_response_text(response, retry_config.log_payload_bytes)
        if policy.max_attempts <= 1 or policy.action == "fail_fast":
            raise NonRetryableStatusError(response.status_code, response_text)
        raise RetryableStatusError(
            response.status_code,
            policy,
            response_text=response_text,
            context=context,
        )

    return response


def _request_with_retry(
    session: requests.Session,
    url: str,
    *,
    retry_config: RetryConfig,
    timeout: float,
    headers: dict[str, str] | None,
    logger: StructuredLogger,
    context: dict[str, Any],
    alert_hook: Callable[[str, dict[str, Any]], None] | None,
    parse_json: bool,
) -> tuple[requests.Response, Any | None]:
    """Shared retry loop for JSON and raw requests."""
    retrying = Retrying(
        retry=retry_if_exception_type(RetryableError),
        wait=PolicyWait(),
        stop=PolicyStop(),
        before_sleep=lambda state: _log_before_sleep(logger, state),
        reraise=True,
    )

    try:
        for attempt in retrying:
            with attempt:
                logger.info(
                    "request_attempt",
                    attempt=attempt.retry_state.attempt_number,
                    url=url,
                    context=context,
                )
                start = time.monotonic()
                response = _perform_request(
                    session,
                    "GET",
                    url,
                    headers=headers,
                    timeout=timeout,
                    retry_config=retry_config,
                    logger=logger,
                    context=context,
                    alert_hook=alert_hook,
                )
                elapsed = time.monotonic() - start
                payload = None
                if parse_json:
                    try:
                        payload = response.json()
                    except (json.JSONDecodeError, ValueError) as exc:
                        policy = retry_config.policy_for_exception(exc)
                        response_text = _extract_response_text(response, retry_config.log_payload_bytes)
                        logger.warning(
                            "json_parse_error",
                            url=url,
                            error=str(exc),
                            response_text=response_text,
                            context=context,
                        )
                        raise RetryableParsingError(
                            "json_parse_error",
                            policy,
                            response_text=response_text,
                            context=context,
                        ) from exc
                success_fields: dict[str, Any] = {
                    "url": url,
                    "status_code": response.status_code,
                    "elapsed_seconds": round(elapsed, 3),
                    "context": context,
                }
                if parse_json and payload is not None:
                    success_fields["payload_type"] = type(payload).__name__
                logger.info("request_success", **success_fields)
                return response, payload
    except Exception as exc:
        status_code = getattr(exc, "status_code", None)
        response_text = getattr(exc, "response_text", None)
        attempts = getattr(retrying, "statistics", {}).get("attempt_number", 0)
        logger.error(
            "request_failed",
            url=url,
            status_code=status_code,
            attempts=attempts or 1,
            error=str(exc),
            context=context,
        )
        failed_payload = _build_failed_payload(
            url=url,
            method="GET",
            attempts=attempts or 1,
            error=str(exc),
            status_code=status_code,
            response_text=response_text,
            context=context,
        )
        _write_failed_request(retry_config, failed_payload)
        raise


def request_json_with_retry(
    session: requests.Session,
    url: str,
    *,
    retry_config: RetryConfig,
    timeout: float | None = None,
    headers: dict[str, str] | None = None,
    logger: StructuredLogger | None = None,
    context: dict[str, Any] | None = None,
    alert_hook: Callable[[str, dict[str, Any]], None] | None = None,
) -> tuple[requests.Response, Any]:
    """Request JSON content with retryable errors and parsing protection."""
    logger = logger or StructuredLogger("centinel.downloader")
    context = context or {}
    timeout = timeout or retry_config.timeout_seconds
    response, payload = _request_with_retry(
        session,
        url,
        retry_config=retry_config,
        timeout=timeout,
        headers=headers,
        logger=logger,
        context=context,
        alert_hook=alert_hook,
        parse_json=True,
    )
    return response, payload


def request_with_retry(
    session: requests.Session,
    url: str,
    *,
    retry_config: RetryConfig,
    timeout: float | None = None,
    headers: dict[str, str] | None = None,
    logger: StructuredLogger | None = None,
    context: dict[str, Any] | None = None,
    alert_hook: Callable[[str, dict[str, Any]], None] | None = None,
) -> requests.Response:
    """Request content with retries but without JSON parsing.

    English: Use when the caller manages parsing or stores raw payloads.
    """
    logger = logger or StructuredLogger("centinel.downloader")
    context = context or {}
    timeout = timeout or retry_config.timeout_seconds
    response, _ = _request_with_retry(
        session,
        url,
        retry_config=retry_config,
        timeout=timeout,
        headers=headers,
        logger=logger,
        context=context,
        alert_hook=alert_hook,
        parse_json=False,
    )
    return response


def should_skip_snapshot(data_dir: Path, source_id: str, *, retry_config: RetryConfig) -> bool:
    """Check idempotency rules to avoid duplicate downloads.

    English: Skips if a recent snapshot already exists for the source.

    data_dir ya apunta al subdirectorio de la fuente (e.g. data/snapshots/NACIONAL/).
    data_dir already points to the source subdirectory (e.g. data/snapshots/NACIONAL/).
    """
    if retry_config.recent_snapshot_seconds <= 0:
        return False
    pattern = "snapshot_*.json"
    candidates = sorted(data_dir.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        return False
    latest = candidates[0]
    age_seconds = max(
        0.0,
        (datetime.now(timezone.utc) - datetime.fromtimestamp(latest.stat().st_mtime, tz=timezone.utc)).total_seconds(),
    )
    return age_seconds <= retry_config.recent_snapshot_seconds


def build_alert_hook(logger: StructuredLogger) -> Callable[[str, dict[str, Any]], None]:
    """Builds a minimal alert hook for retry warnings.

    English: Hook can be replaced by higher-level alerting systems.
    """

    def _alert(event: str, payload: dict[str, Any]) -> None:
        """Español: Función _alert del módulo src/centinel/downloader.py.

        English: Function _alert defined in src/centinel/downloader.py.
        """
        logger.warning(event, **payload)

    return _alert
