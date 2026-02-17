"""
CLI delgado para ejecutar el motor unificado de reglas.

Toda la lógica de ejecución, verificación de hashchain y generación de
reportes vive en ``RulesEngine``.  Este script sólo resuelve rutas de
snapshots, carga configuración y delega a ``RulesEngine.run()``.

Thin CLI wrapper for the unified rules engine.

All execution logic, hashchain verification, and report generation lives in
``RulesEngine``.  This script only resolves snapshot paths, loads config, and
delegates to ``RulesEngine.run()``.
"""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from typing import Any, Optional

from centinel.paths import iter_all_snapshots

import yaml

from centinel.core.rules.common import extract_candidate_votes, extract_total_votes
from centinel.core.rules_engine import RulesEngine
from centinel.utils.config_loader import CONFIG_PATH, load_config

ANALYSIS_DIR = Path("analysis")

PRESIDENTIAL_LEVELS = {
    "PRES",
    "PRESIDENTE",
    "PRESIDENCIAL",
    "PRESIDENTIAL",
}

UNWANTED_KEYS = {"actas", "mesas", "tables"}


# ── config & snapshot helpers ────────────────────────────────────────────


def _load_config() -> dict:
    """Carga la configuración desde config.yaml o el ejemplo.

    English:
        Load configuration from config.yaml or the example file.
    """
    if CONFIG_PATH.exists():
        return load_config()
    example_path = Path("command_center") / "config.yaml.example"
    if example_path.exists():
        return yaml.safe_load(example_path.read_text(encoding="utf-8")) or {}
    return {}


def _load_snapshot(path: Path) -> dict:
    """Lee y parsea un snapshot JSON.

    English:
        Read and parse a JSON snapshot.
    """
    return json.loads(path.read_text(encoding="utf-8"))


def _latest_snapshots() -> tuple[Optional[Path], Optional[Path]]:
    """Ubica los dos snapshots más recientes.

    English:
        Locate the two most recent snapshots.
    """
    normalized_dir = Path("normalized")
    candidates = sorted(
        normalized_dir.glob("*.normalized.json"),
        key=lambda path: path.stat().st_mtime,
    )
    if not candidates:
        candidates = iter_all_snapshots(data_root=Path("data"))
    if not candidates:
        return None, None
    current = candidates[-1]
    previous = candidates[-2] if len(candidates) > 1 else None
    return current, previous


# ── presidential filtering helpers ───────────────────────────────────────


def _normalize_level(level: Optional[str]) -> Optional[str]:
    if level is None:
        return None
    return str(level).strip().upper()


def _extract_level(payload: dict) -> Optional[str]:
    metadata = payload.get("meta") or payload.get("metadata") or {}
    return (
        payload.get("election_level")
        or payload.get("nivel")
        or payload.get("level")
        or payload.get("tipo")
        or metadata.get("election_level")
    )


def _extract_department(payload: dict) -> Optional[str]:
    metadata = payload.get("meta") or payload.get("metadata") or {}
    return (
        payload.get("departamento")
        or payload.get("department")
        or payload.get("dep")
        or metadata.get("department")
        or metadata.get("departamento")
    )


def _strip_unwanted_fields(payload: dict) -> dict:
    return {key: value for key, value in payload.items() if key not in UNWANTED_KEYS}


def _build_source_map(config: dict) -> dict[str, dict[str, Any]]:
    source_map: dict[str, dict[str, Any]] = {}
    for source in config.get("sources", []):
        source_id = source.get("source_id") or source.get("name")
        if not source_id:
            continue
        source_map[str(source_id)] = source
    return source_map


def _normalize_department_label(label: str) -> str:
    cleaned = unicodedata.normalize("NFKD", label)
    cleaned = "".join(char for char in cleaned if not unicodedata.combining(char))
    return cleaned.strip().upper()


def _allowed_departments(config: dict) -> set[str]:
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
    totals_by_candidate: dict[str, int] = {}
    total_votes_sum = 0
    for entry in entries:
        for candidate_id, candidate in extract_candidate_votes(entry).items():
            votes = candidate.get("votes")
            if votes is None:
                continue
            totals_by_candidate[str(candidate_id)] = totals_by_candidate.get(str(candidate_id), 0) + int(votes)
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
        _normalize_department_label(str(entry.get("departamento", ""))) == "NACIONAL" for entry in filtered
    ):
        filtered.append(_aggregate_national(filtered))

    return {
        "timestamp": snapshot.get("timestamp"),
        "source": snapshot_source,
        "source_url": snapshot.get("source_url"),
        "departments": filtered,
    }


# ── hashchain path helper ───────────────────────────────────────────────


def _locate_hashchain(current_path: Path) -> Optional[Path]:
    if current_path.parent.name == "normalized":
        candidate = current_path.parent.parent / "hashchain.json"
        if candidate.exists():
            return candidate
    candidate = current_path.parent / "hashchain.json"
    if candidate.exists():
        return candidate
    return None


# ── main ─────────────────────────────────────────────────────────────────


def main() -> None:
    """Punto de entrada CLI: delega todo a RulesEngine.

    English:
        CLI entry point: delegates everything to RulesEngine.
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
    previous_data = _filter_presidential_snapshot(_load_snapshot(previous_path), config) if previous_path else None

    log_path = ANALYSIS_DIR / "rules_log.jsonl"
    engine = RulesEngine(config=config, log_path=log_path)
    snapshot_id = RulesEngine.snapshot_hash(current_data)

    # ── ejecutar TODAS las reglas ────────────────────────────────────
    result = engine.run(current_data, previous_data, snapshot_id=snapshot_id)

    # ── verificar hashchain ──────────────────────────────────────────
    hashchain_path = _locate_hashchain(current_path)
    if hashchain_path and current_path.parent.name == "normalized":
        tamper_alerts = RulesEngine.verify_hashchain(current_path.parent, hashchain_path)
        if tamper_alerts:
            result.alerts.extend(tamper_alerts)
            result.critical_alerts.extend(tamper_alerts)

    # ── generar reportes ─────────────────────────────────────────────
    report_path = RulesEngine.write_report(result, current_path, snapshot_id, ANALYSIS_DIR)

    print(f"[i] Reporte generado: {report_path}")
    if result.pause_snapshots:
        print("[!] Alertas críticas detectadas: se debe pausar el ingreso de snapshots")


if __name__ == "__main__":
    main()
