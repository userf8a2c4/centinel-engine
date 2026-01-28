"""
Motor avanzado de reglas para detección de anomalías electorales.

Este módulo ejecuta reglas estadísticas avanzadas sobre el snapshot más reciente
comparándolo con el snapshot anterior. Genera reportes JSON y logs estructurados
para auditoría internacional.

Advanced rules engine for electoral anomaly detection.

This module runs advanced statistical rules on the latest snapshot and compares
it with the previous snapshot. It generates JSON reports and structured logs for
international auditing.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml

from sentinel.core.hashchain import compute_hash
from sentinel.core.rules_engine import RulesEngine
from sentinel.utils.config_loader import CONFIG_PATH, load_config

ANALYSIS_DIR = Path("analysis")
ANALYSIS_DIR.mkdir(exist_ok=True)


def _load_config() -> dict:
    if CONFIG_PATH.exists():
        return load_config()
    example_path = Path("command_center") / "config.yaml.example"
    if example_path.exists():
        return yaml.safe_load(example_path.read_text(encoding="utf-8")) or {}
    return {}


def _load_snapshot(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _snapshot_hash(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _latest_snapshots() -> tuple[Optional[Path], Optional[Path]]:
    normalized_dir = Path("normalized")
    candidates = sorted(
        normalized_dir.glob("*.normalized.json"),
        key=lambda path: path.stat().st_mtime,
    )
    if not candidates:
        candidates = sorted(
            Path("data").glob("*.json"),
            key=lambda path: path.stat().st_mtime,
        )
    if not candidates:
        return None, None
    current = candidates[-1]
    previous = candidates[-2] if len(candidates) > 1 else None
    return current, previous


def _locate_hashchain(current_path: Path) -> Optional[Path]:
    if current_path.parent.name == "normalized":
        candidate = current_path.parent.parent / "hashchain.json"
        if candidate.exists():
            return candidate
    candidate = current_path.parent / "hashchain.json"
    if candidate.exists():
        return candidate
    return None


def _verify_hashchain(normalized_dir: Path, hashchain_path: Path) -> list[dict]:
    alerts: list[dict] = []
    try:
        entries = json.loads(hashchain_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return alerts

    previous_hash: Optional[str] = None
    for entry in entries:
        snapshot_name = entry.get("snapshot")
        if not snapshot_name:
            continue
        snapshot_path = normalized_dir / f"{snapshot_name}.json"
        if not snapshot_path.exists():
            alerts.append(
                {
                    "type": "Hashchain Inconsistente",
                    "severity": "CRITICAL",
                    "snapshot": snapshot_name,
                    "justification": (
                        "Falta el snapshot esperado en el directorio normalizado. "
                        f"snapshot={snapshot_name}."
                    ),
                }
            )
            previous_hash = entry.get("hash") or previous_hash
            continue
        canonical_json = snapshot_path.read_text(encoding="utf-8").strip()
        expected_previous = entry.get("previous_hash")
        if expected_previous != previous_hash:
            alerts.append(
                {
                    "type": "Hashchain Inconsistente",
                    "severity": "CRITICAL",
                    "snapshot": snapshot_name,
                    "justification": (
                        "El hash previo no coincide con la cadena esperada. "
                        f"previo_esperado={expected_previous}, "
                        f"previo_calculado={previous_hash}."
                    ),
                }
            )
        computed_hash = compute_hash(canonical_json, previous_hash)
        expected_hash = entry.get("hash")
        if expected_hash != computed_hash:
            alerts.append(
                {
                    "type": "Tampering Retroactivo (Hashchain)",
                    "severity": "CRITICAL",
                    "snapshot": snapshot_name,
                    "justification": (
                        "El hash encadenado no coincide con el contenido canónico. "
                        f"hash_esperado={expected_hash}, hash_calculado={computed_hash}."
                    ),
                }
            )
        previous_hash = expected_hash or previous_hash
    return alerts


def main() -> None:
    current_path, previous_path = _latest_snapshots()
    if not current_path:
        print("[!] No se encontraron snapshots para analizar")
        return

    current_data = _load_snapshot(current_path)
    previous_data = _load_snapshot(previous_path) if previous_path else None

    config = _load_config()
    log_path = ANALYSIS_DIR / "rules_log.jsonl"
    engine = RulesEngine(config=config, log_path=log_path)
    snapshot_id = _snapshot_hash(current_data)

    result = engine.run(current_data, previous_data, snapshot_id=snapshot_id)

    tamper_alerts: list[dict] = []
    hashchain_path = _locate_hashchain(current_path)
    if hashchain_path and current_path.parent.name == "normalized":
        tamper_alerts = _verify_hashchain(current_path.parent, hashchain_path)
        if tamper_alerts:
            result.alerts.extend(tamper_alerts)
            result.critical_alerts.extend(tamper_alerts)

    report = {
        "snapshot": {
            "path": current_path.as_posix(),
            "hash": snapshot_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        "alerts": result.alerts,
        "critical_alerts": result.critical_alerts,
        "pause_snapshots": result.pause_snapshots or bool(tamper_alerts),
    }

    report_path = ANALYSIS_DIR / f"rules_report_{current_path.stem}.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    Path("anomalies_report.json").write_text(
        json.dumps(result.alerts, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"[i] Reporte generado: {report_path}")
    if result.pause_snapshots:
        print("[!] Alertas críticas detectadas: se debe pausar el ingreso de snapshots")


if __name__ == "__main__":
    main()
