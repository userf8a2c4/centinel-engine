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
CHI2_FORMULA = "chi2 = sum((O-E)^2 / E)"


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


def _is_benford_chi2_alert(alert: dict) -> bool:
    """Verifica si la alerta es de Benford o chi2.

    English:
        Check whether the alert is Benford or chi2-related.
    """
    description = alert.get("description") or alert.get("descripcion") or ""
    rule_name = alert.get("rule") or ""
    combined = f"{rule_name} {description}".lower()
    keywords = ("benford", "chi2", "chi-square", "chi cuadrado", "chi-cuadrado")
    return any(keyword in combined for keyword in keywords)


def _build_math_explanation() -> str:
    """Devuelve explicación matemática para chi-cuadrado.

    /** Explicación con fórmula. / Explanation with formula. */

    English:
        Return the chi-square mathematical explanation.
    """
    return CHI2_FORMULA


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
            if (
                p_value is not None
                and p_value < 0.01
                and _is_benford_chi2_alert(triggered_rule)
            ):
                critical_p_alerts.append(
                    {
                        "rule": triggered_rule.get("rule"),
                        "p_value": p_value,
                        "description": description,
                        "math": _build_math_explanation(),
                    }
                )

if critical_p_alerts:
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    alert_log = logs_dir / "alerts.log"
    now = datetime.now(timezone.utc).isoformat()
    with alert_log.open("a", encoding="utf-8") as handle:
        for entry in critical_p_alerts:
            # /** Envía alerta crítica. / Sends critical alert.
            #  chi2 = sum((O-E)^2 / E). */
            handle.write(
                (
                    f"[{now}] ALERTA CRITICA p<0.01 "
                    "tipo=benford/chi2 "
                    f"rule={entry.get('rule')} p_value={entry.get('p_value'):.4f} "
                    f"explicacion={entry.get('math')} "
                    f"detalle={entry.get('description') or ''}\n"
                )
            )

Path("reports/summary.txt").write_text("\n".join(summary_lines), encoding="utf-8")
