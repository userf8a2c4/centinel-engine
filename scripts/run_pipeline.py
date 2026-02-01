import argparse
import hashlib
import json
import logging
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from anchor.arbitrum_anchor import anchor_batch, anchor_root
from scripts.download_and_hash import is_master_switch_on, normalize_master_switch
from scripts.healthcheck import check_cne_connectivity
from scripts.logging_utils import configure_logging, log_event
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
    return datetime.now(timezone.utc)


def load_state():
    if not STATE_PATH.exists():
        return {}
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def save_state(state):
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def load_pipeline_checkpoint() -> dict[str, Any]:
    """Carga el checkpoint del pipeline si existe.

    English:
        Load the pipeline checkpoint when present.
    """
    if not PIPELINE_CHECKPOINT_PATH.exists():
        return {}
    return json.loads(PIPELINE_CHECKPOINT_PATH.read_text(encoding="utf-8"))


def save_pipeline_checkpoint(payload: dict[str, Any]) -> None:
    """Guarda el estado intermedio del pipeline en disco.

    English:
        Persist intermediate pipeline state to disk.
    """
    PIPELINE_CHECKPOINT_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def clear_pipeline_checkpoint() -> None:
    """Elimina el checkpoint si el pipeline finalizó correctamente.

    English:
        Remove the checkpoint once the pipeline completes successfully.
    """
    if PIPELINE_CHECKPOINT_PATH.exists():
        PIPELINE_CHECKPOINT_PATH.unlink()


def load_resilience_checkpoint() -> dict[str, Any]:
    """Carga checkpoint de resiliencia desde data/temp/checkpoint.json.

    English:
        Load resilience checkpoint from data/temp/checkpoint.json.
    """
    if not FAILURE_CHECKPOINT_PATH.exists():
        return {}
    try:
        payload = json.loads(FAILURE_CHECKPOINT_PATH.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except json.JSONDecodeError:
        logger.warning("resilience_checkpoint_invalid path=%s", FAILURE_CHECKPOINT_PATH)
        return {}


def collect_snapshot_index(limit: int = 19) -> list[dict[str, Any]]:
    """Genera índice JSON con los snapshots recientes (máximo 19).

    English:
        Generate a JSON index with recent snapshots (max 19).
    """
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


def save_resilience_checkpoint(
    run_id: str,
    stage: str | None,
    *,
    latest_snapshot: Path | None = None,
    content_hash: str | None = None,
    error: str | None = None,
) -> None:
    """Guarda estado intermedio con hashes e índice JSON.

    /** Checkpointing avanzado para reanudación. / Advanced checkpointing for resume. */

    English:
        Persist intermediate state with hashes and JSON index.
    """
    payload = {
        "run_id": run_id,
        "stage": stage or "unknown",
        "timestamp": utcnow().isoformat(),
        "hashes": collect_recent_hashes(),
        "snapshot_index": collect_snapshot_index(),
        "latest_snapshot": latest_snapshot.name if latest_snapshot else None,
        "last_content_hash": content_hash,
    }
    if error:
        payload["error"] = error
    FAILURE_CHECKPOINT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def collect_recent_hashes(limit: int = 19) -> list[dict[str, Any]]:
    """Recolecta hashes recientes para checkpoints de falla.

    English:
        Collect recent hashes for failure checkpoints.
    """
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
    """Elimina el checkpoint avanzado cuando el pipeline completa.

    English:
        Remove the advanced checkpoint when the pipeline completes.
    """
    if FAILURE_CHECKPOINT_PATH.exists():
        FAILURE_CHECKPOINT_PATH.unlink()


def should_run_stage(current_stage: str, start_stage: str) -> bool:
    """Determina si una etapa debe ejecutarse al reanudar.

    English:
        Determine if a stage should run when resuming.
    """
    try:
        return RESILIENCE_STAGE_ORDER.index(current_stage) >= RESILIENCE_STAGE_ORDER.index(
            start_stage
        )
    except ValueError:
        return True


def run_command(command, description):
    print(f"[+] {description}: {' '.join(command)}")
    subprocess.run(command, check=True)


def latest_file(directory, pattern):
    files = sorted(
        directory.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True
    )
    return files[0] if files else None


def compute_content_hash(snapshot_path):
    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    normalized = json.dumps(payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(normalized).hexdigest()


def should_normalize(snapshot_path):
    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    return "resultados" in payload and "estadisticas" in payload




def build_alerts(anomalies):
    if not anomalies:
        return []

    files = [a.get("file") for a in anomalies if a.get("file")]
    from_file = min(files) if files else "unknown"
    to_file = max(files) if files else "unknown"
    alerts = []
    for anomaly in anomalies:
        rule = anomaly.get("type", "ANOMALY")
        description = anomaly.get("description") or anomaly.get("descripcion")
        alert = {"rule": rule}
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


def critical_rules(config: dict[str, Any]):
    """Resuelve las reglas críticas desde config/config.yaml."""
    raw_rules = config.get("alerts", {}).get("critical_anomaly_types", [])
    if isinstance(raw_rules, str):
        raw_list = [rule.strip() for rule in raw_rules.split(",") if rule.strip()]
    else:
        raw_list = [str(rule).strip() for rule in raw_rules if str(rule).strip()]
    return {rule.upper() for rule in raw_list}


def filter_critical_anomalies(anomalies, config: dict[str, Any]):
    rules = critical_rules(config)
    if not rules:
        return anomalies
    return [
        anomaly for anomaly in anomalies if anomaly.get("type", "").upper() in rules
    ]


def should_generate_report(state, now):
    last_report = state.get("last_report_at")
    if not last_report:
        return True
    last_dt = datetime.fromisoformat(last_report)
    elapsed = now - last_dt
    return elapsed >= timedelta(hours=1)


def update_daily_summary(state, now, anomalies_count):
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
    now = utcnow()
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
                run_command(download_cmd, "descarga + hash")

        if latest_snapshot is None:
            latest_snapshot = latest_file(DATA_DIR, "*.json")
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
            run_command([sys.executable, "scripts/analyze_rules.py"], "análisis")

        anomalies_path = Path("anomalies_report.json")
        anomalies = []
        if anomalies_path.exists():
            anomalies = json.loads(anomalies_path.read_text(encoding="utf-8"))

        critical_anomalies = filter_critical_anomalies(anomalies, config)
        alerts = build_alerts(critical_anomalies)
        (ANALYSIS_DIR / "alerts.json").write_text(
            json.dumps(alerts, indent=2), encoding="utf-8"
        )

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
    """Ejecuta el pipeline con protección contra fallas de red.

    English:
        Run the pipeline with protection against network failures.
    """
    try:
        run_pipeline(config)
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
    except Exception:
        raise


def _read_hashes_for_anchor(batch_size: int) -> list[str]:
    """Lee los hashes más recientes para anclaje en Arbitrum."""
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
    """Determina si debe ejecutarse el anclaje según intervalo."""
    last_anchor = state.get("last_anchor_at")
    if not last_anchor:
        return True
    try:
        last_dt = datetime.fromisoformat(last_anchor)
    except ValueError:
        return True
    return now - last_dt >= timedelta(minutes=interval_minutes)


def _anchor_if_due(config: dict[str, Any], state: dict[str, Any], now: datetime) -> None:
    """Ejecuta el anclaje de hashes si corresponde."""
    arbitrum_config = config.get("arbitrum", {})
    if not arbitrum_config.get("enabled", False):
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
    """Genera hash raíz post-reglas y ancla automáticamente el snapshot."""
    arbitrum_config = config.get("arbitrum", {})
    if not arbitrum_config.get("enabled", False):
        return
    if not arbitrum_config.get("auto_anchor_snapshots", False):
        return
    if not arbitrum_config.get("private_key"):
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
        safe_run_pipeline(config)
        return

    if args.run_now:
        safe_run_pipeline(config)

    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(lambda: safe_run_pipeline(config), CronTrigger(minute=0))
    print("[+] Scheduler activo: ejecución horaria en minuto 00 UTC")
    scheduler.start()


if __name__ == "__main__":
    main()
