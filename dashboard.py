# Dashboard Module
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

"""Streamlit entrypoint for the C.E.N.T.I.N.E.L. dashboard."""

from __future__ import annotations

import runpy

if __name__ == "__main__":
    runpy.run_path("dashboard/streamlit_app.py", run_name="__main__")
