# Verify Hashes Module
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

"""Offline hashchain verification script. (Script de verificación offline de hashchain.)"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .hasher import verify_hashchain_from_snapshots


def _build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser. (Construye el parser de CLI.)"""
    parser = argparse.ArgumentParser(description="Verify Centinel snapshot hashchain")
    parser.add_argument(
        "--dir",
        dest="snapshot_dir",
        required=True,
        help="Snapshot directory root to verify",
    )
    return parser


def main() -> None:
    """Run the offline verification CLI. (Ejecuta el CLI de verificación offline.)"""
    parser = _build_parser()
    args = parser.parse_args()

    snapshot_root = Path(args.snapshot_dir)
    result = verify_hashchain_from_snapshots(snapshot_root)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if not result.get("valid", False):
        sys.exit(1)


if __name__ == "__main__":
    main()
