# Normalize Presidential Module
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

"""Normaliza snapshots presidenciales a un formato consistente.

Normalize presidential snapshots into a consistent format.
"""

import json
import logging
import re
from pathlib import Path

from centinel.paths import iter_all_snapshots
from scripts.logging_utils import configure_logging, log_event

INPUT_DIR = Path("data")
OUTPUT_DIR = Path("normalized")
OUTPUT_DIR.mkdir(exist_ok=True)
logger = configure_logging(__name__)


def to_int(x):
    """Convierte un string con separadores a entero.

    Convert a string with separators to an integer.
    """
    return int(re.sub(r"[^\d]", "", x))


def to_float(x):
    """Convierte un string con coma decimal a float.

    Convert a string with a decimal comma to float.
    """
    return float(x.replace(",", "."))


max_files = 19
files = iter_all_snapshots(data_root=INPUT_DIR)
for index, file in enumerate(files[:max_files]):
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
    log_event(
        logger,
        logging.INFO,
        "normalized_snapshot_written",
        snapshot=file.stem,
        sequence=index + 1,
    )

if len(files) > max_files:
    # Seguridad: Evita exposición de datos sensibles / Security: Avoid exposure of sensitive data.
    log_event(
        logger,
        logging.WARNING,
        "snapshot_limit_enforced",
        processed=max_files,
    )
