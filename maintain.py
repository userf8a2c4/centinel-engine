"""Centinel Engine maintenance utility.

This script provides one-stop maintenance commands for checkpointing,
status inspection, key rotation, backups, and recovery testing.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import importlib.util
import json
import logging
import os
import platform
import secrets
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

import boto3
import psutil
from botocore.exceptions import ClientError, EndpointConnectionError
from cryptography.fernet import Fernet
from dotenv import load_dotenv

from src.centinel.checkpointing import CheckpointConfig, CheckpointManager
from src.monitoring.strict_health import get_recent_health_diagnostics, is_healthy_strict

if importlib.util.find_spec("rich"):
    from rich.console import Console
    from rich.logging import RichHandler

    _RICH_AVAILABLE = True
else:  # pragma: no cover - optional dependency
    Console = None  # type: ignore[assignment]
    RichHandler = None  # type: ignore[assignment]
    _RICH_AVAILABLE = False


LOG_FORMAT = "%(asctime)s | %(levelname)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
DEFAULT_LOG_PATH = Path("logs/maintain.log")


@dataclass(frozen=True)
class BucketConfig:
    """Configuration for S3-compatible bucket operations."""

    bucket: str
    endpoint_url: Optional[str]
    region: Optional[str]
    access_key: Optional[str]
    secret_key: Optional[str]


@dataclass(frozen=True)
class RuntimeConfig:
    """Runtime settings loaded from environment or defaults."""

    pipeline_version: str
    run_id: str
    checkpoint_state_path: Path
    panic_flag_path: Path
    backup_bucket: Optional[str]
    backup_secret: Optional[str]
    backup_salt: Optional[str]
    log_path: Path
    assume_yes: bool


def load_environment() -> None:
    """Load environment variables from .env if present."""

    load_dotenv(override=False)


def build_console() -> "Console | None":
    """Return a rich console if available."""

    if _RICH_AVAILABLE:
        return Console()
    return None


def setup_logging(log_path: Path) -> logging.Logger:
    """Configure logging to file and console with timestamps."""

    log_path.parent.mkdir(parents=True, exist_ok=True)
    handlers: list[logging.Handler] = []

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    handlers.append(file_handler)

    if _RICH_AVAILABLE and RichHandler is not None:
        handlers.append(RichHandler(show_time=True, show_level=True, show_path=False))
    else:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
        handlers.append(stream_handler)

    logging.basicConfig(level=logging.INFO, handlers=handlers)
    logger = logging.getLogger("maintain")
    logger.setLevel(logging.INFO)
    return logger


def parse_runtime_config() -> RuntimeConfig:
    """Build runtime configuration from environment variables."""

    pipeline_version = os.getenv("CENTINEL_PIPELINE_VERSION", "").strip()
    run_id = os.getenv("CENTINEL_RUN_ID", "").strip()
    checkpoint_state_path = Path(
        os.getenv("CENTINEL_CHECKPOINT_STATE_PATH", "data/temp/checkpoint_state.json")
    )
    panic_flag_path = Path(os.getenv("CENTINEL_PANIC_FLAG", "data/panic.flag"))
    backup_bucket = os.getenv("CENTINEL_BACKUP_BUCKET")
    backup_secret = os.getenv("CENTINEL_BACKUP_SECRET")
    backup_salt = os.getenv("CENTINEL_BACKUP_SALT")
    log_path = Path(os.getenv("CENTINEL_MAINTENANCE_LOG", str(DEFAULT_LOG_PATH)))
    assume_yes = os.getenv("CENTINEL_ASSUME_YES", "").lower() in {"1", "true", "yes"}

    if not pipeline_version or not run_id:
        raise RuntimeError(
            "CENTINEL_PIPELINE_VERSION y CENTINEL_RUN_ID son obligatorios para las tareas."
        )

    return RuntimeConfig(
        pipeline_version=pipeline_version,
        run_id=run_id,
        checkpoint_state_path=checkpoint_state_path,
        panic_flag_path=panic_flag_path,
        backup_bucket=backup_bucket,
        backup_secret=backup_secret,
        backup_salt=backup_salt,
        log_path=log_path,
        assume_yes=assume_yes,
    )


def build_bucket_config(bucket: Optional[str] = None) -> BucketConfig:
    """Create bucket configuration from env variables."""

    return BucketConfig(
        bucket=bucket
        or os.getenv("CENTINEL_CHECKPOINT_BUCKET")
        or os.getenv("CHECKPOINT_BUCKET")
        or "",
        endpoint_url=os.getenv("CENTINEL_S3_ENDPOINT")
        or os.getenv("STORAGE_ENDPOINT_URL"),
        region=os.getenv("CENTINEL_S3_REGION")
        or os.getenv("AWS_REGION")
        or "us-east-1",
        access_key=os.getenv("CENTINEL_S3_ACCESS_KEY")
        or os.getenv("AWS_ACCESS_KEY_ID"),
        secret_key=os.getenv("CENTINEL_S3_SECRET_KEY")
        or os.getenv("AWS_SECRET_ACCESS_KEY"),
    )


def build_s3_client(config: BucketConfig) -> Any:
    """Build a boto3 S3 client based on configuration."""

    session = boto3.session.Session()
    return session.client(
        "s3",
        endpoint_url=config.endpoint_url,
        region_name=config.region,
        aws_access_key_id=config.access_key,
        aws_secret_access_key=config.secret_key,
    )


def confirm_action(message: str, assume_yes: bool) -> None:
    """Ask for interactive confirmation before destructive actions."""

    if assume_yes:
        return
    if not sys.stdin.isatty():
        raise RuntimeError("Se requiere confirmación interactiva para continuar.")
    response = input(f"{message} (yes/no): ").strip().lower()
    if response not in {"yes", "y"}:
        raise RuntimeError("Operación cancelada por el usuario.")


def retry_operation(
    operation: Callable[[], Any],
    *,
    attempts: int = 3,
    backoff: float = 1.0,
    logger: logging.Logger,
    description: str,
) -> Any:
    """Retry bucket operations with exponential backoff."""

    last_exc: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return operation()
        except (ClientError, EndpointConnectionError, OSError) as exc:
            last_exc = exc
            logger.warning(
                "Operación falló (%s) intento=%s/%s error=%s",
                description,
                attempt,
                attempts,
                exc,
            )
            if attempt == attempts:
                break
            time.sleep(backoff * (2 ** (attempt - 1)))
    raise RuntimeError(f"Operación falló definitivamente: {description}") from last_exc


def build_checkpoint_manager(runtime: RuntimeConfig, logger: logging.Logger) -> CheckpointManager:
    """Create a checkpoint manager using environment configuration."""

    bucket_config = build_bucket_config()
    if not bucket_config.bucket:
        raise RuntimeError("Bucket de checkpoints no configurado.")
    checkpoint_config = CheckpointConfig(
        bucket=bucket_config.bucket,
        pipeline_version=runtime.pipeline_version,
        run_id=runtime.run_id,
        checkpoint_interval=50,
        s3_endpoint_url=bucket_config.endpoint_url,
        s3_region=bucket_config.region,
        s3_access_key=bucket_config.access_key,
        s3_secret_key=bucket_config.secret_key,
    )
    return CheckpointManager(checkpoint_config, logger=logger)


def load_state_from_file(path: Path) -> dict[str, Any]:
    """Load a JSON state file for checkpointing."""

    if not path.exists():
        raise FileNotFoundError(
            f"No se encontró el estado en {path}. Define CENTINEL_CHECKPOINT_STATE_PATH."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def command_checkpoint_now(runtime: RuntimeConfig, logger: logging.Logger) -> None:
    """Force a checkpoint save using the latest local state."""

    manager = build_checkpoint_manager(runtime, logger)
    state = load_state_from_file(runtime.checkpoint_state_path)
    logger.info("Guardando checkpoint inmediato desde %s", runtime.checkpoint_state_path)
    manager.save_checkpoint(state)
    logger.info("Checkpoint guardado correctamente en el bucket.")


def _latest_checkpoint_key(runtime: RuntimeConfig) -> str:
    """Español: Función _latest_checkpoint_key del módulo maintain.py.

    English: Function _latest_checkpoint_key defined in maintain.py.
    """
    return f"centinel/checkpoints/{runtime.pipeline_version}/{runtime.run_id}/latest.json"


def fetch_latest_checkpoint_metadata(
    runtime: RuntimeConfig, logger: logging.Logger
) -> dict[str, Any]:
    """Fetch the latest checkpoint metadata from the bucket."""

    bucket_config = build_bucket_config()
    if not bucket_config.bucket:
        return {"status": "bucket_not_configured"}
    s3 = build_s3_client(bucket_config)
    key = _latest_checkpoint_key(runtime)

    def _get() -> dict[str, Any]:
        """Español: Función _get del módulo maintain.py.

        English: Function _get defined in maintain.py.
        """
        response = s3.get_object(Bucket=bucket_config.bucket, Key=key)
        body = response.get("Body")
        raw = body.read() if body else b""
        payload = json.loads(raw.decode("utf-8")) if raw else {}
        return {
            "status": "ok",
            "last_modified": response.get("LastModified"),
            "payload": payload,
        }

    try:
        return retry_operation(
            _get, logger=logger, description="checkpoint_metadata_read"
        )
    except RuntimeError:
        return {"status": "unavailable"}


def _load_recent_alerts(log_path: Path, limit: int = 5) -> list[str]:
    """Load recent alert-like lines from the log file."""

    if not log_path.exists():
        return []
    lines = log_path.read_text(encoding="utf-8").splitlines()
    alerts = [line for line in lines if "ALERTA" in line or "CRITICAL" in line]
    return alerts[-limit:]


def command_status(runtime: RuntimeConfig, logger: logging.Logger) -> None:
    """Show a full status report including healthchecks and resources."""

    console = build_console()

    health_status = ("unknown", "strict_health_unavailable")
    diagnostics: list[dict[str, Any]] = []
    ok, diagnostics = asyncio.run(is_healthy_strict())
    detail = (
        "strict_health_ok"
        if ok
        else "; ".join(diagnostics.get("failures", [])) or "strict_health_failed"
    )
    health_status = ("ok" if ok else "fail", detail)
    diagnostics = get_recent_health_diagnostics()

    cpu_percent = psutil.cpu_percent(interval=0.1)
    mem = psutil.virtual_memory()

    checkpoint_meta = fetch_latest_checkpoint_metadata(runtime, logger)
    alerts = _load_recent_alerts(runtime.log_path)

    status_payload = {
        "health": {"status": health_status[0], "detail": health_status[1]},
        "checkpoint": checkpoint_meta,
        "resources": {
            "cpu_percent": cpu_percent,
            "memory_percent": mem.percent,
            "memory_available_gb": round(mem.available / (1024**3), 2),
        },
        "alerts": alerts,
        "diagnostics": diagnostics[-5:],
        "host": {
            "node": platform.node(),
            "python": sys.version.split()[0],
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if console:
        console.print("[bold cyan]Centinel Engine Status[/bold cyan]")
        console.print_json(json.dumps(status_payload, ensure_ascii=False, default=str))
    else:
        print(json.dumps(status_payload, ensure_ascii=False, indent=2, default=str))

    logger.info("Status generado.")


def _update_env_file(path: Path, updates: dict[str, str]) -> None:
    """Update .env file with new key values while keeping other lines."""

    existing_lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    updated_lines: list[str] = []
    remaining = updates.copy()

    for line in existing_lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            updated_lines.append(line)
            continue
        key = line.split("=", 1)[0].strip()
        if key in remaining:
            updated_lines.append(f"{key}={remaining.pop(key)}")
        else:
            updated_lines.append(line)

    for key, value in remaining.items():
        updated_lines.append(f"{key}={value}")

    path.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")


def command_rotate_keys(runtime: RuntimeConfig, logger: logging.Logger) -> None:
    """Rotate encryption keys and update .env."""

    confirm_action(
        "Esta acción rotará las claves de encriptación y actualizará .env.",
        runtime.assume_yes,
    )
    env_path = Path(os.getenv("CENTINEL_ENV_PATH", ".env"))
    backup_path = env_path.with_suffix(f".bak-{datetime.now().strftime('%Y%m%d%H%M%S')}")
    if env_path.exists():
        backup_path.write_text(env_path.read_text(encoding="utf-8"), encoding="utf-8")

    new_secret = secrets.token_urlsafe(32)
    new_salt = secrets.token_urlsafe(16)

    _update_env_file(
        env_path,
        {
            "CENTINEL_CHECKPOINT_SECRET": new_secret,
            "CENTINEL_CHECKPOINT_SALT": new_salt,
        },
    )

    logger.info("Claves rotadas y .env actualizado. Backup en %s", backup_path)


def command_clean_old_checkpoints(
    runtime: RuntimeConfig, logger: logging.Logger, days: int
) -> None:
    """Delete checkpoints older than the specified number of days."""

    confirm_action(
        f"Se eliminarán checkpoints con más de {days} días.",
        runtime.assume_yes,
    )
    bucket_config = build_bucket_config()
    if not bucket_config.bucket:
        raise RuntimeError("Bucket de checkpoints no configurado.")

    s3 = build_s3_client(bucket_config)
    prefix = f"centinel/checkpoints/{runtime.pipeline_version}/{runtime.run_id}/"
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    keys_to_delete: list[dict[str, str]] = []
    continuation: Optional[str] = None

    while True:
        def _list_page() -> dict[str, Any]:
            """Español: Función _list_page del módulo maintain.py.

            English: Function _list_page defined in maintain.py.
            """
            params = {"Bucket": bucket_config.bucket, "Prefix": prefix}
            if continuation:
                params["ContinuationToken"] = continuation
            return s3.list_objects_v2(**params)

        page = retry_operation(
            _list_page, logger=logger, description="checkpoint_list"
        )

        for obj in page.get("Contents", []):
            key = obj.get("Key", "")
            last_modified = obj.get("LastModified")
            if not key or key.endswith("latest.json"):
                continue
            if last_modified and last_modified < cutoff:
                keys_to_delete.append({"Key": key})

        if not page.get("IsTruncated"):
            break
        continuation = page.get("NextContinuationToken")

    if not keys_to_delete:
        logger.info("No hay checkpoints antiguos para eliminar.")
        return

    def _delete_batch(batch: list[dict[str, str]]) -> Any:
        """Español: Función _delete_batch del módulo maintain.py.

        English: Function _delete_batch defined in maintain.py.
        """
        return s3.delete_objects(Bucket=bucket_config.bucket, Delete={"Objects": batch})

    for idx in range(0, len(keys_to_delete), 1000):
        batch = keys_to_delete[idx : idx + 1000]
        retry_operation(
            lambda batch=batch: _delete_batch(batch),
            logger=logger,
            description="checkpoint_cleanup",
        )

    logger.info("Checkpoints eliminados: %s", len(keys_to_delete))


def _build_backup_fernet(runtime: RuntimeConfig) -> Fernet:
    """Español: Función _build_backup_fernet del módulo maintain.py.

    English: Function _build_backup_fernet defined in maintain.py.
    """
    secret = runtime.backup_secret or os.getenv("CENTINEL_CHECKPOINT_SECRET")
    if not secret:
        raise RuntimeError("CENTINEL_BACKUP_SECRET no configurado para backup.")
    salt = runtime.backup_salt or os.getenv("CENTINEL_CHECKPOINT_SALT", "")
    digest = hashlib.sha256(f"{secret}{salt}".encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def command_backup_config(runtime: RuntimeConfig, logger: logging.Logger) -> None:
    """Backup sensitive configuration files to an encrypted bucket."""

    bucket_name = runtime.backup_bucket or os.getenv("CENTINEL_CHECKPOINT_BUCKET")
    if not bucket_name:
        raise RuntimeError("No se configuró bucket para backup.")

    fernet = _build_backup_fernet(runtime)
    bucket_config = build_bucket_config(bucket=bucket_name)
    s3 = build_s3_client(bucket_config)

    extra_files = [
        path.strip()
        for path in os.getenv("CENTINEL_BACKUP_EXTRA_FILES", "").split(",")
        if path.strip()
    ]

    candidate_files = [".env", "config.yaml", "config.example.yaml"] + extra_files
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    uploaded = 0

    for file_name in candidate_files:
        path = Path(file_name)
        if not path.exists():
            logger.warning("Archivo no encontrado para backup: %s", file_name)
            continue
        raw = path.read_bytes()
        encrypted = fernet.encrypt(raw)
        key = f"centinel/backups/config/{timestamp}/{path.name}.enc"

        retry_operation(
            lambda key=key, encrypted=encrypted: s3.put_object(
                Bucket=bucket_name,
                Key=key,
                Body=encrypted,
                ContentType="application/octet-stream",
            ),
            logger=logger,
            description="backup_config",
        )
        uploaded += 1

    logger.info("Backup completado. Archivos subidos: %s", uploaded)


def command_test_recovery(runtime: RuntimeConfig, logger: logging.Logger) -> None:
    """Simulate loading the latest checkpoint and verify integrity."""

    manager = build_checkpoint_manager(runtime, logger)
    payload = manager.validate_checkpoint_integrity()
    if payload is None:
        raise RuntimeError("No se pudo validar el último checkpoint.")
    state = payload.get("state", {})
    required = manager.required_state_keys
    missing = required - set(state.keys())
    if missing:
        raise RuntimeError(f"Checkpoint inválido; faltan llaves: {sorted(missing)}")

    logger.info("Checkpoint válido. Llaves principales: %s", sorted(required))


def command_panic(runtime: RuntimeConfig, logger: logging.Logger) -> None:
    """Activate panic mode: pause processing, publish status, alert."""

    confirm_action(
        "Se activará el modo pánico (pausa de procesamiento y alerta).",
        runtime.assume_yes,
    )
    runtime.panic_flag_path.parent.mkdir(parents=True, exist_ok=True)
    panic_payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "host": platform.node(),
        "reason": "operator_triggered",
    }
    runtime.panic_flag_path.write_text(
        json.dumps(panic_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    bucket_config = build_bucket_config()
    if bucket_config.bucket:
        s3 = build_s3_client(bucket_config)
        key = f"centinel/panic/{runtime.run_id}-{int(time.time())}.json"
        retry_operation(
            lambda: s3.put_object(
                Bucket=bucket_config.bucket,
                Key=key,
                Body=json.dumps(panic_payload).encode("utf-8"),
                ContentType="application/json",
            ),
            logger=logger,
            description="panic_publish",
        )

    panic_webhook = os.getenv("CENTINEL_PANIC_WEBHOOK")
    if panic_webhook:
        import httpx

        retry_operation(
            lambda: httpx.post(panic_webhook, json=panic_payload, timeout=5.0),
            logger=logger,
            description="panic_webhook",
        )

    logger.critical("Modo pánico activado. Flag en %s", runtime.panic_flag_path)


def build_parser() -> argparse.ArgumentParser:
    """Create argument parser with subcommands."""

    parser = argparse.ArgumentParser(
        description="Herramienta de mantenimiento para Centinel Engine."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("checkpoint-now", help="Forzar checkpoint inmediato.")
    subparsers.add_parser("status", help="Mostrar estado completo.")
    subparsers.add_parser("rotate-keys", help="Rotar claves de encriptación.")

    clean_parser = subparsers.add_parser(
        "clean-old-checkpoints", help="Eliminar checkpoints antiguos."
    )
    clean_parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Eliminar checkpoints anteriores a X días.",
    )

    subparsers.add_parser("backup-config", help="Respaldar configuración sensible.")
    subparsers.add_parser("test-recovery", help="Verificar recuperación.")
    subparsers.add_parser("panic", help="Activar modo pánico.")

    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    """Main entry point."""

    load_environment()
    runtime = parse_runtime_config()
    logger = setup_logging(runtime.log_path)

    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "checkpoint-now":
            command_checkpoint_now(runtime, logger)
        elif args.command == "status":
            command_status(runtime, logger)
        elif args.command == "rotate-keys":
            command_rotate_keys(runtime, logger)
        elif args.command == "clean-old-checkpoints":
            command_clean_old_checkpoints(runtime, logger, args.days)
        elif args.command == "backup-config":
            command_backup_config(runtime, logger)
        elif args.command == "test-recovery":
            command_test_recovery(runtime, logger)
        elif args.command == "panic":
            command_panic(runtime, logger)
        else:
            parser.print_help()
            return 1
    except Exception as exc:  # noqa: BLE001
        logger.error("Error en comando %s: %s", args.command, exc)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# Ejemplos de uso:
#   python maintain.py status
#   python maintain.py checkpoint-now
#   python maintain.py rotate-keys
#   python maintain.py clean-old-checkpoints --days 45
#   python maintain.py backup-config
#   python maintain.py test-recovery
#   python maintain.py panic
