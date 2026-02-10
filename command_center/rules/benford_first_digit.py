"""Regla de Benford (primer dígito) para conteos de votos.

Benford first-digit rule for vote counts.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Iterable, List, Optional

import numpy as np
import yaml
from scipy.stats import chisquare


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


def _extract_candidates(entry: dict) -> List[int]:
    votes: List[int] = []
    if isinstance(entry.get("resultados"), dict):
        for value in entry["resultados"].values():
            votes.append(_safe_int(value))
        return votes
    for key in ("candidatos", "candidates", "votos"):
        candidates = entry.get(key)
        if isinstance(candidates, list):
            for candidate in candidates:
                if not isinstance(candidate, dict):
                    continue
                votes.append(_safe_int(candidate.get("votes") or candidate.get("votos")))
            return votes
    return votes


def _first_digit(value: int) -> Optional[int]:
    if value <= 0:
        return None
    return int(str(value)[0])


def _collect_vote_counts(data: dict) -> List[int]:
    counts: List[int] = []
    national_data = (
        data.get("nacional") or data.get("national") or data.get("NACIONAL") or data.get("nivel_nacional") or {}
    )
    counts.extend(_extract_candidates(national_data))
    for department in _extract_departments(data):
        counts.extend(_extract_candidates(department))
    return counts


def check_benford_first_digit(data: dict) -> dict:
    """
    Calcula distribución de primer dígito y chi-cuadrado de Benford.
    Compute first-digit distribution and Benford chi-square test.

    Args:
        data (dict): Datos electorales parseados (nacional + departamentos)

    Returns:
        dict: Resultado estandarizado de la regla
    """
    rule_key = "benford_first_digit"
    config = _load_rules_config()
    rule_config = _get_rule_config(config, rule_key)

    default_p_threshold = 0.05  # TODO: agregar este umbral a rules.yaml / command_center
    default_min_samples = 50  # TODO: agregar este umbral a rules.yaml / command_center
    p_threshold = float(rule_config.get("p_threshold", default_p_threshold))
    min_samples = int(rule_config.get("min_samples", default_min_samples))

    vote_counts = _collect_vote_counts(data)
    digits = [digit for digit in (_first_digit(value) for value in vote_counts) if digit is not None]

    if len(digits) < min_samples:
        return {
            "rule_key": rule_key,
            "passed": True,
            "alert": False,
            "severity": "info",
            "score": None,
            "details": {
                "reason": "insufficient_samples",
                "min_samples": min_samples,
                "observed_samples": len(digits),
            },
            "message": str(rule_config.get("message") or "No hay suficientes muestras para Benford."),
        }

    observed_counts = np.array([digits.count(digit) for digit in range(1, 10)])
    total = observed_counts.sum()
    expected_probs = np.array([math.log10(1 + 1 / digit) for digit in range(1, 10)])
    expected_counts = expected_probs * total
    chi_result = chisquare(observed_counts, f_exp=expected_counts)

    alert = chi_result.pvalue < p_threshold
    passed = not alert
    severity = str(rule_config.get("severity", "critical" if alert else "info")).lower()
    default_message = (
        "Distribución del primer dígito desvía de Benford."  # TODO: agregar mensaje a rules.yaml / command_center
    )
    message = str(rule_config.get("message") or default_message)

    details = {
        "p_value": float(chi_result.pvalue),
        "chi2": float(chi_result.statistic),
        "p_threshold": p_threshold,
        "min_samples": min_samples,
        "observed_counts": observed_counts.tolist(),
        "expected_counts": expected_counts.tolist(),
    }

    return {
        "rule_key": rule_key,
        "passed": passed,
        "alert": alert,
        "severity": severity,
        "score": float(chi_result.pvalue),
        "details": details,
        "message": message,
    }
