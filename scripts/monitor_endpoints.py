"""English: Standalone proactive endpoint monitor for daemon or cron execution.
Español: Monitor proactivo standalone de endpoints para ejecución como daemon o cron.

# English: Crontab example (every 30 minutes) with UTC-safe logging.
# Español: Ejemplo de crontab (cada 30 minutos) con logging seguro en UTC.
# */30 * * * * cd /workspace/centinel-engine && /usr/bin/python3 scripts/monitor_endpoints.py --once >> logs/monitor_endpoints.log 2>&1
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# English: Ensure repository root is importable when running as a standalone script.
# Español: Garantiza que la raíz del repositorio sea importable al ejecutar como script independiente.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from centinel_engine.cne_endpoint_healer import CNEEndpointHealer


def build_parser() -> argparse.ArgumentParser:
    """English: Build CLI parser for one-shot and daemon scanning.
    Español: Construye parser CLI para escaneo one-shot y modo daemon.
    """

    parser = argparse.ArgumentParser(description="Proactive monitor for CNE endpoint healing.")
    parser.add_argument("--once", action="store_true", help="Run a single proactive scan and exit.")
    parser.add_argument(
        "--interval",
        type=int,
        choices=(30, 60),
        default=30,
        help="Proactive scan interval in minutes for loop mode (30 or 60).",
    )
    parser.add_argument(
        "--adaptive-animal-mode",
        action="store_true",
        help="Enable Honey-Badger adaptive cadence using recommended interval from healer metadata.",
    )
    return parser


def run_proactive_scan(healer: CNEEndpointHealer) -> dict[str, object]:
    """English: Run one proactive scan and log forensic metadata.
    Español: Ejecuta un escaneo proactivo y registra metadatos forenses.
    """

    logging.info("PROACTIVE SCAN STARTED | utc=%s", datetime.now(timezone.utc).isoformat())
    result = healer.heal_proactive()

    scan_hash = hashlib.sha256(json.dumps(result, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
    logging.info("PROACTIVE SCAN RESULT | hash=%s | payload=%s", scan_hash, json.dumps(result, ensure_ascii=False))
    return result


def run_loop(interval_minutes: int, adaptive_animal_mode: bool = False) -> None:
    """English: Run proactive monitor forever with fixed sleep suitable for daemon operation.
    Español: Ejecuta monitor proactivo en bucle infinito con sleep fijo apto para daemon.
    """

    healer = CNEEndpointHealer("config/prod/endpoints.yaml")
    while True:
        result = run_proactive_scan(healer)
        effective_interval = interval_minutes
        if adaptive_animal_mode:
            # English: In hostile environments, healer can suggest a shorter survival cadence.
            # Español: En entornos hostiles, el healer puede sugerir una cadencia de supervivencia más corta.
            effective_interval = int(result.get("recommended_interval_minutes", interval_minutes))
        logging.info("PROACTIVE SCAN SLEEP | seconds=%s | adaptive=%s", effective_interval * 60, adaptive_animal_mode)
        time.sleep(effective_interval * 60)


def main() -> int:
    """English: Entrypoint for cron-safe one-shot mode and daemon loop mode.
    Español: Punto de entrada para modo one-shot seguro en cron y modo bucle daemon.
    """

    logging.Formatter.converter = time.gmtime
    logging.basicConfig(level=logging.INFO, format="%(asctime)sZ | %(levelname)s | %(message)s")
    args = build_parser().parse_args()

    if args.once:
        healer = CNEEndpointHealer("config/prod/endpoints.yaml")
        run_proactive_scan(healer)
        return 0

    run_loop(args.interval, adaptive_animal_mode=args.adaptive_animal_mode)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
