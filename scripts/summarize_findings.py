"""Genera un resumen textual de alertas detectadas.

Generate a textual summary of detected alerts.
"""

import json
from pathlib import Path

alerts_payload = json.loads(Path("analysis/alerts.json").read_text())

summary_lines: list[str] = []

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

Path("reports/summary.txt").write_text("\n".join(summary_lines), encoding="utf-8")
