"""Command center CLI entry point with dry-run support. (Punto de entrada CLI del command center con soporte dry-run.)"""

from __future__ import annotations

import argparse
import logging
import sys
from typing import List

from scripts import run_pipeline
from centinel.utils.config_loader import load_config


def _build_pipeline_args(parsed_args: argparse.Namespace) -> List[str]:
    """Build arguments for the pipeline runner. (Construye argumentos para el ejecutor del pipeline.)"""
    args: List[str] = []
    if parsed_args.once:
        args.append("--once")
    if parsed_args.run_now:
        args.append("--run-now")
    return args


def run_command_center(*, dry_run: bool, once: bool, run_now: bool) -> None:
    """Run the command center with optional dry-run. (Ejecuta el command center con dry-run opcional.)"""
    logger = logging.getLogger(__name__)
    load_config()

    if dry_run:
        logger.info("Dry-run activo: no se ejecuta polling real (Dry-run active: no real polling executed).")
        return

    # Ejecuta el pipeline real cuando dry-run está desactivado (Run the real pipeline when dry-run is disabled).
    pipeline_args = _build_pipeline_args(argparse.Namespace(once=once, run_now=run_now))
    original_argv = sys.argv[:]
    sys.argv = ["run_pipeline"] + pipeline_args
    try:
        run_pipeline.main()
    finally:
        sys.argv = original_argv


def main() -> None:
    """CLI for the command center. (CLI para el command center.)"""
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="C.E.N.T.I.N.E.L. Command Center CLI")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simula ejecución sin polling real (Simulate execution without real polling).",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Ejecuta una sola vez y sale (Run once and exit).",
    )
    parser.add_argument(
        "--run-now",
        action="store_true",
        help="Ejecuta inmediatamente antes del scheduler (Run immediately before scheduler).",
    )
    args = parser.parse_args()
    run_command_center(dry_run=args.dry_run, once=args.once, run_now=args.run_now)


if __name__ == "__main__":
    main()
