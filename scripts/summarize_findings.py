# Summarize Findings Module
# AUTO-DOC-INDEX
#
# ES: Índice rápido
#   1) Propósito del módulo
#   2) Componentes principales
#   3) Puntos de extensión
#
# EN: Quick index
#   1) Module purpose
#   2) Main components
#   3) Extension points
#
# Secciones / Sections:
#   - Configuración / Configuration
#   - Lógica principal / Core logic
#   - Integraciones / Integrations

"""Genera un resumen textual de alertas detectadas.

Generate a textual summary of detected alerts.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from centinel_engine.config_loader import load_config

logger = logging.getLogger("centinel.summarize")


def _configure_logging() -> None:
    """/** Configura logging básico para alertas. / Configure basic logging for alerts. **"""
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    alert_log = logs_dir / "alerts.log"
    handler = logging.FileHandler(alert_log, encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    handler.setFormatter(formatter)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        logger.addHandler(handler)


def _load_rules_thresholds() -> dict[str, Any]:
    """/** Carga umbrales desde config/prod/rules.yaml. / Load thresholds from config/prod/rules.yaml. **"""
    try:
        # English: centralized path via config loader. / Español: ruta centralizada vía config loader.
        payload = load_config("rules.yaml", env="prod")
        return payload if isinstance(payload, dict) else {}
    except ValueError as exc:
        logger.warning("rules_yaml_invalid error=%s", exc)
        return {}


def _extract_p_value(alert: dict) -> float | None:
    """/** Extrae p_value desde el payload de alertas. / Extract p_value from alerts payload. **"""
    for key in ("p_value", "pvalue", "p"):
        if key in alert:
            try:
                return float(alert[key])
            except (TypeError, ValueError):
                return None
    value = alert.get("value")
    if isinstance(value, dict):
        for key in ("p_value", "pvalue", "p"):
            if key in value:
                try:
                    return float(value[key])
                except (TypeError, ValueError):
                    return None
    description = alert.get("description") or alert.get("descripcion") or ""
    match = re.search(r"p_value=([0-9.]+)", description)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None


def _extract_hash(alert: dict) -> str:
    """/** Extrae hash relacionado con alerta. / Extract hash related to alert. **"""
    for key in ("hash", "snapshot_hash", "chained_hash", "content_hash"):
        value = alert.get(key)
        if value:
            return str(value)
    return "unknown"


def _build_summary(alerts_payload: list[dict]) -> tuple[list[str], list[dict]]:
    """/** Construye resumen y alertas críticas. / Build summary and critical alerts. **"""
    summary_lines: list[str] = []
    critical_p_alerts: list[dict] = []
    rules_thresholds = _load_rules_thresholds()
    critical_threshold = float(rules_thresholds.get("chi2_p_critical", 0.01))

    if not alerts_payload:
        summary_lines.append("No se detectaron eventos atípicos en los datos públicos analizados.")
        return summary_lines, critical_p_alerts

    for alert_window in alerts_payload:
        summary_lines.append("Evento atípico detectado entre " f"{alert_window['from']} y {alert_window['to']} UTC.")
        for triggered_rule in alert_window.get("alerts", []):
            description = triggered_rule.get("description") or triggered_rule.get("descripcion")
            if description:
                summary_lines.append(f"- {description}")
            else:
                summary_lines.append(f"- Regla activada: {triggered_rule.get('rule')}")
            p_value = _extract_p_value(triggered_rule)
            if p_value is not None and p_value < critical_threshold:
                critical_p_alerts.append(
                    {
                        "rule": triggered_rule.get("rule"),
                        "p_value": p_value,
                        "description": description,
                        "hash": _extract_hash(triggered_rule),
                    }
                )

    return summary_lines, critical_p_alerts


def _log_critical_alerts(critical_p_alerts: list[dict]) -> None:
    """/** Registra alertas críticas en logs/alerts.log. / Log critical alerts in logs/alerts.log. **"""
    if not critical_p_alerts:
        return
    _configure_logging()
    now = datetime.now(timezone.utc).isoformat()
    for entry in critical_p_alerts:
        explanation = "p_value < umbral crítico; chi-cuadrado evalúa Σ((O - E)^2 / E)."
        logger.critical(
            "ALERTA CRITICA p<umbral timestamp=%s rule=%s p_value=%.4f hash=%s detalle=%s explicacion=%s",
            now,
            entry.get("rule"),
            entry.get("p_value"),
            entry.get("hash"),
            entry.get("description") or "",
            explanation,
        )


def summarize_findings() -> None:
    """/** Genera summary.txt y registra alertas críticas. / Generate summary.txt and log critical alerts. **"""
    alerts_path = Path("analysis/alerts.json")
    alerts_payload: list[dict] = []
    try:
        if alerts_path.exists():
            alerts_payload = json.loads(alerts_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        logger.error("alerts_json_invalid error=%s", exc)
        alerts_payload = []

    summary_lines, critical_p_alerts = _build_summary(alerts_payload)
    _log_critical_alerts(critical_p_alerts)

    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    (reports_dir / "summary.txt").write_text("\n".join(summary_lines), encoding="utf-8")


if __name__ == "__main__":
    # Ejemplo de uso / Usage example.
    summarize_findings()
