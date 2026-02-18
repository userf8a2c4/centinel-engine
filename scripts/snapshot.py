#!/usr/bin/env python
# Snapshot Module
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

"""Run collection + hash snapshot in one command.

Ejecuta recolección + snapshot de hash en un solo comando.
"""

from scripts.collector import run_collection
from scripts.hash import run_hash_snapshot


def main() -> None:
    """Execute the audit snapshot pipeline.

    Ejecuta el pipeline de snapshot de auditoría.
    """
    run_collection()
    raise SystemExit(run_hash_snapshot())


if __name__ == "__main__":
    main()
