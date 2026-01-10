import json
from pathlib import Path

alerts = json.loads(Path("analysis/alerts.json").read_text())

lines = []

if not alerts:
    lines.append("No se detectaron eventos atípicos en los datos públicos analizados.")
else:
    for e in alerts:
        lines.append(f"Evento atípico detectado entre {e['from']} y {e['to']} UTC.")
        for a in e["alerts"]:
            lines.append(f"- Regla activada: {a['rule']}")

Path("reports/summary.txt").write_text("\n".join(lines), encoding="utf-8")
