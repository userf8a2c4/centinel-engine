"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `maintain.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - BucketConfig
  - RuntimeConfig
  - load_environment
  - build_console
  - setup_logging
  - resolve_rate_limit_settings
  - _read_rate_limit_state
  - _write_rate_limit_state
  - is_rate_limited
  - parse_runtime_config
  - build_bucket_config
  - build_s3_client
  - confirm_action
  - retry_operation
  - build_checkpoint_manager
  - ...

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `maintain.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - BucketConfig
  - RuntimeConfig
  - load_environment
  - build_console
  - setup_logging
  - resolve_rate_limit_settings
  - _read_rate_limit_state
  - _write_rate_limit_state
  - is_rate_limited
  - parse_runtime_config
  - build_bucket_config
  - build_s3_client
  - confirm_action
  - retry_operation
  - build_checkpoint_manager
  - ...

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
"""

# Maintain Module
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

import psutil
import yaml
from cryptography.fernet import Fernet
from dotenv import load_dotenv

from src.centinel.checkpointing import CheckpointConfig, CheckpointManager
from src.monitoring.strict_health import (
    get_recent_health_diagnostics,
    is_healthy_strict,
)

from centinel_engine.cne_endpoint_healer import CNEEndpointHealer, run_endpoint_healer

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
DEFAULT_RATE_LIMIT_STATE_PATH = Path("data/temp/polling_rate_limit.json")
DEFAULT_RATE_LIMIT_COOLDOWN_SECONDS = 10
CONFIG_PATH = Path("command_center/config.yaml")


@dataclass(frozen=True)
class RuntimeConfig:
    """Runtime settings loaded from environment or defaults."""

    pipeline_version: str
    run_id: str
    checkpoint_state_path: Path
    panic_flag_path: Path
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
    """Español:
        Configura logging a archivo y consola con timestamps.

    English:
        Configure logging to file and console with timestamps.

    Args:
        log_path: Ruta del archivo de log.

    Returns:
        Logger configurado para el módulo maintain.
    """

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


def resolve_rate_limit_settings(logger: logging.Logger) -> tuple[int, Path]:
    """Español:
        Resuelve la configuración de rate limiting desde config.yaml.

    English:
        Resolve rate limiting settings from config.yaml.

    Args:
        logger: Logger para registrar advertencias.

    Returns:
        Tupla con cooldown_seconds y state_path.
    """
    cooldown_seconds = DEFAULT_RATE_LIMIT_COOLDOWN_SECONDS
    state_path = DEFAULT_RATE_LIMIT_STATE_PATH

    if not CONFIG_PATH.exists():
        return cooldown_seconds, state_path

    try:
        config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        logger.warning("Config YAML inválido para rate limiting: %s", exc)
        return cooldown_seconds, state_path

    rate_limit_cfg = config.get("polling_rate_limit", {}) if isinstance(config, dict) else {}
    if isinstance(rate_limit_cfg, dict):
        cooldown_seconds = int(rate_limit_cfg.get("cooldown_seconds", DEFAULT_RATE_LIMIT_COOLDOWN_SECONDS))
        state_path_value = rate_limit_cfg.get("state_path")
        if state_path_value:
            state_path = Path(state_path_value)

    return cooldown_seconds, state_path


def _read_rate_limit_state(state_path: Path, logger: logging.Logger) -> float | None:
    """Español:
        Lee el timestamp del último request desde un archivo de estado.

    English:
        Read the last request timestamp from a state file.

    Args:
        state_path: Ruta del archivo de estado.
        logger: Logger para registrar advertencias.

    Returns:
        Timestamp epoch en segundos o None si no existe.
    """
    if not state_path.exists():
        return None
    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Estado de rate limit inválido: %s", exc)
        return None
    last_request = payload.get("last_request_epoch")
    try:
        return float(last_request) if last_request is not None else None
    except (TypeError, ValueError):
        logger.warning("Estado de rate limit corrupto en %s", state_path)
        return None


def _write_rate_limit_state(state_path: Path, timestamp: float, logger: logging.Logger) -> None:
    """Español:
        Escribe el timestamp del último request en el archivo de estado.

    English:
        Write the last request timestamp into the state file.

    Args:
        state_path: Ruta del archivo de estado.
        timestamp: Timestamp epoch en segundos.
        logger: Logger para registrar advertencias.
    """
    state_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        state_path.write_text(
            json.dumps({"last_request_epoch": timestamp}, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError as exc:
        logger.warning("No se pudo actualizar el estado de rate limit: %s", exc)


def is_rate_limited(state_path: Path, cooldown_seconds: int, logger: logging.Logger) -> bool:
    """Español:
        Determina si debe saltarse una petición por cooldown activo.

    English:
        Determine whether a request should be skipped due to cooldown.

    Args:
        state_path: Ruta del archivo de estado.
        cooldown_seconds: Cooldown mínimo entre requests.
        logger: Logger para registrar advertencias.

    Returns:
        True si la petición debe omitirse por rate limiting.
    """
    last_request = _read_rate_limit_state(state_path, logger)
    now = time.time()
    if last_request is not None and now - last_request < cooldown_seconds:
        remaining = round(cooldown_seconds - (now - last_request), 2)
        logger.warning("Rate limit activo. Omitiendo petición (restante=%ss).", remaining)
        return True

    _write_rate_limit_state(state_path, now, logger)
    return False


def parse_runtime_config() -> RuntimeConfig:
    """Build runtime configuration from environment variables."""

    pipeline_version = os.getenv("CENTINEL_PIPELINE_VERSION", "").strip()
    run_id = os.getenv("CENTINEL_RUN_ID", "").strip()
    checkpoint_state_path = Path(os.getenv("CENTINEL_CHECKPOINT_STATE_PATH", "data/temp/checkpoint_state.json"))
    panic_flag_path = Path(os.getenv("CENTINEL_PANIC_FLAG", "data/panic.flag"))
    backup_secret = os.getenv("CENTINEL_BACKUP_SECRET")
    backup_salt = os.getenv("CENTINEL_BACKUP_SALT")
    log_path = Path(os.getenv("CENTINEL_MAINTENANCE_LOG", str(DEFAULT_LOG_PATH)))
    assume_yes = os.getenv("CENTINEL_ASSUME_YES", "").lower() in {"1", "true", "yes"}

    if not pipeline_version or not run_id:
        raise RuntimeError("CENTINEL_PIPELINE_VERSION y CENTINEL_RUN_ID son obligatorios para las tareas.")

    return RuntimeConfig(
        pipeline_version=pipeline_version,
        run_id=run_id,
        checkpoint_state_path=checkpoint_state_path,
        panic_flag_path=panic_flag_path,
        backup_secret=backup_secret,
        backup_salt=backup_salt,
        log_path=log_path,
        assume_yes=assume_yes,
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
        except OSError as exc:
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
    """Create a checkpoint manager using local filesystem."""

    checkpoint_dir = os.getenv("CENTINEL_CHECKPOINT_DIR", "checkpoints/")
    checkpoint_config = CheckpointConfig(
        pipeline_version=runtime.pipeline_version,
        run_id=runtime.run_id,
        checkpoint_dir=checkpoint_dir,
        checkpoint_interval=50,
    )
    return CheckpointManager(checkpoint_config, logger=logger)


def load_state_from_file(path: Path) -> dict[str, Any]:
    """Load a JSON state file for checkpointing."""

    if not path.exists():
        raise FileNotFoundError(f"No se encontró el estado en {path}. Define CENTINEL_CHECKPOINT_STATE_PATH.")
    return json.loads(path.read_text(encoding="utf-8"))


def command_checkpoint_now(runtime: RuntimeConfig, logger: logging.Logger) -> None:
    """Force a checkpoint save using the latest local state."""

    manager = build_checkpoint_manager(runtime, logger)
    state = load_state_from_file(runtime.checkpoint_state_path)
    logger.info("Guardando checkpoint inmediato desde %s", runtime.checkpoint_state_path)
    manager.save_checkpoint(state)
    logger.info("Checkpoint guardado correctamente en el bucket.")


def fetch_latest_checkpoint_metadata(runtime: RuntimeConfig, logger: logging.Logger) -> dict[str, Any]:
    """Fetch latest checkpoint metadata from the local filesystem."""

    checkpoint_dir = Path(os.getenv("CENTINEL_CHECKPOINT_DIR", "checkpoints/"))
    latest_path = checkpoint_dir / "latest.json"
    if not latest_path.exists():
        return {"status": "checkpoint_not_found"}
    try:
        payload = json.loads(latest_path.read_text(encoding="utf-8"))
        stat = latest_path.stat()
        return {
            "status": "ok",
            "last_modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            "payload": payload,
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("checkpoint_metadata_read_failed error=%s", exc)
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
    detail = "strict_health_ok" if ok else "; ".join(diagnostics.get("failures", [])) or "strict_health_failed"
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
    path.chmod(0o600)


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


def command_clean_old_checkpoints(runtime: RuntimeConfig, logger: logging.Logger, days: int) -> None:
    """Delete checkpoints older than the specified number of days from the local filesystem."""

    confirm_action(
        f"Se eliminarán checkpoints con más de {days} días.",
        runtime.assume_yes,
    )
    checkpoint_dir = Path(os.getenv("CENTINEL_CHECKPOINT_DIR", "checkpoints/"))
    if not checkpoint_dir.exists():
        logger.info("No hay directorio de checkpoints en %s.", checkpoint_dir)
        return

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    deleted = 0
    for entry in checkpoint_dir.glob("*.json"):
        if entry.name == "latest.json":
            continue
        mtime = datetime.fromtimestamp(entry.stat().st_mtime, tz=timezone.utc)
        if mtime < cutoff:
            entry.unlink(missing_ok=True)
            deleted += 1

    if deleted == 0:
        logger.info("No hay checkpoints antiguos para eliminar.")
    else:
        logger.info("Checkpoints eliminados: %s", deleted)


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
    """Backup sensitive configuration files to a local encrypted directory."""

    fernet = _build_backup_fernet(runtime)
    extra_files = [path.strip() for path in os.getenv("CENTINEL_BACKUP_EXTRA_FILES", "").split(",") if path.strip()]
    candidate_files = [".env", "config.yaml", "config.example.yaml"] + extra_files
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_dir = Path("backups") / "config" / timestamp
    backup_dir.mkdir(parents=True, exist_ok=True)
    saved = 0

    for file_name in candidate_files:
        path = Path(file_name)
        if not path.exists():
            logger.warning("Archivo no encontrado para backup: %s", file_name)
            continue
        raw = path.read_bytes()
        encrypted = fernet.encrypt(raw)
        dest = backup_dir / (path.name + ".enc")
        dest.write_bytes(encrypted)
        saved += 1

    logger.info("Backup completado. Archivos guardados en %s: %s", backup_dir, saved)


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

    panic_report_dir = Path("reports") / "panic"
    panic_report_dir.mkdir(parents=True, exist_ok=True)
    panic_report_path = panic_report_dir / f"{int(time.time())}.json"
    panic_report_path.write_text(
        json.dumps(panic_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
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




def ensure_recent_proactive_scan(logger: logging.Logger, max_age_minutes: int = 30) -> dict[str, Any]:
    """Español:
        Verifica y ejecuta un proactive scan si el último escaneo exitoso supera el umbral.

    English:
        Verify and run a proactive scan when the last successful scan is older than threshold.

    Args:
        logger: Logger operativo para trazabilidad forense.
        max_age_minutes: Máxima edad permitida del último escaneo exitoso.
    """

    config_path = Path("config/prod/endpoints.yaml")
    healer = CNEEndpointHealer(config_path)
    config = healer._load_config()
    last_success = healer._parse_iso8601(config.get("healing", {}).get("last_successful_scan"))

    if last_success is not None:
        elapsed = datetime.now(timezone.utc) - last_success
        if elapsed <= timedelta(minutes=max_age_minutes):
            logger.info("🟩 Proactive endpoint scan vigente (edad=%s minutos)", round(elapsed.total_seconds() / 60, 2))
            return {
                "scan_status": "fresh",
                "trusted_for_production": True,
                "safe_mode_active": False,
                "animal_mode": str(config.get("healing", {}).get("animal_mode", "normal")),
                "recommended_interval_minutes": int(config.get("healing", {}).get("recommended_interval_minutes", config.get("healing", {}).get("interval_minutes", 30))),
            }

    logger.info("🩺 Ejecutando proactive endpoint scan previo a fetch/auditoría")
    result = healer.heal_proactive(force=True)
    logger.info(
        "🧾 Proactive endpoint scan ejecutado: status=%s mode=%s interval=%s",
        result.get("scan_status", "unknown"),
        result.get("animal_mode", "normal"),
        result.get("recommended_interval_minutes", "n/a"),
    )
    return result

def build_parser() -> argparse.ArgumentParser:
    """Create argument parser with subcommands."""

    parser = argparse.ArgumentParser(description="Herramienta de mantenimiento para Centinel Engine.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("checkpoint-now", help="Forzar checkpoint inmediato.")
    subparsers.add_parser("status", help="Mostrar estado completo.")
    subparsers.add_parser("rotate-keys", help="Rotar claves de encriptación.")

    clean_parser = subparsers.add_parser("clean-old-checkpoints", help="Eliminar checkpoints antiguos.")
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

    # English: Run proactive gate before any fetch and keep standard endpoint healer execution.
    # Español: Ejecuta compuerta proactiva antes de cualquier fetch y mantiene el healer estándar.
    proactive_result: dict[str, Any] = {"trusted_for_production": True, "safe_mode_active": False}
    try:
        proactive_result = ensure_recent_proactive_scan(logger, max_age_minutes=30)
    except Exception as exc:  # noqa: BLE001
        logger.warning("⚠️ Proactive endpoint scan failed before command %s: %s", args.command, exc)
        proactive_result = {"trusted_for_production": False, "safe_mode_active": True, "scan_status": "error"}

    if args.command != "status" and (not proactive_result.get("trusted_for_production", False) or proactive_result.get("safe_mode_active", False)):
        logger.error(
            "⛔ Production fetch guardrail blocked command %s (status=%s mode=%s)",
            args.command,
            proactive_result.get("scan_status", "unknown"),
            proactive_result.get("animal_mode", "unknown"),
        )
        return 1

    try:
        healer_result = run_endpoint_healer()
        logger.info("🩺 Endpoint healer executed before command %s: %s", args.command, healer_result)
    except Exception as exc:  # noqa: BLE001
        logger.warning("⚠️ Endpoint healer failed before command %s: %s", args.command, exc)

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
