"""Genera un resumen textual de alertas detectadas.

Generate a textual summary of detected alerts.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

alerts_payload = json.loads(Path("analysis/alerts.json").read_text())

summary_lines: list[str] = []
critical_p_alerts: list[dict] = []


def _extract_p_value(alert: dict) -> float | None:
    """Extrae p_value desde el payload de alertas (si existe).

    English:
        Extract p_value from the alerts payload (when present).
    """
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

if not alerts_payload:
    summary_lines.append(
        "No se detectaron eventos atípicos en los datos públicos analizados."
    )
else:
    for alert_window in alerts_payload:
        summary_lines.append(
            "Evento atípico detectado entre "
            f"{alert_window['from']} y {alert_window['to']} UTC."
        )
        for triggered_rule in alert_window["alerts"]:
            description = triggered_rule.get("description") or triggered_rule.get(
                "descripcion"
            )
            if description:
                summary_lines.append(f"- {description}")
            else:
                summary_lines.append(
                    f"- Regla activada: {triggered_rule['rule']}"
                )
            p_value = _extract_p_value(triggered_rule)
            if p_value is not None and p_value < 0.01:
                critical_p_alerts.append(
                    {
                        "rule": triggered_rule.get("rule"),
                        "p_value": p_value,
                        "description": description,
                    }
                )

if critical_p_alerts:
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    alert_log = logs_dir / "alerts.log"
    now = datetime.now(timezone.utc).isoformat()
    with alert_log.open("a", encoding="utf-8") as handle:
        for entry in critical_p_alerts:
            # /** Alerta crítica p<0.01. / Critical alert p<0.01. */
            handle.write(
                (
                    f"[{now}] ALERTA CRITICA p<0.01 "
                    f"rule={entry.get('rule')} p_value={entry.get('p_value'):.4f} "
                    f"detalle={entry.get('description') or ''}\n"
                )
            )

Path("reports/summary.txt").write_text("\n".join(summary_lines), encoding="utf-8")
