import argparse
import hashlib
import json
import logging
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from anchor.arbitrum_anchor import anchor_batch
from scripts.download_and_hash import is_master_switch_on, normalize_master_switch
from sentinel.utils.config_loader import load_config

DATA_DIR = Path("data")
HASH_DIR = Path("hashes")
ANALYSIS_DIR = Path("analysis")
REPORTS_DIR = Path("reports")
ANCHOR_LOG_DIR = Path("logs") / "anchors"
STATE_PATH = DATA_DIR / "pipeline_state.json"

DATA_DIR.mkdir(exist_ok=True)
HASH_DIR.mkdir(exist_ok=True)
ANALYSIS_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)
ANCHOR_LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger(__name__)


def utcnow():
    return datetime.now(timezone.utc)


def load_state():
    if not STATE_PATH.exists():
        return {}
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def save_state(state):
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


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


def send_alert_if_configured(
    config: dict[str, Any], state: dict[str, Any], summary_path: Path, critical_count: int
):
    if critical_count <= 0:
        print("[i] Alertas omitidas: no hay errores críticos")
        return

    telegram_config = config.get("alerts", {}).get("telegram", {})
    if not telegram_config.get("enabled", False):
        print("[i] Alertas deshabilitadas: Telegram no está habilitado")
        return

    token = telegram_config.get("bot_token")
    chat_id = telegram_config.get("chat_id")
    if not token or not chat_id:
        print("[i] Alertas deshabilitadas: faltan credenciales de Telegram")
        return

    summary_text = summary_path.read_text(encoding="utf-8")
    latest_hash_file = latest_file(HASH_DIR, "*.sha256")
    if not latest_hash_file:
        print("[i] Alertas omitidas: no hay hash disponible")
        return

    alert_fingerprint = hashlib.sha256(summary_text.encode("utf-8")).hexdigest()
    if state.get("last_alert_hash") == alert_fingerprint:
        print("[i] Alertas omitidas: resumen ya enviado")
        return

    run_command(
        [
            sys.executable,
            "scripts/post_to_telegram.py",
            summary_text,
            str(latest_hash_file),
        ],
        "alertas",
    )
    state["last_alert_hash"] = alert_fingerprint


def run_pipeline(config: dict[str, Any]):
    now = utcnow()
    state = load_state()

    run_command([sys.executable, "scripts/download_and_hash.py"], "descarga + hash")

    latest_snapshot = latest_file(DATA_DIR, "*.json")
    if not latest_snapshot:
        print("[!] No se encontró snapshot para procesar")
        return

    content_hash = compute_content_hash(latest_snapshot)
    if state.get("last_content_hash") == content_hash:
        state["last_run_at"] = now.isoformat()
        save_state(state)
        print("[i] Snapshot duplicado detectado, se omite procesamiento")
        return

    state["last_content_hash"] = content_hash
    state["last_snapshot"] = latest_snapshot.name

    if should_normalize(latest_snapshot):
        run_command(
            [sys.executable, "scripts/normalize_presidential.py"], "normalización"
        )
    else:
        print("[i] Normalización omitida: estructura no compatible")

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

    if should_generate_report(state, now):
        run_command([sys.executable, "scripts/summarize_findings.py"], "reportes")
        state["last_report_at"] = now.isoformat()
        send_alert_if_configured(
            config, state, REPORTS_DIR / "summary.txt", len(critical_anomalies)
        )
    else:
        print("[i] Reporte omitido por cadencia")

    _anchor_if_due(config, state, now)

    update_daily_summary(state, now, len(anomalies))
    state["last_run_at"] = now.isoformat()
    save_state(state)


def _read_hashes_for_anchor(batch_size: int) -> list[str]:
    """Lee los hashes más recientes para anclaje en Arbitrum."""
    hash_files = sorted(
        HASH_DIR.glob(\"*.sha256\"), key=lambda p: p.stat().st_mtime, reverse=True
    )
    selected = list(reversed(hash_files[:batch_size]))
    hashes: list[str] = []
    for hash_file in selected:
        try:
            payload = json.loads(hash_file.read_text(encoding=\"utf-8\"))
            hash_value = payload.get(\"hash\") or payload.get(\"chained_hash\")
            if hash_value:
                hashes.append(hash_value)
        except json.JSONDecodeError:
            logger.warning(\"hash_file_invalid path=%s\", hash_file)
    return hashes


def _should_anchor(state: dict[str, Any], now: datetime, interval_minutes: int) -> bool:
    """Determina si debe ejecutarse el anclaje según intervalo."""
    last_anchor = state.get(\"last_anchor_at\")
    if not last_anchor:
        return True
    try:
        last_dt = datetime.fromisoformat(last_anchor)
    except ValueError:
        return True
    return now - last_dt >= timedelta(minutes=interval_minutes)


def _anchor_if_due(config: dict[str, Any], state: dict[str, Any], now: datetime) -> None:
    """Ejecuta el anclaje de hashes si corresponde."""
    arbitrum_config = config.get(\"arbitrum\", {})
    if not arbitrum_config.get(\"enabled\", False):
        return

    interval_minutes = int(arbitrum_config.get(\"interval_minutes\", 15))
    batch_size = int(arbitrum_config.get(\"batch_size\", 19))
    if not _should_anchor(state, now, interval_minutes):
        return

    hashes = _read_hashes_for_anchor(batch_size)
    if len(hashes) < batch_size:
        logger.warning(
            \"anchor_skipped_not_enough_hashes expected=%s actual=%s\",
            batch_size,
            len(hashes),
        )
        return

    try:
        result = anchor_batch(hashes)
    except Exception as exc:  # noqa: BLE001
        logger.error(\"anchor_failed error=%s\", exc)
        return

    anchor_record = {
        \"batch_id\": result.get(\"batch_id\"),
        \"root\": result.get(\"root\"),
        \"tx_hash\": result.get(\"tx_hash\"),
        \"timestamp\": result.get(\"timestamp\"),
        \"individual_hashes\": hashes,
    }
    anchor_path = ANCHOR_LOG_DIR / f\"anchor_{anchor_record['batch_id']}.json\"
    anchor_path.write_text(
        json.dumps(anchor_record, indent=2, ensure_ascii=False), encoding=\"utf-8\"
    )
    state[\"last_anchor_at\"] = result.get(\"timestamp\")


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
        run_pipeline(config)
        return

    if args.run_now:
        run_pipeline(config)

    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(lambda: run_pipeline(config), CronTrigger(minute=0))
    print("[+] Scheduler activo: ejecución horaria en minuto 00 UTC")
    scheduler.start()


if __name__ == "__main__":
    main()
