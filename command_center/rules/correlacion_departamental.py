"""Regla de correlación departamental usando porcentajes por candidato.

Department-level correlation rule using candidate vote shares.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import numpy as np
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


def _extract_candidate_votes(entry: dict) -> Dict[str, int]:
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


def _build_share_vector(candidate_ids: List[str], votes: Dict[str, int]) -> Optional[List[float]]:
    total_votes = sum(votes.values())
    if total_votes <= 0:
        return None
    return [votes.get(candidate_id, 0) / total_votes for candidate_id in candidate_ids]


def check_correlacion_departamental(data: dict) -> dict:
    """
    Calcula matriz Pearson de % votos por candidato y alerta por baja correlación.
    Compute Pearson matrix for candidate vote shares and alert on low correlation.

    Args:
        data (dict): Datos electorales parseados (nacional + departamentos)

    Returns:
        dict: Resultado estandarizado de la regla
    """
    rule_key = "correlacion_departamental"
    config = _load_rules_config()
    rule_config = _get_rule_config(config, rule_key)

    default_min_expected = 0.7  # TODO: agregar este umbral a rules.yaml / command_center
    min_expected = float(rule_config.get("min_expected", default_min_expected))

    departments = list(_extract_departments(data))
    candidate_ids: List[str] = []
    votes_by_department: Dict[str, Dict[str, int]] = {}
    for department in departments:
        dept_name = _extract_department_name(department)
        votes = _extract_candidate_votes(department)
        if not votes:
            continue
        votes_by_department[dept_name] = votes
        for candidate_id in votes.keys():
            if candidate_id not in candidate_ids:
                candidate_ids.append(candidate_id)

    share_vectors = []
    department_names = []
    for dept_name, votes in votes_by_department.items():
        vector = _build_share_vector(candidate_ids, votes)
        if vector is None:
            continue
        share_vectors.append(vector)
        department_names.append(dept_name)

    if len(share_vectors) < 2 or len(candidate_ids) < 2:
        return {
            "rule_key": rule_key,
            "passed": True,
            "alert": False,
            "severity": "info",
            "score": None,
            "details": {
                "reason": "insufficient_data",
                "departments_used": len(share_vectors),
                "candidates": len(candidate_ids),
            },
            "message": str(rule_config.get("message") or "No hay datos suficientes para correlación departamental."),
        }

    matrix = np.corrcoef(np.array(share_vectors))
    min_corr = 1.0
    worst_pair = None
    for idx_i in range(len(department_names)):
        for idx_j in range(idx_i + 1, len(department_names)):
            corr_value = float(matrix[idx_i, idx_j])
            if corr_value < min_corr:
                min_corr = corr_value
                worst_pair = (department_names[idx_i], department_names[idx_j])

    alert = min_corr < min_expected
    passed = not alert
    severity = str(rule_config.get("severity", "warning" if alert else "info")).lower()
    default_message = (
        "Correlación baja detectada entre departamentos."  # TODO: agregar mensaje a rules.yaml / command_center
    )
    message = str(rule_config.get("message") or default_message)

    details = {
        "min_expected": min_expected,
        "min_correlation": min_corr,
        "worst_pair": worst_pair,
        "departments_used": department_names,
        "candidates": candidate_ids,
        "correlation_matrix": matrix.tolist(),
    }

    return {
        "rule_key": rule_key,
        "passed": passed,
        "alert": alert,
        "severity": severity,
        "score": float(min_corr),
        "details": details,
        "message": message,
    }
