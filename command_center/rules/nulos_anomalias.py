"""Regla de anomalías en votos nulos con chequeo de regresión básica.

Null-vote anomaly rule with basic regression check.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple

import yaml
from scipy.stats import linregress


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


def _extract_vote_breakdown(entry: dict) -> Tuple[Optional[int], Optional[int]]:
    totals = entry.get("totals") or {}
    votos_totales = entry.get("votos_totales") or {}
    null_votes = _safe_int(
        totals.get("null_votes")
        or totals.get("nulos")
        or votos_totales.get("nulos")
        or votos_totales.get("null_votes")
        or entry.get("votos_nulos"),
        default=0,
    )
    total_votes = _safe_int(
        totals.get("total_votes")
        or totals.get("total")
        or votos_totales.get("total")
        or votos_totales.get("total_votes")
        or entry.get("total_votes")
        or entry.get("total_votos")
        or entry.get("votos_emitidos"),
        default=0,
    )
    if total_votes <= 0:
        return None, None
    return null_votes, total_votes


def _extract_registered_voters(entry: dict) -> Optional[int]:
    padron_value = entry.get("padron") or entry.get("padron_total")
    padron_dict = padron_value if isinstance(padron_value, dict) else {}
    return _safe_int(
        entry.get("registered_voters")
        or entry.get("electores")
        or (padron_value if not isinstance(padron_value, dict) else None)
        or padron_dict.get("total")
        or padron_dict.get("registered_voters"),
        default=0,
    )


def _calculate_turnout(entry: dict) -> Optional[float]:
    total_votes_tuple = _extract_vote_breakdown(entry)
    if total_votes_tuple[1] is None:
        return None
    total_votes = total_votes_tuple[1]
    registered_voters = _extract_registered_voters(entry)
    if not registered_voters or registered_voters <= 0:
        return None
    return float(total_votes) / float(registered_voters)


def check_nulos_anomalias(data: dict) -> dict:
    """
    Detecta porcentaje de nulos alto y residuos de regresión vs turnout.
    Detect high null-vote percentage and regression residuals vs turnout.

    Args:
        data (dict): Datos electorales parseados (nacional + departamentos)

    Returns:
        dict: Resultado estandarizado de la regla
    """
    rule_key = "nulos_anomalias"
    config = _load_rules_config()
    rule_config = _get_rule_config(config, rule_key)

    default_max_percentage = 0.08  # TODO: agregar este umbral a rules.yaml / command_center
    default_residual_threshold = 0.05  # TODO: agregar este umbral a rules.yaml / command_center
    max_percentage = float(rule_config.get("max_percentage", default_max_percentage))
    residual_threshold = float(
        rule_config.get("residual_threshold", default_residual_threshold)
    )

    department_alerts: Dict[str, dict] = {}
    regression_points = []

    for department in _extract_departments(data):
        null_votes, total_votes = _extract_vote_breakdown(department)
        if null_votes is None or total_votes is None:
            continue
        null_percentage = null_votes / total_votes if total_votes else 0.0
        dept_name = _extract_department_name(department)
        turnout = _calculate_turnout(department)
        if turnout is not None:
            regression_points.append((turnout, null_percentage, dept_name))
        if null_percentage > max_percentage:
            department_alerts[dept_name] = {
                "null_percentage": null_percentage,
                "null_votes": null_votes,
                "total_votes": total_votes,
            }

    regression_alerts = {}
    if len(regression_points) >= 3:
        xs = [point[0] for point in regression_points]
        ys = [point[1] for point in regression_points]
        regression = linregress(xs, ys)
        for turnout, null_percentage, dept_name in regression_points:
            predicted = regression.intercept + regression.slope * turnout
            residual = null_percentage - predicted
            if abs(residual) > residual_threshold:
                regression_alerts[dept_name] = {
                    "turnout": turnout,
                    "null_percentage": null_percentage,
                    "predicted": predicted,
                    "residual": residual,
                }

    alert = bool(department_alerts or regression_alerts)
    passed = not alert
    severity = str(rule_config.get("severity", "warning" if alert else "info")).lower()
    default_message = (
        "Porcentaje de votos nulos elevado o desviación atípica vs turnout."
    )  # TODO: agregar mensaje a rules.yaml / command_center
    message = str(rule_config.get("message") or default_message)

    details = {
        "max_percentage": max_percentage,
        "residual_threshold": residual_threshold,
        "null_percentage_alerts": department_alerts,
        "regression_alerts": regression_alerts,
        "regression_samples": len(regression_points),
    }

    max_null_percentage = 0.0
    if department_alerts:
        max_null_percentage = max(
            alert_data["null_percentage"] for alert_data in department_alerts.values()
        )
    max_residual = 0.0
    if regression_alerts:
        max_residual = max(
            abs(alert_data["residual"]) for alert_data in regression_alerts.values()
        )
    score = max(max_null_percentage, max_residual) if alert else None

    return {
        "rule_key": rule_key,
        "passed": passed,
        "alert": alert,
        "severity": severity,
        "score": score,
        "details": details,
        "message": message,
    }
