#!/usr/bin/env python3
"""Modo pánico para Centinel Engine.

Ejecuta una secuencia segura para pausar el procesamiento, guardar checkpoint,
generar un reporte auditable y notificar canales de alerta.
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import json
import logging
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import boto3
import yaml

from monitoring.alerts import dispatch_alert
from scripts.logging_utils import configure_logging

DATA_DIR = Path("data")
TEMP_DIR = DATA_DIR / "temp"
REPORTS_DIR = Path("reports")
HASH_DIR = Path("hashes")
PANIC_FLAG_PATH = DATA_DIR / "panic_mode.json"

CONFIG_PATHS = [
    Path("command_center") / "config.yaml",
    Path("config") / "config.yaml",
    Path("config.yaml"),
]

logger = configure_logging("centinel.panic", log_file="logs/centinel.log")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_stamp() -> str:
    return utc_now().strftime("%Y-%m-%d_%H-%M-%S")


def prompt_confirmation() -> None:
    first = input("¿Estás seguro? (si/no): ").strip().lower()
    if first not in {"si", "sí", "yes", "y"}:
        print("[!] Operación cancelada.")
        raise SystemExit(1)
    second = input('Escribe "PANIC" para continuar: ').strip()
    if second != "PANIC":
        print("[!] Confirmación incorrecta. Operación cancelada.")
        raise SystemExit(1)


def prompt_emergency_token() -> None:
    token_required = os.getenv("CENTINEL_PANIC_TOKEN") or os.getenv("PANIC_TOKEN")
    if not token_required:
        return
    token = input("Token de emergencia: ").strip()
    if token != token_required:
        print("[!] Token inválido. Operación cancelada.")
        raise SystemExit(1)


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except FileNotFoundError:
        return {}
    except yaml.YAMLError as exc:
        logger.error("panic_config_invalid path=%s error=%s", path, exc)
        return {}


def update_master_switch(status: str) -> list[Path]:
    updated: list[Path] = []
    for path in CONFIG_PATHS:
        if not path.exists():
            continue
        config = load_yaml(path)
        if not isinstance(config, dict):
            logger.warning("panic_config_not_dict path=%s", path)
            continue
        config["master_switch"] = status
        path.write_text(
            yaml.safe_dump(config, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        updated.append(path)
    return updated


def set_panic_flag(user: str, timestamp: str) -> dict[str, Any]:
    payload = {
        "active": True,
        "user": user,
        "timestamp": timestamp,
        "reason": "manual_panic",
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PANIC_FLAG_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload


def load_checkpoint_candidate() -> dict[str, Any]:
    for path in (TEMP_DIR / "checkpoint.json", TEMP_DIR / "pipeline_checkpoint.json"):
        if path.exists():
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    return payload
            except json.JSONDecodeError as exc:
                logger.warning("panic_checkpoint_invalid path=%s error=%s", path, exc)
    return {}


def resolve_alert_paths() -> tuple[Path, Path]:
    alerts_log_path = Path("alerts.log")
    alerts_output_path = Path("data/alerts.json")
    for path in CONFIG_PATHS:
        if not path.exists():
            continue
        config = load_yaml(path)
        if not isinstance(config, dict):
            continue
        alerts_config = config.get("alerts", {}) if isinstance(config.get("alerts", {}), dict) else {}
        if alerts_config.get("log_path"):
            alerts_log_path = Path(alerts_config["log_path"])
        if alerts_config.get("output_path"):
            alerts_output_path = Path(alerts_config["output_path"])
    return alerts_log_path, alerts_output_path


def load_last_alerts(limit: int = 10) -> list[dict[str, Any]]:
    alerts_log_path, alerts_output_path = resolve_alert_paths()
    alerts: list[dict[str, Any]] = []
    if alerts_log_path.exists():
        lines = alerts_log_path.read_text(encoding="utf-8").strip().splitlines()
        for line in lines[-limit:]:
            try:
                payload = json.loads(line)
                if isinstance(payload, dict):
                    alerts.append(payload)
            except json.JSONDecodeError:
                alerts.append({"raw": line})
        return alerts
    if alerts_output_path.exists():
        try:
            payload = json.loads(alerts_output_path.read_text(encoding="utf-8"))
            if isinstance(payload, list):
                return payload[-limit:]
            if isinstance(payload, dict):
                return [payload]
        except json.JSONDecodeError as exc:
            logger.warning("panic_alerts_invalid path=%s error=%s", alerts_output_path, exc)
    return alerts


def latest_hash() -> str | None:
    hash_files = sorted(HASH_DIR.glob("*.sha256"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not hash_files:
        return None
    content = hash_files[0].read_text(encoding="utf-8").strip()
    if not content:
        return None
    try:
        payload = json.loads(content)
        if isinstance(payload, dict):
            return payload.get("chained_hash") or payload.get("hash")
    except json.JSONDecodeError:
        return content.splitlines()[-1]
    return None


def get_health_status() -> dict[str, Any]:
    try:
        from monitoring.strict_health import is_healthy_strict

        ok, diagnostics = asyncio.run(is_healthy_strict())
        return {"ok": ok, "diagnostics": diagnostics}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "message": f"healthcheck_error: {exc}"}


def build_report(user: str, timestamp: str, checkpoint: dict[str, Any]) -> dict[str, Any]:
    report = {
        "panic_activated_at": timestamp,
        "user": user,
        "health": get_health_status(),
        "last_alerts": load_last_alerts(limit=10),
        "final_hash": latest_hash(),
        "checkpoint_summary": {
            "stage": checkpoint.get("stage"),
            "latest_snapshot": checkpoint.get("latest_snapshot"),
            "last_content_hash": checkpoint.get("last_content_hash"),
        },
    }
    return report


def build_s3_client() -> tuple[Any | None, str | None]:
    bucket = os.getenv("CENTINEL_PANIC_BUCKET") or os.getenv("CENTINEL_CHECKPOINT_BUCKET")
    if not bucket:
        return None, None
    session = boto3.session.Session()
    client = session.client(
        "s3",
        endpoint_url=os.getenv("CENTINEL_S3_ENDPOINT"),
        region_name=os.getenv("CENTINEL_S3_REGION"),
        aws_access_key_id=os.getenv("CENTINEL_S3_ACCESS_KEY"),
        aws_secret_access_key=os.getenv("CENTINEL_S3_SECRET_KEY"),
    )
    return client, bucket


def upload_to_bucket(
    client: Any,
    bucket: str,
    prefix: str,
    report_path: Path,
    checkpoint_path: Path | None,
    panic_flag: dict[str, Any],
) -> dict[str, str]:
    uploaded: dict[str, str] = {}
    report_key = f"{prefix}/{report_path.name}"
    client.put_object(
        Bucket=bucket,
        Key=report_key,
        Body=report_path.read_bytes(),
        ContentType="application/json",
    )
    uploaded["report"] = report_key
    flag_key = f"{prefix}/panic_flag.json"
    client.put_object(
        Bucket=bucket,
        Key=flag_key,
        Body=json.dumps(panic_flag, ensure_ascii=False, indent=2).encode("utf-8"),
        ContentType="application/json",
    )
    uploaded["flag"] = flag_key
    if checkpoint_path and checkpoint_path.exists():
        checkpoint_key = f"{prefix}/{checkpoint_path.name}"
        client.put_object(
            Bucket=bucket,
            Key=checkpoint_key,
            Body=checkpoint_path.read_bytes(),
            ContentType="application/json",
        )
        uploaded["checkpoint"] = checkpoint_key
    return uploaded


def build_report_url(bucket: str, key: str) -> str | None:
    base_url = os.getenv("CENTINEL_PANIC_PUBLIC_BASE_URL")
    if base_url:
        return f"{base_url.rstrip('/')}/{key}"
    endpoint = os.getenv("CENTINEL_S3_ENDPOINT")
    if endpoint:
        return f"{endpoint.rstrip('/')}/{bucket}/{key}"
    return None


def send_alert_message(report_url: str | None, final_hash: str | None, timestamp: str) -> None:
    message = "MODO PÁNICO ACTIVADO"
    if report_url:
        message += f" - Reporte: {report_url}"
    context = {
        "timestamp": timestamp,
        "report_url": report_url,
        "final_hash": final_hash,
        "checkpoint_hash": final_hash,
        "source": "panic_mode",
    }
    dispatch_alert("PANIC", message, context)


def shutdown_worker() -> None:
    pid_env = os.getenv("CENTINEL_WORKER_PID")
    pid_path = DATA_DIR / "worker.pid"
    pid: int | None = None
    if pid_env and pid_env.isdigit():
        pid = int(pid_env)
    elif pid_path.exists():
        raw = pid_path.read_text(encoding="utf-8").strip()
        if raw.isdigit():
            pid = int(raw)
    if pid is None:
        logger.warning("panic_worker_pid_missing")
        return
    try:
        os.kill(pid, signal.SIGTERM)
        logger.info("panic_worker_sigterm pid=%s", pid)
        time.sleep(2)
    except ProcessLookupError:
        logger.warning("panic_worker_not_found pid=%s", pid)
    except PermissionError:
        logger.error("panic_worker_permission_denied pid=%s", pid)


def main() -> int:
    parser = argparse.ArgumentParser(description="Activa el modo pánico de Centinel Engine.")
    parser.add_argument("--user", help="Usuario que activa el modo pánico.")
    args = parser.parse_args()

    prompt_confirmation()
    prompt_emergency_token()

    user = args.user or os.getenv("PANIC_USER") or getpass.getuser()
    timestamp = utc_now().isoformat()
    stamp = utc_stamp()

    try:
        panic_flag = set_panic_flag(user, timestamp)
        updated = update_master_switch("OFF")
        logger.info("panic_master_switch_off paths=%s", [p.as_posix() for p in updated])
    except Exception as exc:  # noqa: BLE001
        logger.error("panic_pause_failed error=%s", exc)

    checkpoint = load_checkpoint_candidate()
    panic_dir = REPORTS_DIR / "panic" / stamp
    panic_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = panic_dir / "panic_checkpoint.json"
    checkpoint_payload = {
        "captured_at": timestamp,
        "source": "panic_mode",
        "checkpoint": checkpoint,
    }
    checkpoint_path.write_text(
        json.dumps(checkpoint_payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    report = build_report(user, timestamp, checkpoint)
    report_path = panic_dir / "panic_report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    uploaded_report_url = None
    try:
        client, bucket = build_s3_client()
        if client and bucket:
            prefix = f"panic/{stamp}"
            uploaded = upload_to_bucket(
                client, bucket, prefix, report_path, checkpoint_path, panic_flag
            )
            if "report" in uploaded:
                uploaded_report_url = build_report_url(bucket, uploaded["report"])
            logger.info("panic_upload_complete keys=%s", uploaded)
        else:
            logger.warning("panic_bucket_missing")
    except Exception as exc:  # noqa: BLE001
        logger.error("panic_upload_failed error=%s", exc)

    try:
        send_alert_message(uploaded_report_url, report.get("final_hash"), timestamp)
    except Exception as exc:  # noqa: BLE001
        logger.error("panic_alert_publish_failed error=%s", exc)

    try:
        shutdown_worker()
    except Exception as exc:  # noqa: BLE001
        logger.error("panic_worker_shutdown_failed error=%s", exc)

    logger.critical("MODO PÁNICO ACTIVADO por %s/%s", user, timestamp)
    print("[!] MODO PÁNICO ACTIVADO.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
