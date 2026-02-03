import argparse
import hashlib
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import random
import requests
import yaml
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from anchor.arbitrum_anchor import anchor_batch, anchor_root
from scripts.download_and_hash import is_master_switch_on, normalize_master_switch
from scripts.healthcheck import check_cne_connectivity
from scripts.logging_utils import configure_logging, log_event
from scripts.security.encrypt_secrets import decrypt_secrets
from sentinel.core.anchoring_payload import build_diff_summary, compute_anchor_root
from sentinel.utils.config_loader import load_config

DATA_DIR = Path("data")
TEMP_DIR = DATA_DIR / "temp"
HASH_DIR = Path("hashes")
ANALYSIS_DIR = Path("analysis")
REPORTS_DIR = Path("reports")
ANCHOR_LOG_DIR = Path("logs") / "anchors"
STATE_PATH = DATA_DIR / "pipeline_state.json"
PIPELINE_CHECKPOINT_PATH = TEMP_DIR / "pipeline_checkpoint.json"
FAILURE_CHECKPOINT_PATH = TEMP_DIR / "checkpoint.json"
HEARTBEAT_PATH = DATA_DIR / "heartbeat.json"
RULES_CONFIG_PATH = Path("command_center") / "rules.yaml"
RESILIENCE_STAGE_ORDER = [
    "start",
    "healthcheck",
    "download",
    "normalize",
    "analyze",
    "report",
    "anchor",
    "complete",
]

DATA_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)
HASH_DIR.mkdir(exist_ok=True)
ANALYSIS_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)
ANCHOR_LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = configure_logging("centinel.pipeline", log_file="logs/centinel.log")


def utcnow():
    """/** Obtiene hora UTC actual. / Get current UTC time. **"""
    return datetime.now(timezone.utc)


def update_heartbeat(status: str = "ok", details: dict[str, Any] | None = None) -> None:
    """/** Actualiza archivo heartbeat para monitoreo. / Update heartbeat file for monitoring. **/"""
    payload = {
        "updated_at": utcnow().isoformat(),
        "status": status,
        "pid": os.getpid(),
    }
    if details:
        payload["details"] = details
    try:
        HEARTBEAT_PATH.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    except OSError as exc:
        logger.warning("heartbeat_write_failed path=%s error=%s", HEARTBEAT_PATH, exc)


def load_state():
    """/** Carga estado del pipeline si existe. / Load pipeline state when present. **"""
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        logger.error("pipeline_state_invalid path=%s error=%s", STATE_PATH, exc)
        return {}


def save_state(state):
    """/** Guarda el estado del pipeline. / Save pipeline state. **"""
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def load_pipeline_checkpoint() -> dict[str, Any]:
    """/** Carga checkpoint del pipeline si existe. / Load the pipeline checkpoint when present. **"""
    if not PIPELINE_CHECKPOINT_PATH.exists():
        return {}
    try:
        return json.loads(PIPELINE_CHECKPOINT_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        logger.error(
            "pipeline_checkpoint_invalid path=%s error=%s",
            PIPELINE_CHECKPOINT_PATH,
            exc,
        )
        return {}


def save_pipeline_checkpoint(payload: dict[str, Any]) -> None:
    """/** Guarda estado intermedio del pipeline en disco. / Persist intermediate pipeline state to disk. **"""
    PIPELINE_CHECKPOINT_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def clear_pipeline_checkpoint() -> None:
    """/** Elimina el checkpoint si el pipeline finalizó correctamente. / Remove the checkpoint once the pipeline completes successfully. **"""
    if PIPELINE_CHECKPOINT_PATH.exists():
        PIPELINE_CHECKPOINT_PATH.unlink()


def load_resilience_checkpoint() -> dict[str, Any]:
    """/** Carga checkpoint desde data/temp/checkpoint.json. / Load checkpoint from data/temp/checkpoint.json. **"""
    if not FAILURE_CHECKPOINT_PATH.exists():
        return {}
    try:
        payload = json.loads(FAILURE_CHECKPOINT_PATH.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except json.JSONDecodeError:
        logger.warning("resilience_checkpoint_invalid path=%s", FAILURE_CHECKPOINT_PATH)
        return {}


def collect_snapshot_index(limit: int = 19) -> list[dict[str, Any]]:
    """/** Genera índice JSON con snapshots recientes. / Generate a JSON index with recent snapshots. **"""
    snapshots = sorted(
        DATA_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True
    )
    index: list[dict[str, Any]] = []
    for snapshot in snapshots[:limit]:
        index.append(
            {
                "file": snapshot.name,
                "mtime": snapshot.stat().st_mtime,
            }
        )
    return index


def load_rules_thresholds() -> dict[str, Any]:
    """/** Carga reglas desde command_center/rules.yaml. / Load rules from command_center/rules.yaml. **"""
    if not RULES_CONFIG_PATH.exists():
        return {}
    try:
        return yaml.safe_load(RULES_CONFIG_PATH.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        logger.warning("rules_yaml_invalid error=%s", exc)
        return {}


def load_security_settings() -> dict[str, Any]:
    """/** Carga configuración de seguridad desde rules.yaml. / Load security settings from rules.yaml. **/"""
    rules_thresholds = load_rules_thresholds()
    security = rules_thresholds.get("security", {}) if isinstance(rules_thresholds, dict) else {}
    return security if isinstance(security, dict) else {}


def load_resilience_settings(config: dict[str, Any]) -> dict[str, Any]:
    """/** Carga configuración de resiliencia desde el config principal. / Load resilience settings from main config. **/"""
    resilience = config.get("resilience", {}) if isinstance(config, dict) else {}
    return resilience if isinstance(resilience, dict) else {}


def resolve_alert_paths(config: dict[str, Any]) -> tuple[Path, Path]:
    """/** Resuelve rutas para alertas críticas. / Resolve paths for critical alerts. **/"""
    alerts_config = config.get("alerts", {}) if isinstance(config, dict) else {}
    if not isinstance(alerts_config, dict):
        alerts_config = {}
    alerts_log_path = Path(alerts_config.get("log_path", "alerts.log"))
    alerts_output_path = Path(alerts_config.get("output_path", "data/alerts.json"))
    return alerts_log_path, alerts_output_path


def build_chaos_rng(resilience: dict[str, Any]) -> random.Random:
    """/** Construye generador aleatorio para caos. / Build random generator for chaos. **/"""
    chaos_settings = resilience.get("chaos", {}) if isinstance(resilience, dict) else {}
    if not isinstance(chaos_settings, dict):
        return random.Random()
    seed = chaos_settings.get("seed")
    return random.Random(seed)


def maybe_inject_chaos_failure(stage: str, resilience: dict[str, Any], rng: random.Random) -> None:
    """/** Inyecta falla caótica si está habilitado. / Inject chaos failure when enabled. **/"""
    chaos_settings = resilience.get("chaos", {}) if isinstance(resilience, dict) else {}
    if not isinstance(chaos_settings, dict):
        return
    if not chaos_settings.get("enabled", False):
        return
    failure_rate = float(chaos_settings.get("failure_rate", 0.0))
    if failure_rate <= 0:
        return
    if rng.random() < min(max(failure_rate, 0.0), 1.0):
        raise RuntimeError(f"chaos_injected stage={stage}")


def build_auto_resume_settings(resilience: dict[str, Any]) -> dict[str, Any]:
    """/** Normaliza configuración de auto-resume. / Normalize auto-resume settings. **/"""
    auto_resume = resilience.get("auto_resume", {}) if isinstance(resilience, dict) else {}
    if not isinstance(auto_resume, dict):
        auto_resume = {}
    return {
        "enabled": bool(auto_resume.get("enabled", True)),
        "max_attempts": int(auto_resume.get("max_attempts", 3)),
        "backoff_base_seconds": float(auto_resume.get("backoff_base_seconds", 5)),
        "backoff_max_seconds": float(auto_resume.get("backoff_max_seconds", 60)),
        "retry_on": str(auto_resume.get("retry_on", "any")).lower(),
    }


def compute_backoff_delay(attempt: int, base_seconds: float, max_seconds: float) -> float:
    """/** Calcula backoff exponencial. / Compute exponential backoff delay. **/"""
    if attempt <= 0:
        return 0.0
    delay = base_seconds * (2 ** (attempt - 1))
    return min(max(delay, 0.0), max_seconds)


def _has_private_key(arbitrum_config: dict[str, Any]) -> bool:
    """/** Determina si hay private key disponible. / Determine if a private key is available. **/"""
    raw_key = arbitrum_config.get("private_key")
    placeholder_values = {"", None, "0x...", "REPLACE_ME"}
    if raw_key not in placeholder_values:
        return True
    return bool(os.getenv("ARBITRUM_PRIVATE_KEY"))


def _ensure_decrypted_private_key(arbitrum_config: dict[str, Any]) -> None:
    """/** Desencripta private key sólo si falta. / Decrypt private key only when missing. **/"""
    security_settings = load_security_settings()
    if not security_settings.get("encrypt_enabled", False):
        return
    if _has_private_key(arbitrum_config):
        return
    try:
        decrypted = decrypt_secrets(keys=["ARBITRUM_PRIVATE_KEY"])
    except ValueError:
        # Seguridad: si falla la desencriptación, evitar anclaje. / Security: avoid anchoring if decryption fails.
        logger.error("anchor_decrypt_failed")
        return
    private_key = decrypted.get("ARBITRUM_PRIVATE_KEY")
    if private_key:
        # Seguridad: mantener secreto en memoria/env sin escribir en disco. / Security: keep secret in memory/env only.
        os.environ["ARBITRUM_PRIVATE_KEY"] = private_key
        arbitrum_config["private_key"] = private_key


def resolve_max_json_limit(config: dict[str, Any]) -> int:
    """/** Resuelve límite de JSON presidenciales. / Resolve presidential JSON limit. **"""
    rules_thresholds = load_rules_thresholds()
    return int(
        rules_thresholds.get(
            "max_json_presidenciales", config.get("max_sources_per_cycle", 19)
        )
    )


def build_snapshot_queue(limit: int) -> list[Path]:
    """/** Construye lista ordenada de snapshots. / Build ordered snapshot list. **"""
    snapshots = sorted(DATA_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime)
    return snapshots[-limit:]


def process_snapshot_queue(
    snapshots: list[Path],
    checkpoint: dict[str, Any],
    *,
    run_id: str,
) -> tuple[list[str], int, Path | None]:
    """/** Procesa snapshots con checkpointing avanzado. / Process snapshots with advanced checkpointing. **"""
    processed_hashes = list(checkpoint.get("processed_hashes", []))
    start_index = int(checkpoint.get("current_index", 0))
    snapshot_index = collect_snapshot_index(limit=len(snapshots))
    latest_snapshot: Path | None = snapshots[-1] if snapshots else None

    for idx in range(start_index, len(snapshots)):
        snapshot_path = snapshots[idx]
        try:
            content_hash = compute_content_hash(snapshot_path)
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "snapshot_hash_failed path=%s error=%s",
                snapshot_path,
                exc,
            )
            continue
        processed_hashes.append(content_hash)
        save_resilience_checkpoint(
            run_id,
            "checkpoint",
            latest_snapshot=snapshot_path,
            content_hash=content_hash,
            processed_hashes=processed_hashes,
            snapshot_index=snapshot_index,
            current_index=idx + 1,
        )

    return processed_hashes, start_index, latest_snapshot


def save_resilience_checkpoint(
    run_id: str,
    stage: str | None,
    *,
    latest_snapshot: Path | None = None,
    content_hash: str | None = None,
    error: str | None = None,
    processed_hashes: list[str] | None = None,
    snapshot_index: list[dict[str, Any]] | None = None,
    current_index: int | None = None,
) -> None:
    """/** Guarda estado intermedio con hashes e índice JSON. / Persist intermediate state with hashes and JSON index. **"""
    existing = load_resilience_checkpoint()
    payload = {
        **existing,
        "run_id": run_id,
        "stage": stage or "unknown",
        "timestamp": utcnow().isoformat(),
        "hashes": collect_recent_hashes(),
        "snapshot_index": snapshot_index or collect_snapshot_index(),
        "latest_snapshot": latest_snapshot.name if latest_snapshot else existing.get("latest_snapshot"),
        "last_content_hash": content_hash or existing.get("last_content_hash"),
    }
    if error:
        payload["error"] = error
    if processed_hashes is not None:
        payload["processed_hashes"] = processed_hashes
    if current_index is not None:
        payload["current_index"] = current_index
    FAILURE_CHECKPOINT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def collect_recent_hashes(limit: int = 19) -> list[dict[str, Any]]:
    """/** Recolecta hashes recientes para checkpoint. / Collect recent hashes for checkpoint. **"""
    hash_files = sorted(
        HASH_DIR.glob("*.sha256"), key=lambda p: p.stat().st_mtime, reverse=True
    )
    hashes: list[dict[str, Any]] = []
    for hash_file in hash_files[:limit]:
        try:
            payload = json.loads(hash_file.read_text(encoding="utf-8"))
            hashes.append(
                {
                    "file": hash_file.name,
                    "hash": payload.get("hash"),
                    "chained_hash": payload.get("chained_hash"),
                }
            )
        except json.JSONDecodeError:
            logger.warning("checkpoint_hash_invalid path=%s", hash_file)
    return hashes


def clear_resilience_checkpoint() -> None:
    """/** Elimina checkpoint cuando el pipeline completa. / Remove checkpoint when pipeline completes. **"""
    if FAILURE_CHECKPOINT_PATH.exists():
        FAILURE_CHECKPOINT_PATH.unlink()


def should_run_stage(current_stage: str, start_stage: str) -> bool:
    """/** Determina si una etapa debe ejecutarse al reanudar. / Determine if a stage should run when resuming. **"""
    try:
        return RESILIENCE_STAGE_ORDER.index(current_stage) >= RESILIENCE_STAGE_ORDER.index(
            start_stage
        )
    except ValueError:
        return True


def run_command(command, description):
    """/** Ejecuta un comando del sistema. / Execute a system command. **"""
    print(f"[+] {description}: {' '.join(command)}")
    subprocess.run(command, check=True)


def latest_file(directory, pattern):
    """/** Obtiene archivo más reciente por patrón. / Get newest file by pattern. **"""
    files = sorted(
        directory.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True
    )
    return files[0] if files else None


def compute_content_hash(snapshot_path):
    """/** Calcula hash de contenido del snapshot. / Compute snapshot content hash. **"""
    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    normalized = json.dumps(payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(normalized).hexdigest()


def should_normalize(snapshot_path):
    """/** Determina si requiere normalización. / Determine if normalization is required. **"""
    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    return "resultados" in payload and "estadisticas" in payload




def build_alerts(anomalies, *, severity: str = "HIGH"):
    """/** Construye alertas desde anomalías. / Build alerts from anomalies. **"""
    if not anomalies:
        return []

    files = [a.get("file") for a in anomalies if a.get("file")]
    from_file = min(files) if files else "unknown"
    to_file = max(files) if files else "unknown"
    alerts = []
    for anomaly in anomalies:
        rule = anomaly.get("type", "ANOMALY")
        description = anomaly.get("description") or anomaly.get("descripcion")
        alert = {"rule": rule, "severity": severity}
        if description:
            alert["description"] = description
        alerts.append(alert)

    return [
        {
            "from": from_file,
            "to": to_file,
            "alerts": alerts,
        }
    ]


def emit_critical_alerts(
    critical_anomalies: list[dict[str, Any]],
    config: dict[str, Any],
    *,
    run_id: str,
) -> None:
    """/** Emite alertas críticas en JSON y log. / Emit critical alerts to JSON and log. **/"""
    if not critical_anomalies:
        return
    alerts_payload = build_alerts(critical_anomalies, severity="CRITICAL")
    alerts_log_path, alerts_output_path = resolve_alert_paths(config)
    alerts_output_path.parent.mkdir(parents=True, exist_ok=True)
    alerts_output_path.write_text(
        json.dumps(alerts_payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    alerts_log_path.parent.mkdir(parents=True, exist_ok=True)
    log_lines = [
        json.dumps(
            {
                "timestamp": utcnow().isoformat(),
                "run_id": run_id,
                "severity": "CRITICAL",
                "rule": alert.get("rule"),
                "description": alert.get("description", ""),
            },
            ensure_ascii=False,
        )
        for window in alerts_payload
        for alert in window.get("alerts", [])
    ]
    if log_lines:
        with alerts_log_path.open("a", encoding="utf-8") as handle:
            handle.write("\n".join(log_lines) + "\n")
    log_event(
        logger,
        logging.CRITICAL,
        "critical_alerts_detected",
        run_id=run_id,
        count=len(critical_anomalies),
    )


def critical_rules(config: dict[str, Any]):
    """/** Resuelve reglas críticas desde configuración. / Resolve critical rules from configuration. **"""
    raw_rules = config.get("alerts", {}).get("critical_anomaly_types", [])
    if isinstance(raw_rules, str):
        raw_list = [rule.strip() for rule in raw_rules.split(",") if rule.strip()]
    else:
        raw_list = [str(rule).strip() for rule in raw_rules if str(rule).strip()]
    return {rule.upper() for rule in raw_list}


def filter_critical_anomalies(anomalies, config: dict[str, Any]):
    """/** Filtra anomalías críticas según reglas. / Filter critical anomalies by rules. **"""
    rules = critical_rules(config)
    if not rules:
        return anomalies
    return [
        anomaly for anomaly in anomalies if anomaly.get("type", "").upper() in rules
    ]


def should_generate_report(state, now):
    """/** Determina si generar reporte por cadencia. / Determine if report cadence allows generation. **"""
    last_report = state.get("last_report_at")
    if not last_report:
        return True
    last_dt = datetime.fromisoformat(last_report)
    elapsed = now - last_dt
    return elapsed >= timedelta(hours=1)


def update_daily_summary(state, now, anomalies_count):
    """/** Actualiza resumen diario. / Update daily summary. **"""
    today = now.date().isoformat()
    daily = state.get("daily_summary", {})
    if daily.get("date") != today:
        if daily:
            summary_path = REPORTS_DIR / f"daily_summary_{daily['date']}.txt"
            summary_lines = [
                f"Resumen diario {daily['date']} UTC",
                f"Ejecuciones: {daily.get('runs', 0)}",
                f"Anomalías detectadas: {daily.get('anomalies', 0)}",
            ]
            summary_path.write_text("\n".join(summary_lines), encoding="utf-8")

        daily = {"date": today, "runs": 0, "anomalies": 0}

    daily["runs"] += 1
    daily["anomalies"] += anomalies_count
    state["daily_summary"] = daily


def run_pipeline(config: dict[str, Any]):
    """/** Ejecuta el pipeline completo. / Run the full pipeline. **"""
    now = utcnow()
    resilience_settings = load_resilience_settings(config)
    chaos_rng = build_chaos_rng(resilience_settings)
    state = load_state()
    checkpoint = load_pipeline_checkpoint()
    resilience_checkpoint = load_resilience_checkpoint()
    run_id = checkpoint.get("run_id") or resilience_checkpoint.get("run_id") or now.strftime(
        "%Y%m%d%H%M%S"
    )
    start_stage = "start"
    latest_snapshot: Path | None = None
    content_hash: str | None = None
    resume_stage = resilience_checkpoint.get("stage")
    resume_snapshot_name = resilience_checkpoint.get("latest_snapshot")
    if (
        resume_stage in RESILIENCE_STAGE_ORDER
        and resume_snapshot_name
        and resume_stage not in {"start", "healthcheck", "download"}
    ):
        candidate_snapshot = DATA_DIR / resume_snapshot_name
        if candidate_snapshot.exists():
            latest_snapshot = candidate_snapshot
            content_hash = resilience_checkpoint.get("last_content_hash")
            start_stage = resume_stage
            log_event(
                logger,
                logging.INFO,
                "pipeline_resume",
                run_id=run_id,
                stage=resume_stage,
                snapshot=resume_snapshot_name,
            )
    save_pipeline_checkpoint({"run_id": run_id, "stage": "start", "at": now.isoformat()})
    save_resilience_checkpoint(
        run_id,
        "start",
        latest_snapshot=latest_snapshot,
        content_hash=content_hash,
    )
    log_event(logger, logging.INFO, "pipeline_start", run_id=run_id)

    try:
        if should_run_stage("healthcheck", start_stage):
            save_pipeline_checkpoint(
                {"run_id": run_id, "stage": "healthcheck", "at": utcnow().isoformat()}
            )
            save_resilience_checkpoint(run_id, "healthcheck")
            maybe_inject_chaos_failure("healthcheck", resilience_settings, chaos_rng)
            health_ok = check_cne_connectivity(config)
            download_cmd = [sys.executable, "scripts/download_and_hash.py"]
            if not health_ok:
                log_event(
                    logger,
                    logging.WARNING,
                    "healthcheck_failed_fallback_mock",
                    run_id=run_id,
                )
                download_cmd.append("--mock")

            if should_run_stage("download", start_stage):
                save_pipeline_checkpoint(
                    {"run_id": run_id, "stage": "download", "at": utcnow().isoformat()}
                )
                save_resilience_checkpoint(run_id, "download")
                maybe_inject_chaos_failure("download", resilience_settings, chaos_rng)
                run_command(download_cmd, "descarga + hash")

        max_json = resolve_max_json_limit(config)
        snapshots = build_snapshot_queue(max_json)
        if snapshots:
            process_snapshot_queue(
                snapshots,
                resilience_checkpoint,
                run_id=run_id,
            )

        if latest_snapshot is None:
            latest_snapshot = snapshots[-1] if snapshots else latest_file(DATA_DIR, "*.json")
        if not latest_snapshot:
            print("[!] No se encontró snapshot para procesar")
            log_event(logger, logging.WARNING, "snapshot_missing", run_id=run_id)
            return

        content_hash = content_hash or compute_content_hash(latest_snapshot)
        if state.get("last_content_hash") == content_hash:
            state["last_run_at"] = now.isoformat()
            save_state(state)
            print("[i] Snapshot duplicado detectado, se omite procesamiento")
            log_event(logger, logging.INFO, "snapshot_duplicate", run_id=run_id)
            return

        state["last_content_hash"] = content_hash
        state["last_snapshot"] = latest_snapshot.name

        if should_run_stage("normalize", start_stage):
            save_pipeline_checkpoint(
                {"run_id": run_id, "stage": "normalize", "at": utcnow().isoformat()}
            )
            save_resilience_checkpoint(
                run_id,
                "normalize",
                latest_snapshot=latest_snapshot,
                content_hash=content_hash,
            )
            maybe_inject_chaos_failure("normalize", resilience_settings, chaos_rng)
            if should_normalize(latest_snapshot):
                run_command(
                    [sys.executable, "scripts/normalize_presidential.py"], "normalización"
                )
            else:
                print("[i] Normalización omitida: estructura no compatible")
                log_event(logger, logging.INFO, "normalize_skipped", run_id=run_id)

        if should_run_stage("analyze", start_stage):
            save_pipeline_checkpoint(
                {"run_id": run_id, "stage": "analyze", "at": utcnow().isoformat()}
            )
            save_resilience_checkpoint(
                run_id,
                "analyze",
                latest_snapshot=latest_snapshot,
                content_hash=content_hash,
            )
            maybe_inject_chaos_failure("analyze", resilience_settings, chaos_rng)
            run_command([sys.executable, "scripts/analyze_rules.py"], "análisis")

        anomalies_path = Path("anomalies_report.json")
        anomalies = []
        if anomalies_path.exists():
            anomalies = json.loads(anomalies_path.read_text(encoding="utf-8"))

        critical_anomalies = filter_critical_anomalies(anomalies, config)
        alerts = build_alerts(critical_anomalies, severity="CRITICAL")
        (ANALYSIS_DIR / "alerts.json").write_text(
            json.dumps(alerts, indent=2), encoding="utf-8"
        )
        emit_critical_alerts(critical_anomalies, config, run_id=run_id)

        if should_run_stage("report", start_stage):
            save_pipeline_checkpoint(
                {"run_id": run_id, "stage": "report", "at": utcnow().isoformat()}
            )
            save_resilience_checkpoint(
                run_id,
                "report",
                latest_snapshot=latest_snapshot,
                content_hash=content_hash,
            )
            maybe_inject_chaos_failure("report", resilience_settings, chaos_rng)
            if should_generate_report(state, now):
                run_command([sys.executable, "scripts/summarize_findings.py"], "reportes")
                state["last_report_at"] = now.isoformat()
            else:
                print("[i] Reporte omitido por cadencia")
                log_event(logger, logging.INFO, "report_skipped", run_id=run_id)

        if should_run_stage("anchor", start_stage):
            save_resilience_checkpoint(
                run_id,
                "anchor",
                latest_snapshot=latest_snapshot,
                content_hash=content_hash,
            )
            maybe_inject_chaos_failure("anchor", resilience_settings, chaos_rng)
            _anchor_snapshot(config, state, now, latest_snapshot)
            _anchor_if_due(config, state, now)

        update_daily_summary(state, now, len(anomalies))
        state["last_run_at"] = now.isoformat()
        save_state(state)
        clear_pipeline_checkpoint()
        clear_resilience_checkpoint()
        log_event(logger, logging.INFO, "pipeline_complete", run_id=run_id)
    except Exception as exc:  # noqa: BLE001
        log_event(
            logger,
            logging.ERROR,
            "pipeline_failed",
            run_id=run_id,
            error=str(exc),
        )
        save_resilience_checkpoint(
            run_id,
            checkpoint.get("stage") or "error",
            latest_snapshot=latest_snapshot,
            content_hash=content_hash,
            error=str(exc),
        )
        raise


def safe_run_pipeline(config: dict[str, Any]) -> None:
    """/** Ejecuta pipeline con protección contra fallas de red. / Run pipeline with protection against network failures. **"""
    resilience_settings = load_resilience_settings(config)
    auto_resume = build_auto_resume_settings(resilience_settings)
    attempt = 0
    while True:
        try:
            run_pipeline(config)
            return
        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            TimeoutError,
            ConnectionError,
        ) as exc:
            checkpoint = load_pipeline_checkpoint()
            run_id = checkpoint.get("run_id", utcnow().strftime("%Y%m%d%H%M%S"))
            stage = checkpoint.get("stage")
            log_event(
                logger,
                logging.ERROR,
                "pipeline_network_failure",
                run_id=run_id,
                stage=stage or "unknown",
                error=str(exc),
            )
            save_resilience_checkpoint(run_id, stage, error=str(exc))
            retry_on = auto_resume["retry_on"]
            retryable = retry_on in {"any", "network"}
            attempt += 1
            if not auto_resume["enabled"] or not retryable or attempt >= auto_resume["max_attempts"]:
                return
            delay = compute_backoff_delay(
                attempt, auto_resume["backoff_base_seconds"], auto_resume["backoff_max_seconds"]
            )
            log_event(
                logger,
                logging.WARNING,
                "pipeline_auto_resume_wait",
                run_id=run_id,
                attempt=attempt,
                delay_seconds=delay,
            )
            time.sleep(delay)
        except Exception as exc:
            checkpoint = load_pipeline_checkpoint()
            run_id = checkpoint.get("run_id", utcnow().strftime("%Y%m%d%H%M%S"))
            stage = checkpoint.get("stage")
            log_event(
                logger,
                logging.ERROR,
                "pipeline_failure",
                run_id=run_id,
                stage=stage or "unknown",
                error=str(exc),
            )
            save_resilience_checkpoint(run_id, stage, error=str(exc))
            attempt += 1
            if not auto_resume["enabled"] or auto_resume["retry_on"] != "any":
                raise
            if attempt >= auto_resume["max_attempts"]:
                raise
            delay = compute_backoff_delay(
                attempt, auto_resume["backoff_base_seconds"], auto_resume["backoff_max_seconds"]
            )
            log_event(
                logger,
                logging.WARNING,
                "pipeline_auto_resume_wait",
                run_id=run_id,
                attempt=attempt,
                delay_seconds=delay,
            )
            time.sleep(delay)


def _read_hashes_for_anchor(batch_size: int) -> list[str]:
    """/** Lee hashes recientes para anclaje en Arbitrum. / Read recent hashes for Arbitrum anchoring. **"""
    hash_files = sorted(
        HASH_DIR.glob("*.sha256"), key=lambda p: p.stat().st_mtime, reverse=True
    )
    selected = list(reversed(hash_files[:batch_size]))
    hashes: list[str] = []
    for hash_file in selected:
        try:
            payload = json.loads(hash_file.read_text(encoding="utf-8"))
            hash_value = payload.get("hash") or payload.get("chained_hash")
            if hash_value:
                hashes.append(hash_value)
        except json.JSONDecodeError:
            logger.warning("hash_file_invalid path=%s", hash_file)
    return hashes


def _should_anchor(state: dict[str, Any], now: datetime, interval_minutes: int) -> bool:
    """/** Determina si debe anclarse según intervalo. / Determine whether to anchor based on interval. **"""
    last_anchor = state.get("last_anchor_at")
    if not last_anchor:
        return True
    try:
        last_dt = datetime.fromisoformat(last_anchor)
    except ValueError:
        return True
    return now - last_dt >= timedelta(minutes=interval_minutes)


def _anchor_if_due(config: dict[str, Any], state: dict[str, Any], now: datetime) -> None:
    """/** Ejecuta anclaje de hashes si corresponde. / Execute hash anchoring when due. **"""
    arbitrum_config = config.get("arbitrum", {})
    if not arbitrum_config.get("enabled", False):
        return
    _ensure_decrypted_private_key(arbitrum_config)
    if not _has_private_key(arbitrum_config):
        logger.warning("anchor_skipped_missing_private_key")
        return

    interval_minutes = int(arbitrum_config.get("interval_minutes", 15))
    batch_size = int(arbitrum_config.get("batch_size", 19))
    if not _should_anchor(state, now, interval_minutes):
        return

    hashes = _read_hashes_for_anchor(batch_size)
    if len(hashes) < batch_size:
        logger.warning(
            "anchor_skipped_not_enough_hashes expected=%s actual=%s",
            batch_size,
            len(hashes),
        )
        return

    try:
        result = anchor_batch(hashes)
    except Exception as exc:  # noqa: BLE001
        logger.error("anchor_failed error=%s", exc)
        return

    anchor_record = {
        "batch_id": result.get("batch_id"),
        "root": result.get("root"),
        "tx_hash": result.get("tx_hash"),
        "timestamp": result.get("timestamp"),
        "individual_hashes": hashes,
    }
    anchor_path = ANCHOR_LOG_DIR / f"anchor_{anchor_record['batch_id']}.json"
    anchor_path.write_text(
        json.dumps(anchor_record, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    state["last_anchor_at"] = result.get("timestamp")


def _anchor_snapshot(
    config: dict[str, Any],
    state: dict[str, Any],
    now: datetime,
    snapshot_path: Path,
) -> None:
    """/** Genera hash raíz post-reglas y ancla snapshot. / Generate post-rule root hash and anchor snapshot. **"""
    arbitrum_config = config.get("arbitrum", {})
    if not arbitrum_config.get("enabled", False):
        return
    if not arbitrum_config.get("auto_anchor_snapshots", False):
        return
    _ensure_decrypted_private_key(arbitrum_config)
    if not _has_private_key(arbitrum_config):
        logger.warning("anchor_snapshot_skipped_missing_private_key")
        return

    current_payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    snapshots = sorted(DATA_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime)
    previous_snapshot = snapshots[-2] if len(snapshots) > 1 else None
    previous_payload = (
        json.loads(previous_snapshot.read_text(encoding="utf-8"))
        if previous_snapshot
        else None
    )

    diff_summary = build_diff_summary(previous_payload, current_payload)

    rules_report_path = ANALYSIS_DIR / f"rules_report_{snapshot_path.stem}.json"
    rules_payload: dict[str, Any] = {}
    if rules_report_path.exists():
        report = json.loads(rules_report_path.read_text(encoding="utf-8"))
        rules_payload = {
            "alerts": report.get("alerts", []),
            "critical_alerts": report.get("critical_alerts", []),
            "pause_snapshots": report.get("pause_snapshots", []),
        }

    anchor_hashes = compute_anchor_root(current_payload, diff_summary, rules_payload)
    root_hash = anchor_hashes["root_hash"]

    try:
        anchor_result = anchor_root(root_hash)
    except Exception as exc:  # noqa: BLE001
        logger.error("anchor_snapshot_failed error=%s", exc)
        return

    explorer_base = arbitrum_config.get("explorer_url", "https://arbiscan.io/tx/")
    tx_hash = anchor_result.get("tx_hash")
    tx_url = f"{explorer_base}{tx_hash}" if tx_hash else ""

    anchor_record = {
        "snapshot": snapshot_path.name,
        "root_hash": root_hash,
        "raw_hash": anchor_hashes["raw_hash"],
        "diffs_hash": anchor_hashes["diffs_hash"],
        "rules_hash": anchor_hashes["rules_hash"],
        "diff_summary": diff_summary,
        "rules_report_path": rules_report_path.as_posix(),
        "tx_hash": tx_hash,
        "tx_url": tx_url,
        "network": arbitrum_config.get("network", "Arbitrum One"),
        "anchored_at": anchor_result.get("timestamp"),
        "anchor_id": anchor_result.get("anchor_id"),
        "generated_at": now.isoformat(),
    }

    anchor_path = ANCHOR_LOG_DIR / f"anchor_snapshot_{snapshot_path.stem}.json"
    anchor_path.write_text(
        json.dumps(anchor_record, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    state["last_anchor_snapshot_at"] = anchor_result.get("timestamp")

    if rules_report_path.exists():
        report = json.loads(rules_report_path.read_text(encoding="utf-8"))
        report["blockchain_anchor"] = {
            "root_hash": root_hash,
            "tx_hash": tx_hash,
            "tx_url": tx_url,
            "network": anchor_record["network"],
            "anchored_at": anchor_result.get("timestamp"),
        }
        rules_report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    report_path = REPORTS_DIR / f"anchor_report_{snapshot_path.stem}.json"
    report_path.write_text(
        json.dumps(anchor_record, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main():
    """/** Punto de entrada principal. / Main entry point. **"""
    parser = argparse.ArgumentParser(
        description="Pipeline Proyecto C.E.N.T.I.N.E.L.: descarga → normaliza → hash → análisis → reportes → alertas"
    )
    parser.add_argument(
        "--once", action="store_true", help="Ejecuta una sola vez y sale"
    )
    parser.add_argument(
        "--run-now",
        action="store_true",
        help="Ejecuta inmediatamente antes del scheduler",
    )
    args = parser.parse_args()
    config = load_config()
    master_status = normalize_master_switch(config.get("master_switch"))
    print(f"[i] MASTER SWITCH: {master_status}")
    if not is_master_switch_on(config):
        print("[!] Ejecución detenida por switch maestro (OFF)")
        return

    if args.once:
        update_heartbeat(status="manual_once")
        safe_run_pipeline(config)
        update_heartbeat(status="manual_once_completed")
        return

    if args.run_now:
        update_heartbeat(status="manual_run_now")
        safe_run_pipeline(config)

    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(update_heartbeat, "interval", minutes=1)
    scheduler.add_job(lambda: safe_run_pipeline(config), CronTrigger(minute=0))
    print("[+] Scheduler activo: ejecución horaria en minuto 00 UTC")
    scheduler.start()


if __name__ == "__main__":
    main()
