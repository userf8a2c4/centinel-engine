"""Healthcheck estricto para validar liveness/readiness real.

English:
    Strict healthcheck to validate real liveness/readiness.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Deque, Tuple

import boto3
import httpx
import psutil
from dateutil import parser as date_parser
from fastapi import APIRouter, FastAPI, HTTPException

from monitoring.alerts import dispatch_alert

logger = logging.getLogger(__name__)

DEFAULT_MAX_AGE_CHECKPOINT_SECONDS = 900
DEFAULT_MAX_CRITICAL_ERRORS = 3
DEFAULT_MEMORY_THRESHOLD = 0.85
DEFAULT_CPU_THRESHOLD = 0.90
DEFAULT_CPU_WINDOW_SECONDS = 300
DEFAULT_DIAGNOSTICS_HISTORY = 10

_diagnostics: Deque[dict[str, Any]] = deque(maxlen=DEFAULT_DIAGNOSTICS_HISTORY)
_critical_log_tracker: "CriticalLogTracker | None" = None


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning("invalid_env_int name=%s value=%s", name, raw)
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        logger.warning("invalid_env_float name=%s value=%s", name, raw)
        return default


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _parse_timestamp(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    if isinstance(value, str):
        try:
            parsed = date_parser.parse(value)
        except (ValueError, TypeError):
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    return None


def _get_s3_client():
    endpoint_url = os.getenv("STORAGE_ENDPOINT_URL")
    region = os.getenv("AWS_REGION", "us-east-1")
    return boto3.client("s3", endpoint_url=endpoint_url, region_name=region)


def _get_pending_actas_url() -> str:
    return os.getenv("PENDING_ACTAS_URL", "").strip()


def _get_pending_actas_prefix() -> str:
    return os.getenv("PENDING_ACTAS_PREFIX", "").strip()


def _get_bucket_name() -> str:
    return os.getenv("CHECKPOINT_BUCKET", "").strip()


def _get_checkpoint_key() -> str:
    return os.getenv("CHECKPOINT_KEY", "").strip()


def _get_expected_hash_env() -> str:
    return os.getenv("CHECKPOINT_EXPECTED_HASH", "").strip()


def _get_write_test_key() -> str:
    return os.getenv("STORAGE_WRITE_TEST_KEY", "healthcheck/write-test.txt").strip()


@dataclass
class ResourceSample:
    timestamp: datetime
    cpu: float
    memory: float


class ResourceSampler:
    def __init__(self, window_seconds: int) -> None:
        self._window_seconds = window_seconds
        self._samples: Deque[ResourceSample] = deque()

    def sample(self) -> Tuple[float, float]:
        now = _now_utc()
        cpu_percent = psutil.cpu_percent(interval=0.1) / 100.0
        memory_percent = psutil.virtual_memory().percent / 100.0
        self._samples.append(ResourceSample(now, cpu_percent, memory_percent))
        self._trim(now)
        return self._average()

    def _trim(self, now: datetime) -> None:
        window = self._window_seconds
        while self._samples and (now - self._samples[0].timestamp).total_seconds() > window:
            self._samples.popleft()

    def _average(self) -> Tuple[float, float]:
        if not self._samples:
            return (0.0, 0.0)
        cpu = sum(sample.cpu for sample in self._samples) / len(self._samples)
        memory = sum(sample.memory for sample in self._samples) / len(self._samples)
        return (cpu, memory)


class CriticalLogTracker(logging.Handler):
    def __init__(self, max_entries: int = 100) -> None:
        super().__init__()
        self._levels: Deque[int] = deque(maxlen=max_entries)

    def emit(self, record: logging.LogRecord) -> None:
        self._levels.append(record.levelno)

    def consecutive_critical(self) -> int:
        count = 0
        for level in reversed(self._levels):
            if level >= logging.CRITICAL:
                count += 1
            else:
                break
        return count


_resource_sampler = ResourceSampler(
    _env_int("CPU_WINDOW_SECONDS", DEFAULT_CPU_WINDOW_SECONDS)
)


def _ensure_critical_tracker() -> CriticalLogTracker:
    global _critical_log_tracker
    if _critical_log_tracker is None:
        _critical_log_tracker = CriticalLogTracker()
        logging.getLogger().addHandler(_critical_log_tracker)
    return _critical_log_tracker


def _record_diagnostic(ok: bool, message: str) -> None:
    _diagnostics.append(
        {"timestamp": _now_utc().isoformat(), "ok": ok, "message": message}
    )


def get_recent_health_diagnostics() -> list[dict[str, Any]]:
    return list(_diagnostics)


def _read_checkpoint() -> Tuple[bool, str, dict[str, Any]]:
    bucket = _get_bucket_name()
    key = _get_checkpoint_key()
    if not bucket or not key:
        return False, "checkpoint_storage_not_configured", {}

    s3 = _get_s3_client()
    try:
        response = s3.get_object(Bucket=bucket, Key=key)
    except Exception as exc:  # noqa: BLE001
        return False, f"checkpoint_read_failed error={exc}", {}

    body = response.get("Body")
    raw = body.read() if body else b""
    if not raw:
        return False, "checkpoint_empty", {}

    try:
        payload = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        return False, f"checkpoint_invalid_json error={exc}", {}

    return True, "checkpoint_read_ok", {"payload": payload, "raw": raw, "meta": response}


def _verify_checkpoint_integrity(checkpoint: dict[str, Any]) -> Tuple[bool, str]:
    payload = checkpoint.get("payload", {})
    raw = checkpoint.get("raw", b"")
    meta = checkpoint.get("meta", {})
    expected_hash = (
        _get_expected_hash_env()
        or meta.get("Metadata", {}).get("expected_hash", "")
        or payload.get("expected_hash")
        or payload.get("expectedHash")
    )
    if not expected_hash:
        return False, "checkpoint_expected_hash_missing"
    actual_hash = hashlib.sha256(raw).hexdigest()
    if actual_hash != expected_hash:
        return False, "checkpoint_hash_mismatch"
    payload_hash = payload.get("hash")
    if payload_hash and payload_hash != expected_hash:
        return False, "checkpoint_payload_hash_mismatch"
    return True, "checkpoint_hash_ok"


def _verify_checkpoint_age(checkpoint: dict[str, Any]) -> Tuple[bool, str]:
    payload = checkpoint.get("payload", {})
    timestamp = (
        payload.get("timestamp")
        or payload.get("timestamp_utc")
        or payload.get("updated_at")
        or payload.get("created_at")
    )
    parsed = _parse_timestamp(timestamp)
    if parsed is None:
        return False, "checkpoint_timestamp_missing"
    max_age = _env_int("MAX_AGE_CHECKPOINT_SECONDS", DEFAULT_MAX_AGE_CHECKPOINT_SECONDS)
    age_seconds = (_now_utc() - parsed).total_seconds()
    if age_seconds > max_age:
        return False, "checkpoint_stale"
    return True, "checkpoint_fresh"


def _check_pending_actas() -> Tuple[bool, str]:
    url = _get_pending_actas_url()
    prefix = _get_pending_actas_prefix()
    bucket = _get_bucket_name()

    if url:
        try:
            response = httpx.get(url, timeout=5.0)
        except Exception as exc:  # noqa: BLE001
            return False, f"queue_http_failed error={exc}"
        if response.status_code != 200:
            return False, f"queue_http_status status={response.status_code}"
        pending = 0
        try:
            data = response.json()
            if isinstance(data, dict):
                pending = int(
                    data.get("pending")
                    or data.get("pending_actas")
                    or data.get("count")
                    or 0
                )
            elif isinstance(data, list):
                pending = len(data)
        except (ValueError, TypeError):
            pending = 0
        if pending > 0:
            return True, f"pending_actas={pending}"
        return True, "queue_accessible_pending_zero"

    if prefix and bucket:
        s3 = _get_s3_client()
        try:
            response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=1)
        except Exception as exc:  # noqa: BLE001
            return False, f"queue_list_failed error={exc}"
        if response.get("KeyCount", 0) > 0:
            return True, "pending_actas_found"
        return True, "queue_accessible_pending_zero"

    return False, "queue_check_not_configured"


def _check_critical_errors() -> Tuple[bool, str]:
    tracker = _ensure_critical_tracker()
    consecutive = tracker.consecutive_critical()
    max_errors = _env_int("MAX_CRITICAL_ERRORS", DEFAULT_MAX_CRITICAL_ERRORS)
    if consecutive > max_errors:
        return False, f"critical_errors_exceeded count={consecutive}"
    return True, "critical_errors_ok"


def _check_resources() -> Tuple[bool, str]:
    cpu_avg, memory_avg = _resource_sampler.sample()
    memory_threshold = _env_float("MEMORY_THRESHOLD", DEFAULT_MEMORY_THRESHOLD)
    cpu_threshold = _env_float("CPU_THRESHOLD", DEFAULT_CPU_THRESHOLD)
    if memory_avg >= memory_threshold:
        return False, f"memory_threshold_exceeded value={memory_avg:.2f}"
    if cpu_avg >= cpu_threshold:
        return False, f"cpu_threshold_exceeded value={cpu_avg:.2f}"
    return True, "resources_ok"


def _check_storage_write() -> Tuple[bool, str]:
    bucket = _get_bucket_name()
    if not bucket:
        return False, "storage_bucket_missing"
    key = _get_write_test_key()
    s3 = _get_s3_client()
    payload = f"healthcheck {datetime.utcnow().isoformat()}".encode("utf-8")
    try:
        s3.put_object(Bucket=bucket, Key=key, Body=payload)
    except Exception as exc:  # noqa: BLE001
        return False, f"storage_write_failed error={exc}"
    return True, "storage_write_ok"


def is_healthy_strict() -> Tuple[bool, str]:
    """Evalúa un healthcheck estricto con diagnóstico detallado.

    Returns:
        Tuple[bool, str]: (estado, diagnóstico)
    """

    checks = []

    checkpoint_ok, checkpoint_msg, checkpoint = _read_checkpoint()
    checks.append((checkpoint_ok, checkpoint_msg))
    if checkpoint_ok:
        integrity_ok, integrity_msg = _verify_checkpoint_integrity(checkpoint)
        checks.append((integrity_ok, integrity_msg))
        if integrity_ok:
            age_ok, age_msg = _verify_checkpoint_age(checkpoint)
            checks.append((age_ok, age_msg))

    pending_ok, pending_msg = _check_pending_actas()
    checks.append((pending_ok, pending_msg))

    critical_ok, critical_msg = _check_critical_errors()
    checks.append((critical_ok, critical_msg))

    resources_ok, resources_msg = _check_resources()
    checks.append((resources_ok, resources_msg))

    write_ok, write_msg = _check_storage_write()
    checks.append((write_ok, write_msg))

    failed = [message for ok, message in checks if not ok]
    if failed:
        diagnostic = "; ".join(failed)
        logger.critical("strict_healthcheck_failed reason=%s", diagnostic)
        dispatch_alert(
            "CRITICAL",
            "Healthcheck estricto fallido",
            {
                "diagnostic": diagnostic,
                "checks": [{"ok": ok, "message": message} for ok, message in checks],
                "source": "strict_healthcheck",
            },
        )
        _record_diagnostic(False, diagnostic)
        return False, diagnostic

    diagnostic = "healthcheck_strict_ok"
    _record_diagnostic(True, diagnostic)
    return True, diagnostic


def register_strict_health_endpoints(app: FastAPI) -> None:
    router = APIRouter()

    @router.get("/healthz")
    def healthz() -> dict[str, str]:
        ok, message = is_healthy_strict()
        if not ok:
            raise HTTPException(status_code=503, detail=message)
        return {"status": "ok", "detail": message}

    @router.get("/ready")
    def ready() -> dict[str, str]:
        ok, message = is_healthy_strict()
        if not ok:
            raise HTTPException(status_code=503, detail=message)
        return {"status": "ready", "detail": message}

    @router.get("/live")
    def live() -> dict[str, str]:
        return {"status": "alive"}

    app.include_router(router)
