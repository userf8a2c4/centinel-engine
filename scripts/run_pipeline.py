import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path("data")
HASH_DIR = Path("hashes")
ANALYSIS_DIR = Path("analysis")
REPORTS_DIR = Path("reports")
STATE_PATH = DATA_DIR / "pipeline_state.json"

DATA_DIR.mkdir(exist_ok=True)
HASH_DIR.mkdir(exist_ok=True)
ANALYSIS_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)


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
    rules = sorted({a.get("type", "ANOMALY") for a in anomalies})

    return [
        {
            "from": from_file,
            "to": to_file,
            "alerts": [{"rule": rule} for rule in rules],
        }
    ]


def critical_rules():
    raw = os.getenv(
        "CRITICAL_ANOMALY_TYPES",
        "ARITHMETIC_MISMATCH,NEGATIVE_DELTA,CHANGE_POINT,RELATIVE_DELTA,SCRUTINY_JUMP,VOTE_BREAKDOWN_MISMATCH",
    )
    return {rule.strip().upper() for rule in raw.split(",") if rule.strip()}


def filter_critical_anomalies(anomalies):
    rules = critical_rules()
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


def send_alert_if_configured(state, summary_path, critical_count):
    if critical_count <= 0:
        print("[i] Alertas omitidas: no hay errores críticos")
        return

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
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


def run_pipeline():
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

    critical_anomalies = filter_critical_anomalies(anomalies)
    alerts = build_alerts(critical_anomalies)
    (ANALYSIS_DIR / "alerts.json").write_text(
        json.dumps(alerts, indent=2), encoding="utf-8"
    )

    if should_generate_report(state, now):
        run_command([sys.executable, "scripts/summarize_findings.py"], "reportes")
        state["last_report_at"] = now.isoformat()
        send_alert_if_configured(
            state, REPORTS_DIR / "summary.txt", len(critical_anomalies)
        )
    else:
        print("[i] Reporte omitido por cadencia")

    update_daily_summary(state, now, len(anomalies))
    state["last_run_at"] = now.isoformat()
    save_state(state)


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

    if args.once:
        run_pipeline()
        return

    if args.run_now:
        run_pipeline()

    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(run_pipeline, CronTrigger(minute=0))
    print("[+] Scheduler activo: ejecución horaria en minuto 00 UTC")
    scheduler.start()


if __name__ == "__main__":
    main()
