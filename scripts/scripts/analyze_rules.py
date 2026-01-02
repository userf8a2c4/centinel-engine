import json
from pathlib import Path

INPUT_DIR = Path("normalized")
OUTPUT_DIR = Path("analysis")
OUTPUT_DIR.mkdir(exist_ok=True)

files = sorted(INPUT_DIR.glob("*.normalized.json"))

alerts = []

for prev, curr in zip(files, files[1:]):
    a = json.loads(prev.read_text())
    b = json.loads(curr.read_text())

    event = {
        "from": a["timestamp_utc"],
        "to": b["timestamp_utc"],
        "alerts": []
    }

    # Regla 1: votos negativos
    for partido, votos_b in b["resultados"].items():
        votos_a = a["resultados"].get(partido, 0)
        if votos_b < votos_a:
            event["alerts"].append({
                "rule": "NEGATIVE_VOTES",
                "partido": partido,
                "delta": votos_b - votos_a
            })

    # Regla 2: votos crecen sin actas
    if b["actas"]["divulgadas"] == a["actas"]["divulgadas"]:
        if b["votos_totales"]["validos"] > a["votos_totales"]["validos"]:
            event["alerts"].append({
                "rule": "VOTES_WITHOUT_ACTAS",
                "delta_votos": b["votos_totales"]["validos"] - a["votos_totales"]["validos"]
            })

    if event["alerts"]:
        alerts.append(event)

(Path("analysis/alerts.json")
 .write_text(json.dumps(alerts, indent=2), encoding="utf-8"))
