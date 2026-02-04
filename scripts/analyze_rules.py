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
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

import yaml

from sentinel.core.hashchain import compute_hash
from sentinel.core.rules.common import extract_candidate_votes, extract_total_votes
from sentinel.core.rules_engine import RulesEngine
from sentinel.utils.config_loader import CONFIG_PATH, load_config

ANALYSIS_DIR = Path("analysis")
ANALYSIS_DIR.mkdir(exist_ok=True)

RuleFn = Callable[[dict, Optional[dict], dict], list[dict]]
RULES: list[tuple[str, RuleFn]] = []


def run_all_rules(current: dict, previous: Optional[dict], config: dict) -> list[dict]:
    """Run configured rules respecting enablement flags."""
    rules_config = config.get("rules", {}) if config else {}
    if not rules_config.get("global_enabled", True):
        return []

    alerts: list[dict] = []
    for name, rule in RULES:
        rule_config = rules_config.get(name, {})
        if rule_config.get("enabled", True) is False:
            continue
        alerts.extend(rule(current, previous, config))
    return alerts


PRESIDENTIAL_LEVELS = {
    "PRES",
    "PRESIDENTE",
    "PRESIDENCIAL",
    "PRESIDENTIAL",
}

UNWANTED_KEYS = {"actas", "mesas", "tables"}


def _load_config() -> dict:
    """Español: Función _load_config del módulo scripts/analyze_rules.py.

    English: Function _load_config defined in scripts/analyze_rules.py.
    """
    if CONFIG_PATH.exists():
        return load_config()
    example_path = Path("command_center") / "config.yaml.example"
    if example_path.exists():
        return yaml.safe_load(example_path.read_text(encoding="utf-8")) or {}
    return {}


def _load_snapshot(path: Path) -> dict:
    """Español: Función _load_snapshot del módulo scripts/analyze_rules.py.

    English: Function _load_snapshot defined in scripts/analyze_rules.py.
    """
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize_level(level: Optional[str]) -> Optional[str]:
    """Español: Función _normalize_level del módulo scripts/analyze_rules.py.

    English: Function _normalize_level defined in scripts/analyze_rules.py.
    """
    if level is None:
        return None
    return str(level).strip().upper()


def _extract_level(payload: dict) -> Optional[str]:
    """Español: Función _extract_level del módulo scripts/analyze_rules.py.

    English: Function _extract_level defined in scripts/analyze_rules.py.
    """
    metadata = payload.get("meta") or payload.get("metadata") or {}
    return (
        payload.get("election_level")
        or payload.get("nivel")
        or payload.get("level")
        or payload.get("tipo")
        or metadata.get("election_level")
    )


def _extract_department(payload: dict) -> Optional[str]:
    """Español: Función _extract_department del módulo scripts/analyze_rules.py.

    English: Function _extract_department defined in scripts/analyze_rules.py.
    """
    metadata = payload.get("meta") or payload.get("metadata") or {}
    return (
        payload.get("departamento")
        or payload.get("department")
        or payload.get("dep")
        or metadata.get("department")
        or metadata.get("departamento")
    )


def _strip_unwanted_fields(payload: dict) -> dict:
    """Español: Función _strip_unwanted_fields del módulo scripts/analyze_rules.py.

    English: Function _strip_unwanted_fields defined in scripts/analyze_rules.py.
    """
    return {key: value for key, value in payload.items() if key not in UNWANTED_KEYS}


def _build_source_map(config: dict) -> dict[str, dict[str, Any]]:
    """Español: Función _build_source_map del módulo scripts/analyze_rules.py.

    English: Function _build_source_map defined in scripts/analyze_rules.py.
    """
    source_map: dict[str, dict[str, Any]] = {}
    for source in config.get("sources", []):
        source_id = source.get("source_id") or source.get("name")
        if not source_id:
            continue
        source_map[str(source_id)] = source
    return source_map


def _normalize_department_label(label: str) -> str:
    """Español: Función _normalize_department_label del módulo scripts/analyze_rules.py.

    English: Function _normalize_department_label defined in scripts/analyze_rules.py.
    """
    cleaned = unicodedata.normalize("NFKD", label)
    cleaned = "".join(char for char in cleaned if not unicodedata.combining(char))
    return cleaned.strip().upper()


def _allowed_departments(config: dict) -> set[str]:
    """Español: Función _allowed_departments del módulo scripts/analyze_rules.py.

    English: Function _allowed_departments defined in scripts/analyze_rules.py.
    """
    departments: set[str] = set()
    for source in config.get("sources", []):
        if source.get("scope") != "DEPARTMENT":
            continue
        if source.get("department_code"):
            departments.add(_normalize_department_label(str(source["department_code"])))
        if source.get("name"):
            departments.add(_normalize_department_label(str(source["name"])))
    departments.add(_normalize_department_label("NACIONAL"))
    return departments


def _aggregate_national(entries: list[dict]) -> dict:
    """Español: Función _aggregate_national del módulo scripts/analyze_rules.py.

    English: Function _aggregate_national defined in scripts/analyze_rules.py.
    """
    totals_by_candidate: dict[str, int] = {}
    total_votes_sum = 0
    for entry in entries:
        for candidate_id, candidate in extract_candidate_votes(entry).items():
            votes = candidate.get("votes")
            if votes is None:
                continue
            totals_by_candidate[str(candidate_id)] = totals_by_candidate.get(
                str(candidate_id), 0
            ) + int(votes)
        entry_total = extract_total_votes(entry)
        if entry_total is not None:
            total_votes_sum += int(entry_total)

    return {
        "departamento": "NACIONAL",
        "nivel": "PRES",
        "resultados": totals_by_candidate,
        "totals": {"total_votes": total_votes_sum} if total_votes_sum else {},
        "metadata": {"aggregated": True},
    }


def _filter_presidential_snapshot(snapshot: dict, config: dict) -> dict:
    """Español: Función _filter_presidential_snapshot del módulo scripts/analyze_rules.py.

    English: Function _filter_presidential_snapshot defined in scripts/analyze_rules.py.
    """
    source_map = _build_source_map(config)
    allowed_departments = _allowed_departments(config)
    scope = {scope.lower() for scope in config.get("scope", ["presidential"])}
    allowed_levels = {level for level in PRESIDENTIAL_LEVELS}

    snapshot_source = snapshot.get("source")
    snapshot_entries = snapshot.get("data")
    if isinstance(snapshot_entries, list):
        entries = snapshot_entries
    else:
        entries = [snapshot]

    filtered: list[dict] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        source_info = source_map.get(str(snapshot_source)) if snapshot_source else None
        level = _normalize_level(_extract_level(entry))
        if not level and source_info:
            level = _normalize_level(source_info.get("level"))
        if "presidential" in scope and level not in allowed_levels:
            continue

        department = _extract_department(entry)
        if not department and source_info:
            department = source_info.get("name") or source_info.get("department_code")
        department = (department or "NACIONAL").strip()
        department_upper = _normalize_department_label(department)
        if department_upper not in allowed_departments:
            continue

        sanitized = _strip_unwanted_fields(entry)
        sanitized["departamento"] = department
        sanitized["nivel"] = level or "PRES"
        filtered.append(sanitized)

    if filtered and not any(
        _normalize_department_label(str(entry.get("departamento", ""))) == "NACIONAL"
        for entry in filtered
    ):
        filtered.append(_aggregate_national(filtered))

    return {
        "timestamp": snapshot.get("timestamp"),
        "source": snapshot_source,
        "source_url": snapshot.get("source_url"),
        "departments": filtered,
    }


def _snapshot_hash(payload: dict) -> str:
    """Español: Función _snapshot_hash del módulo scripts/analyze_rules.py.

    English: Function _snapshot_hash defined in scripts/analyze_rules.py.
    """
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _latest_snapshots() -> tuple[Optional[Path], Optional[Path]]:
    """Español: Función _latest_snapshots del módulo scripts/analyze_rules.py.

    English: Function _latest_snapshots defined in scripts/analyze_rules.py.
    """
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
    """Español: Función _locate_hashchain del módulo scripts/analyze_rules.py.

    English: Function _locate_hashchain defined in scripts/analyze_rules.py.
    """
    if current_path.parent.name == "normalized":
        candidate = current_path.parent.parent / "hashchain.json"
        if candidate.exists():
            return candidate
    candidate = current_path.parent / "hashchain.json"
    if candidate.exists():
        return candidate
    return None


def _verify_hashchain(normalized_dir: Path, hashchain_path: Path) -> list[dict]:
    """Español: Función _verify_hashchain del módulo scripts/analyze_rules.py.

    English: Function _verify_hashchain defined in scripts/analyze_rules.py.
    """
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
    """Español: Función main del módulo scripts/analyze_rules.py.

    English: Function main defined in scripts/analyze_rules.py.
    """
    current_path, previous_path = _latest_snapshots()
    if not current_path:
        print("[!] No se encontraron snapshots para analizar")
        return

    config = _load_config()
    current_data = _filter_presidential_snapshot(
        _load_snapshot(current_path),
        config,
    )
    previous_data = (
        _filter_presidential_snapshot(_load_snapshot(previous_path), config)
        if previous_path
        else None
    )
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
