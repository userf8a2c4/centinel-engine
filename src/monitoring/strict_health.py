"""Healthcheck estricto para validar liveness/readiness real.

English:
    Strict healthcheck to validate real liveness/readiness.

Ejemplo de respuesta cuando falla:
    {
      "healthy": false,
      "timestamp": "2024-01-01T12:00:00Z",
      "failures": [
        "checkpoint_integrity_failed",
        "resources_threshold_exceeded"
      ],
      "checks": {
        "checkpoint": {"ok": false, "message": "checkpoint_integrity_failed"},
        "resources": {"ok": false, "cpu_avg": 0.95, "memory_avg": 0.90}
      }
    }
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Deque, Tuple

import boto3
import psutil
from botocore.config import Config
from dateutil import parser as date_parser
from fastapi import APIRouter, FastAPI
from fastapi.responses import JSONResponse

from centinel.checkpointing import CheckpointConfig, CheckpointManager

logger = logging.getLogger(__name__)

DEFAULT_MAX_CHECKPOINT_AGE_SECONDS = 1200
DEFAULT_MAX_CRITICAL_ERRORS = 4
DEFAULT_MEMORY_THRESHOLD = 0.85
DEFAULT_CPU_THRESHOLD = 0.90
DEFAULT_CPU_WINDOW_SECONDS = 300
DEFAULT_DIAGNOSTICS_HISTORY = 10
DEFAULT_LAST_ACTA_MAX_AGE_SECONDS = 900
DEFAULT_BUCKET_LATENCY_SECONDS = 5
DEFAULT_CRITICAL_WINDOW_SECONDS = 1800

_diagnostics: Deque[dict[str, Any]] = deque(maxlen=DEFAULT_DIAGNOSTICS_HISTORY)
_critical_log_tracker: "CriticalLogTracker | None" = None


def _env_int(name: str, default: int, fallbacks: tuple[str, ...] = ()) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        for fallback in fallbacks:
            raw = os.getenv(fallback, "").strip()
            if raw:
                break
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning("invalid_env_int name=%s value=%s", name, raw)
        return default


def _env_float(name: str, default: float, fallbacks: tuple[str, ...] = ()) -> float:
    raw = os.getenv(name, "").strip()
    if not raw:
        for fallback in fallbacks:
            raw = os.getenv(fallback, "").strip()
            if raw:
                break
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


def _build_s3_config() -> Config:
    return Config(connect_timeout=DEFAULT_BUCKET_LATENCY_SECONDS, read_timeout=5, retries={"max_attempts": 2})


def _build_s3_client():
    endpoint_url = os.getenv("CENTINEL_S3_ENDPOINT") or os.getenv("STORAGE_ENDPOINT_URL")
    region = os.getenv("CENTINEL_S3_REGION") or os.getenv("AWS_REGION", "us-east-1")
    access_key = os.getenv("CENTINEL_S3_ACCESS_KEY") or os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("CENTINEL_S3_SECRET_KEY") or os.getenv("AWS_SECRET_ACCESS_KEY")
    session = boto3.session.Session()
    return session.client(
        "s3",
        endpoint_url=endpoint_url,
        region_name=region,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=_build_s3_config(),
    )


def _get_bucket_name() -> str:
    return (
        os.getenv("CENTINEL_CHECKPOINT_BUCKET")
        or os.getenv("CHECKPOINT_BUCKET")
        or ""
    ).strip()


def _get_pipeline_version() -> str:
    return (os.getenv("CENTINEL_PIPELINE_VERSION") or "").strip()


def _get_run_id() -> str:
    return (os.getenv("CENTINEL_RUN_ID") or "").strip()


def _get_write_test_key() -> str:
    return os.getenv("STORAGE_WRITE_TEST_KEY", "healthcheck/write-test.txt").strip()


def _get_checkpoint_manager() -> Tuple[CheckpointManager | None, str | None]:
    bucket = _get_bucket_name()
    pipeline_version = _get_pipeline_version()
    run_id = _get_run_id()
    if not bucket or not pipeline_version or not run_id:
        return None, "checkpoint_config_missing"

    config = CheckpointConfig(
        bucket=bucket,
        pipeline_version=pipeline_version,
        run_id=run_id,
        s3_endpoint_url=os.getenv("CENTINEL_S3_ENDPOINT") or os.getenv("STORAGE_ENDPOINT_URL"),
        s3_region=os.getenv("CENTINEL_S3_REGION") or os.getenv("AWS_REGION"),
        s3_access_key=os.getenv("CENTINEL_S3_ACCESS_KEY") or os.getenv("AWS_ACCESS_KEY_ID"),
        s3_secret_key=os.getenv("CENTINEL_S3_SECRET_KEY") or os.getenv("AWS_SECRET_ACCESS_KEY"),
    )

    try:
        manager = CheckpointManager(config, s3_client=_build_s3_client())
    except Exception as exc:  # noqa: BLE001
        return None, f"checkpoint_manager_init_failed error={exc}"

    return manager, None


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
    def __init__(self, max_entries: int = 200) -> None:
        super().__init__()
        self._entries: Deque[tuple[float, int]] = deque(maxlen=max_entries)

    def emit(self, record: logging.LogRecord) -> None:
        self._entries.append((record.created, record.levelno))

    def max_consecutive_critical(self, window_seconds: int) -> int:
        now = time.time()
        entries = [(ts, lvl) for ts, lvl in self._entries if now - ts <= window_seconds]
        max_consecutive = 0
        current = 0
        for _, level in entries:
            if level >= logging.CRITICAL:
                current += 1
                max_consecutive = max(max_consecutive, current)
            else:
                current = 0
        return max_consecutive


_resource_sampler = ResourceSampler(_env_int("CPU_WINDOW_SECONDS", DEFAULT_CPU_WINDOW_SECONDS))


def _ensure_critical_tracker() -> CriticalLogTracker:
    global _critical_log_tracker
    if _critical_log_tracker is None:
        _critical_log_tracker = CriticalLogTracker()
        logging.getLogger().addHandler(_critical_log_tracker)
    return _critical_log_tracker


def _record_diagnostic(payload: dict[str, Any]) -> None:
    _diagnostics.append(payload)


def get_recent_health_diagnostics() -> list[dict[str, Any]]:
    return list(_diagnostics)


def _check_bucket_latency(s3_client, bucket: str) -> dict[str, Any]:
    start = time.monotonic()
    try:
        s3_client.head_bucket(Bucket=bucket)
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "message": f"bucket_latency_failed error={exc}",
        }
    elapsed = time.monotonic() - start
    max_allowed = DEFAULT_BUCKET_LATENCY_SECONDS
    if elapsed > max_allowed:
        return {
            "ok": False,
            "message": "bucket_latency_exceeded",
            "elapsed_seconds": round(elapsed, 3),
        }
    return {
        "ok": True,
        "message": "bucket_latency_ok",
        "elapsed_seconds": round(elapsed, 3),
    }


def _load_checkpoint_payload(manager: CheckpointManager) -> Tuple[dict[str, Any] | None, str]:
    try:
        payload = manager.validate_checkpoint_integrity()
    except Exception as exc:  # noqa: BLE001
        return None, f"checkpoint_integrity_exception error={exc}"
    if payload is None:
        return None, "checkpoint_integrity_failed"
    return payload, "checkpoint_integrity_ok"


def _extract_checkpoint_timestamp(payload: dict[str, Any]) -> datetime | None:
    metadata = payload.get("metadata", {}) if isinstance(payload, dict) else {}
    state = payload.get("state", {}) if isinstance(payload, dict) else {}
    candidate = (
        state.get("last_acta_processed_at")
        or state.get("last_acta_timestamp")
        or state.get("last_acta_at")
        or state.get("checkpoint_timestamp")
        or metadata.get("checkpoint_timestamp")
    )
    return _parse_timestamp(candidate)


def _check_checkpoint_age(timestamp: datetime | None) -> dict[str, Any]:
    if timestamp is None:
        return {"ok": False, "message": "checkpoint_timestamp_missing"}
    max_age = _env_int(
        "MAX_CHECKPOINT_AGE_SECONDS",
        DEFAULT_MAX_CHECKPOINT_AGE_SECONDS,
        fallbacks=("MAX_AGE_CHECKPOINT_SECONDS",),
    )
    age_seconds = (_now_utc() - timestamp).total_seconds()
    if age_seconds > max_age:
        return {
            "ok": False,
            "message": "checkpoint_stale",
            "age_seconds": round(age_seconds, 2),
            "max_age_seconds": max_age,
        }
    return {
        "ok": True,
        "message": "checkpoint_fresh",
        "age_seconds": round(age_seconds, 2),
    }


def _check_last_acta_timestamp(timestamp: datetime | None) -> dict[str, Any]:
    if timestamp is None:
        return {"ok": False, "message": "last_acta_timestamp_missing"}
    max_age = _env_int("MAX_LAST_ACTA_AGE_SECONDS", DEFAULT_LAST_ACTA_MAX_AGE_SECONDS)
    age_seconds = (_now_utc() - timestamp).total_seconds()
    if age_seconds > max_age:
        return {
            "ok": False,
            "message": "last_acta_stale",
            "age_seconds": round(age_seconds, 2),
            "max_age_seconds": max_age,
        }
    return {
        "ok": True,
        "message": "last_acta_recent",
        "age_seconds": round(age_seconds, 2),
    }


def _check_critical_errors() -> dict[str, Any]:
    tracker = _ensure_critical_tracker()
    window_seconds = _env_int("CRITICAL_WINDOW_SECONDS", DEFAULT_CRITICAL_WINDOW_SECONDS)
    max_errors = _env_int("MAX_CRITICAL_ERRORS", DEFAULT_MAX_CRITICAL_ERRORS)
    consecutive = tracker.max_consecutive_critical(window_seconds)
    if consecutive >= max_errors:
        return {
            "ok": False,
            "message": "critical_errors_exceeded",
            "consecutive": consecutive,
            "window_seconds": window_seconds,
            "max_allowed": max_errors - 1,
        }
    return {
        "ok": True,
        "message": "critical_errors_ok",
        "consecutive": consecutive,
        "window_seconds": window_seconds,
    }


def _check_resources() -> dict[str, Any]:
    cpu_avg, memory_avg = _resource_sampler.sample()
    memory_threshold = _env_float("MEMORY_THRESHOLD", DEFAULT_MEMORY_THRESHOLD)
    cpu_threshold = _env_float("CPU_THRESHOLD", DEFAULT_CPU_THRESHOLD)
    if memory_avg >= memory_threshold or cpu_avg >= cpu_threshold:
        return {
            "ok": False,
            "message": "resources_threshold_exceeded",
            "cpu_avg": round(cpu_avg, 3),
            "memory_avg": round(memory_avg, 3),
            "cpu_threshold": cpu_threshold,
            "memory_threshold": memory_threshold,
        }
    return {
        "ok": True,
        "message": "resources_ok",
        "cpu_avg": round(cpu_avg, 3),
        "memory_avg": round(memory_avg, 3),
    }


def _check_storage_write(s3_client, bucket: str) -> dict[str, Any]:
    key = _get_write_test_key()
    payload = f"healthcheck {datetime.utcnow().isoformat()}".encode("utf-8")
    try:
        s3_client.put_object(Bucket=bucket, Key=key, Body=payload)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "message": f"storage_write_failed error={exc}"}
    return {"ok": True, "message": "storage_write_ok", "key": key}


def _check_paused_flag() -> dict[str, Any]:
    env_paused = os.getenv("CENTINEL_PAUSED") or os.getenv("PAUSED")
    if env_paused and env_paused.strip().lower() in {"1", "true", "yes", "on"}:
        return {"ok": False, "message": "paused_flag_active", "source": "env"}

    paths = [
        Path(os.getenv("CENTINEL_PANIC_FLAG", "data/panic.flag")),
        Path("data/panic_mode.json"),
    ]
    for path in paths:
        if not path.exists():
            continue
        try:
            content = path.read_text(encoding="utf-8").strip()
        except OSError as exc:
            return {"ok": False, "message": f"paused_flag_read_failed error={exc}", "path": str(path)}
        if not content:
            continue
        if path.suffix == ".json":
            try:
                payload = json.loads(content)
            except json.JSONDecodeError:
                return {"ok": False, "message": "paused_flag_invalid_json", "path": str(path)}
            if isinstance(payload, dict) and payload.get("active") is False:
                continue
            return {"ok": False, "message": "paused_flag_active", "path": str(path)}
        return {"ok": False, "message": "paused_flag_active", "path": str(path)}

    return {"ok": True, "message": "paused_flag_clear"}


async def is_healthy_strict() -> tuple[bool, dict[str, Any]]:
    """Evalúa un healthcheck estricto con diagnóstico detallado.

    Returns:
        Tuple[bool, dict[str, Any]]: (estado, diagnóstico detallado)
    """

    diagnostics: dict[str, Any] = {
        "healthy": False,
        "timestamp": _now_utc().isoformat().replace("+00:00", "Z"),
        "checks": {},
        "failures": [],
    }

    manager, manager_error = _get_checkpoint_manager()
    if manager_error:
        diagnostics["checks"]["checkpoint"] = {
            "ok": False,
            "message": manager_error,
        }
        diagnostics["failures"].append(manager_error)
        _record_diagnostic(diagnostics)
        return False, diagnostics

    bucket = _get_bucket_name()
    s3_client = _build_s3_client()

    bucket_latency = await asyncio.to_thread(_check_bucket_latency, s3_client, bucket)
    diagnostics["checks"]["bucket_latency"] = bucket_latency
    if not bucket_latency.get("ok", False):
        diagnostics["failures"].append(bucket_latency.get("message", "bucket_latency_failed"))

    checkpoint_payload, integrity_message = await asyncio.to_thread(
        _load_checkpoint_payload, manager
    )
    checkpoint_check = {"ok": checkpoint_payload is not None, "message": integrity_message}
    diagnostics["checks"]["checkpoint"] = checkpoint_check
    if checkpoint_payload is None:
        diagnostics["failures"].append(integrity_message)
    else:
        timestamp = _extract_checkpoint_timestamp(checkpoint_payload)
        age_check = _check_checkpoint_age(timestamp)
        diagnostics["checks"]["checkpoint_age"] = age_check
        if not age_check.get("ok", False):
            diagnostics["failures"].append(age_check.get("message", "checkpoint_age_failed"))

        last_acta_check = _check_last_acta_timestamp(timestamp)
        diagnostics["checks"]["last_acta"] = last_acta_check
        if not last_acta_check.get("ok", False):
            diagnostics["failures"].append(last_acta_check.get("message", "last_acta_failed"))

    write_check = await asyncio.to_thread(_check_storage_write, s3_client, bucket)
    diagnostics["checks"]["storage_write"] = write_check
    if not write_check.get("ok", False):
        diagnostics["failures"].append(write_check.get("message", "storage_write_failed"))

    critical_check = _check_critical_errors()
    diagnostics["checks"]["critical_errors"] = critical_check
    if not critical_check.get("ok", False):
        diagnostics["failures"].append(critical_check.get("message", "critical_errors_failed"))

    resources_check = _check_resources()
    diagnostics["checks"]["resources"] = resources_check
    if not resources_check.get("ok", False):
        diagnostics["failures"].append(resources_check.get("message", "resources_failed"))

    paused_check = _check_paused_flag()
    diagnostics["checks"]["paused"] = paused_check
    if not paused_check.get("ok", False):
        diagnostics["failures"].append(paused_check.get("message", "paused_failed"))

    diagnostics["healthy"] = not diagnostics["failures"]
    if diagnostics["healthy"]:
        logger.info("strict_healthcheck_ok")
    else:
        logger.critical("strict_healthcheck_failed failures=%s", diagnostics["failures"])

    _record_diagnostic(diagnostics)
    return diagnostics["healthy"], diagnostics


async def _health_response() -> tuple[bool, dict[str, Any]]:
    try:
        return await is_healthy_strict()
    except Exception as exc:  # noqa: BLE001
        logger.exception("strict_healthcheck_exception error=%s", exc)
        diagnostics = {
            "healthy": False,
            "timestamp": _now_utc().isoformat().replace("+00:00", "Z"),
            "failures": ["strict_healthcheck_exception"],
            "checks": {"exception": {"ok": False, "message": str(exc)}},
        }
        _record_diagnostic(diagnostics)
        return False, diagnostics


def register_strict_health_endpoints(app: FastAPI) -> None:
    router = APIRouter()

    @router.get("/healthz")
    async def healthz() -> dict[str, Any]:
        ok, diagnostics = await _health_response()
        if not ok:
            return JSONResponse(status_code=503, content=diagnostics)
        return {"status": "ok", **diagnostics}

    @router.get("/ready")
    async def ready() -> dict[str, Any]:
        ok, diagnostics = await _health_response()
        if not ok:
            return JSONResponse(status_code=503, content=diagnostics)
        return {"status": "ready", **diagnostics}

    @router.get("/live")
    async def live() -> dict[str, str]:
        return {"status": "alive"}

    app.include_router(router)
