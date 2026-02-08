"""Regla de turnout con Z-score contra media nacional.

Turnout rule with Z-score against national mean.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import statistics
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


def _extract_total_votes(entry: dict) -> Optional[int]:
    totals = entry.get("totals") or {}
    votos_totales = entry.get("votos_totales") or {}
    return _safe_int(
        totals.get("total_votes")
        or totals.get("total")
        or votos_totales.get("total")
        or votos_totales.get("total_votes")
        or entry.get("total_votes")
        or entry.get("total_votos")
        or entry.get("votos_emitidos"),
        default=0,
    )


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
    total_votes = _extract_total_votes(entry)
    registered_voters = _extract_registered_voters(entry)
    if not total_votes or not registered_voters:
        return None
    if registered_voters <= 0:
        return None
    return float(total_votes) / float(registered_voters)


def check_turnout_zscore(data: dict) -> dict:
    """
    Calcula turnout por departamento y Z-score respecto a la media nacional.
    Compute turnout per department and Z-score versus the national mean.

    Args:
        data (dict): Datos electorales parseados (nacional + departamentos)

    Returns:
        dict: Resultado estandarizado de la regla
    """
    rule_key = "turnout_zscore"
    config = _load_rules_config()
    rule_config = _get_rule_config(config, rule_key)

    default_z_threshold = 2.5  # TODO: agregar este umbral a rules.yaml / command_center
    default_turnout_min = 0.4  # TODO: agregar este umbral a rules.yaml / command_center
    default_turnout_max = (
        0.95  # TODO: agregar este umbral a rules.yaml / command_center
    )
    default_critical_z = 3.5  # TODO: agregar este umbral a rules.yaml / command_center

    z_threshold = float(rule_config.get("z_threshold", default_z_threshold))
    critical_z_threshold = float(
        rule_config.get("critical_z_threshold", default_critical_z)
    )
    turnout_min = float(rule_config.get("turnout_min", default_turnout_min))
    turnout_max = float(rule_config.get("turnout_max", default_turnout_max))

    national_data = (
        data.get("nacional")
        or data.get("national")
        or data.get("NACIONAL")
        or data.get("nivel_nacional")
        or {}
    )
    national_turnout = _calculate_turnout(national_data)

    departments = list(_extract_departments(data))
    dept_turnouts: Dict[str, float] = {}
    for department in departments:
        turnout = _calculate_turnout(department)
        if turnout is None:
            continue
        dept_turnouts[_extract_department_name(department)] = turnout

    turnout_values = list(dept_turnouts.values())
    mean_turnout = national_turnout
    if mean_turnout is None and turnout_values:
        mean_turnout = statistics.mean(turnout_values)

    std_turnout = statistics.pstdev(turnout_values) if len(turnout_values) > 1 else 0.0

    alerts = {}
    max_abs_z = 0.0
    for dept_name, turnout in dept_turnouts.items():
        if std_turnout > 0 and mean_turnout is not None:
            z_score = (turnout - mean_turnout) / std_turnout
        else:
            z_score = 0.0
        max_abs_z = max(max_abs_z, abs(z_score))
        outside_range = turnout < turnout_min or turnout > turnout_max
        z_alert = abs(z_score) > z_threshold
        critical = abs(z_score) > critical_z_threshold
        if outside_range or z_alert:
            alerts[dept_name] = {
                "turnout": turnout,
                "z_score": z_score,
                "outside_range": outside_range,
                "critical": critical,
            }

    alert = bool(alerts)
    passed = not alert

    default_message = "Turnout con Z-score fuera de umbral en uno o más departamentos."  # TODO: agregar mensaje a rules.yaml / command_center
    message = str(rule_config.get("message") or default_message)
    severity = str(
        rule_config.get(
            "severity",
            "critical" if any(a["critical"] for a in alerts.values()) else "warning",
        )
    ).lower()

    details = {
        "national_turnout": mean_turnout,
        "turnout_min": turnout_min,
        "turnout_max": turnout_max,
        "z_threshold": z_threshold,
        "critical_z_threshold": critical_z_threshold,
        "alerts": alerts,
        "departments_checked": len(departments),
        "departments_used": list(dept_turnouts.keys()),
        "std_turnout": std_turnout,
    }

    score = float(max_abs_z) if turnout_values else None

    return {
        "rule_key": rule_key,
        "passed": passed,
        "alert": alert,
        "severity": severity,
        "score": score,
        "details": details,
        "message": message,
    }
