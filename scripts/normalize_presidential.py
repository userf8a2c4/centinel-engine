import json
import re
from pathlib import Path
from datetime import datetime

INPUT_DIR = Path("data")
OUTPUT_DIR = Path("normalized")
OUTPUT_DIR.mkdir(exist_ok=True)

def to_int(x):
    return int(re.sub(r"[^\d]", "", x))

def to_float(x):
    return float(x.replace(",", "."))

for file in sorted(INPUT_DIR.glob("*.json")):
    raw = json.loads(file.read_text(encoding="utf-8"))

    timestamp = file.stem.split(" ", 1)[-1]
    timestamp = timestamp.replace("_", ":").replace(" ", "T") + "Z"

    normalized = {
        "timestamp_utc": timestamp,
        "nivel": "presidencial",
        "departamento": "NACIONAL",
        "resultados": {},
        "actas": {},
        "votos_totales": {},
    }

    for r in raw["resultados"]:
        normalized["resultados"][r["partido"]] = to_int(r["votos"])

    est = raw["estadisticas"]

    normalized["actas"] = {
        "totales": to_int(est["totalizacion_actas"]["actas_totales"]),
        "divulgadas": to_int(est["totalizacion_actas"]["actas_divulgadas"]),
        "correctas": to_int(est["estado_actas_divulgadas"]["actas_correctas"]),
        "inconsistentes": to_int(est["estado_actas_divulgadas"]["actas_inconsistentes"]),
    }

    normalized["votos_totales"] = {
        "validos": to_int(est["distribucion_votos"]["validos"]),
        "nulos": to_int(est["distribucion_votos"]["nulos"]),
        "blancos": to_int(est["distribucion_votos"]["blancos"]),
    }

    out = OUTPUT_DIR / f"{file.stem}.normalized.json"
    out.write_text(json.dumps(normalized, indent=2), encoding="utf-8")
