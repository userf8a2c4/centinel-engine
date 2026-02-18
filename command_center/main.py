"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `command_center/main.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - _build_pipeline_args
  - run_command_center
  - main
  - bloque_main

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `command_center/main.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - _build_pipeline_args
  - run_command_center
  - main
  - bloque_main

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
"""

# Main Module
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
