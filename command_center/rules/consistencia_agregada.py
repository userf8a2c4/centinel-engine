"""Regla de consistencia agregada entre departamentos y nivel nacional.

Aggregated consistency rule between departments and national level.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable

import yaml


def _load_rules_config() -> dict:
    """Carga reglas desde command_center/rules.yaml."""
    rules_path = Path(__file__).resolve().parents[1] / "rules.yaml"
    if not rules_path.exists():
        return {}
    try:
        with rules_path.open("r", encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}
    except (OSError, yaml.YAMLError):
        return {}


def _get_rule_config(config: dict, rule_key: str) -> dict:
    rules_section = config.get("rules", {})
    if isinstance(rules_section, dict) and rule_key in rules_section:
        return rules_section.get(rule_key, {}) or {}
    return config.get(rule_key, {}) or {}


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(str(value).replace(",", "").split(".")[0])
    except (ValueError, TypeError):
        return default


def _extract_departments(data: dict) -> Iterable[dict]:
    for key in ("departamentos", "departments", "by_department", "por_departamento"):
        departments = data.get(key)
        if isinstance(departments, list):
            return departments
        if isinstance(departments, dict):
            return departments.values()
    return []


def _extract_department_name(entry: dict) -> str:
    meta = entry.get("meta") or entry.get("metadata") or {}
    return (
        entry.get("departamento")
        or entry.get("dep")
        or entry.get("department")
        or meta.get("department")
        or "DESCONOCIDO"
    )


def _extract_candidates(entry: dict) -> Dict[str, int]:
    if isinstance(entry.get("resultados"), dict):
        return {str(key): _safe_int(value) for key, value in entry["resultados"].items()}
    for key in ("candidatos", "candidates", "votos"):
        candidates = entry.get(key)
        if isinstance(candidates, list):
            output: Dict[str, int] = {}
            for candidate in candidates:
                if not isinstance(candidate, dict):
                    continue
                candidate_id = (
                    candidate.get("candidate_id")
                    or candidate.get("id")
                    or candidate.get("nombre")
                    or candidate.get("name")
                    or candidate.get("candidato")
                )
                name = candidate.get("name") or candidate.get("nombre") or candidate_id
                votes = candidate.get("votes") or candidate.get("votos")
                if candidate_id is None and name is None:
                    continue
                key_id = str(candidate_id or name)
                output[key_id] = _safe_int(votes)
            return output
    return {}


def check_consistencia_agregada(data: dict) -> dict:
    """
    Compara la suma de votos por candidato en departamentos vs el nivel nacional.
    Compare the sum of candidate votes across departments versus national totals.

    Args:
        data (dict): Datos electorales parseados (nacional + departamentos)

    Returns:
        dict: Resultado estandarizado de la regla
    """
    rule_key = "consistencia_agregada"
    config = _load_rules_config()
    rule_config = _get_rule_config(config, rule_key)

    default_tolerance = 0.0  # TODO: agregar este umbral a rules.yaml / command_center
    tolerance = float(rule_config.get("tolerance", default_tolerance))

    national_data = (
        data.get("nacional")
        or data.get("national")
        or data.get("NACIONAL")
        or data.get("nivel_nacional")
        or {}
    )
    national_candidates = _extract_candidates(national_data)

    department_sums: Dict[str, int] = {}
    departments = list(_extract_departments(data))
    for department in departments:
        candidate_votes = _extract_candidates(department)
        for candidate_id, votes in candidate_votes.items():
            department_sums[candidate_id] = department_sums.get(candidate_id, 0) + votes

    differences: Dict[str, dict] = {}
    mismatches = 0
    max_diff = 0.0
    for candidate_id, national_votes in national_candidates.items():
        department_total = department_sums.get(candidate_id, 0)
        diff = department_total - national_votes
        differences[candidate_id] = {
            "department_sum": department_total,
            "national": national_votes,
            "difference": diff,
        }
        if abs(diff) > tolerance:
            mismatches += 1
            max_diff = max(max_diff, abs(diff))

    passed = mismatches == 0
    alert = not passed
    default_message = (
        "Diferencias detectadas entre la suma departamental y el total nacional."
    )  # TODO: agregar mensaje a rules.yaml / command_center
    message = str(rule_config.get("message") or default_message)
    severity = str(
        rule_config.get("severity", "warning" if alert else "info")
    ).lower()

    details = {
        "tolerance": tolerance,
        "departments_checked": len(departments),
        "mismatches": mismatches,
        "differences": differences,
        "departments": [_extract_department_name(dep) for dep in departments],
    }

    score = float(max_diff) if differences else None

    return {
        "rule_key": rule_key,
        "passed": passed,
        "alert": alert,
        "severity": severity,
        "score": score,
        "details": details,
        "message": message,
    }
