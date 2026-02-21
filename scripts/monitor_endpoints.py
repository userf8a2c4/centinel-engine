"""English: Cron/daemon monitor for CNE endpoint auto-discovery self-healing.
Español: Monitor para cron/daemon de autodescubrimiento y autocuración de endpoints CNE.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

# English: Ensure repository root is importable when running as a standalone script.
# Español: Garantiza que la raíz del repositorio sea importable al ejecutar como script independiente.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from centinel_engine.cne_endpoint_healer import run_endpoint_healer


def build_parser() -> argparse.ArgumentParser:
    """English: Build CLI parser for single-run or loop execution modes.
    Español: Construye parser CLI para modo de ejecución única o en bucle.
    """

    parser = argparse.ArgumentParser(description="Monitor and self-heal CNE endpoints every 30 minutes.")
    parser.add_argument("--loop", action="store_true", help="Run forever sleeping 1800s between checks.")
    parser.add_argument("--interval", type=int, default=1800, help="Seconds between checks in loop mode.")
    return parser


def monitor_once() -> list[dict[str, object]]:
    """English: Execute one monitoring pass and emit concise logs.
    Español: Ejecuta una pasada de monitoreo y emite logs concisos.
    """

    results = run_endpoint_healer()
    changed = any(bool(item.get("changed")) for item in results)
    if changed:
        logging.info("🩺 Endpoint changes detected and healed: %s", json.dumps(results, ensure_ascii=False))
    else:
        logging.info("✅ No endpoint changes detected")
    return results


def main() -> int:
    """English: Script entrypoint supporting cron mode and daemon loop mode.
    Español: Punto de entrada con soporte para modo cron y modo daemon en bucle.
    """

    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    args = build_parser().parse_args()

    if not args.loop:
        monitor_once()
        return 0

    while True:
        monitor_once()
        logging.info("⏳ Sleeping %s seconds before next endpoint check", args.interval)
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
