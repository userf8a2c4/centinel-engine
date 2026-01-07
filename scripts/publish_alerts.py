import datetime
import hashlib
import json
import os
import sys
from typing import List, Dict

SCRIPT_DIR = os.path.dirname(__file__)
sys.path.append(SCRIPT_DIR)

import post_to_telegram
import post_to_x

DEFAULT_ANOMALY_PATH = os.getenv("ANOMALY_REPORT_PATH", "anomalies_report.json")
LOG_PATH = os.getenv("PUBLICATION_LOG_PATH", "logs/publication_log.jsonl")
MIN_ANOMALIES = int(os.getenv("MIN_ANOMALIES", "1"))
MIN_NEGATIVE_DELTA = int(os.getenv("MIN_NEGATIVE_DELTA", "1"))


def critical_rules() -> set[str]:
    raw = os.getenv("CRITICAL_ANOMALY_TYPES", "ARITHMETIC_MISMATCH,NEGATIVE_DELTA,CHANGE_POINT")
    return {rule.strip().upper() for rule in raw.split(",") if rule.strip()}


def filter_critical_anomalies(anomalies: List[Dict]) -> List[Dict]:
    rules = critical_rules()
    if not rules:
        return anomalies
    return [anomaly for anomaly in anomalies if anomaly.get("type", "").upper() in rules]


def load_anomalies(path: str) -> List[Dict]:
    if not os.path.exists(path):
        print(f"[!] ANOMALY_REPORT_NOT_FOUND: {path}")
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def filter_anomalies(anomalies: List[Dict]) -> List[Dict]:
    filtered = []
    for anomaly in anomalies:
        if anomaly.get("type") == "NEGATIVE_DELTA":
            loss = int(anomaly.get("loss", 0))
            if abs(loss) >= MIN_NEGATIVE_DELTA:
                filtered.append(anomaly)
        else:
            filtered.append(anomaly)
    return filtered


def build_summary(anomalies: List[Dict]) -> str:
    if not anomalies:
        return "No anomalies recorded in the latest audit."

    lines = [f"Anomalies detected: {len(anomalies)}"]
    for anomaly in anomalies[:5]:
        if anomaly.get("type") == "NEGATIVE_DELTA":
            entity = anomaly.get("entity", "unknown")
            loss = anomaly.get("loss", "n/a")
            file_name = anomaly.get("file", "unknown")
            lines.append(f"- NEGATIVE_DELTA | {entity} | {loss} votes | {file_name}")
        else:
            lines.append(f"- {anomaly.get('type', 'UNKNOWN')} | {anomaly.get('file', 'unknown')}")
    return "\n".join(lines)


def build_message(summary: str) -> str:
    header = "AUTOMATED ALERT" if "Anomalies detected" in summary else "AUTOMATED STATUS"
    return f"{header}\n{summary}"


def ensure_log_dir(path: str) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)


def hash_message(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def log_publication(entry: Dict) -> None:
    ensure_log_dir(LOG_PATH)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def publish(summary: str, hash_path: str, channels: List[str]) -> None:
    timestamp = datetime.datetime.utcnow().isoformat() + "Z"
    message = build_message(summary)
    message_hash = hash_message(message)
    file_hash = post_to_telegram.get_stored_hash(hash_path) if hash_path else None

    for channel in channels:
        entry = {
            "timestamp": timestamp,
            "channel": channel,
            "message_hash": message_hash,
            "verification_hash": file_hash,
            "template": "neutral",
            "anomaly_threshold": MIN_ANOMALIES,
            "negative_delta_threshold": MIN_NEGATIVE_DELTA,
            "summary": summary,
        }
        try:
            if channel == "telegram":
                post_to_telegram.send_message(message, stored_hash=file_hash, template_name="neutral")
            elif channel == "x":
                formatted = post_to_x.format_as_neutral(message, file_hash)
                post_to_x.send_message(post_to_x.truncate_for_x(formatted))
            else:
                print(f"[!] UNKNOWN_CHANNEL: {channel}")
                entry["status"] = "unknown_channel"
                log_publication(entry)
                continue
            entry["status"] = "sent"
        except SystemExit:
            entry["status"] = "failed"
        log_publication(entry)


def main():
    anomalies = load_anomalies(DEFAULT_ANOMALY_PATH)
    critical_only = filter_critical_anomalies(anomalies)
    filtered = filter_anomalies(critical_only)

    if len(filtered) < MIN_ANOMALIES:
        summary = (
            f"Critical anomalies detected: {len(filtered)} (below threshold {MIN_ANOMALIES}). "
            "No alert published."
        )
        log_publication({
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "channel": "all",
            "status": "skipped_threshold",
            "summary": summary,
            "anomaly_threshold": MIN_ANOMALIES,
            "negative_delta_threshold": MIN_NEGATIVE_DELTA,
            "critical_types": sorted(critical_rules()),
        })
        print("[i] ALERT_SKIPPED_THRESHOLD")
        return

    summary = build_summary(filtered)
    hash_path = sys.argv[1] if len(sys.argv) > 1 else None
    channels = sys.argv[2:] if len(sys.argv) > 2 else ["telegram", "x"]
    publish(summary, hash_path, channels)


if __name__ == "__main__":
    main()
