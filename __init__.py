#   Init   Module
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

"""Paquete raíz para la distribución local de Centinel.

English:
    Root package shim for the local Centinel distribution.
"""

from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_LOCAL_PACKAGE = _ROOT / "centinel"
__path__ = [str(_LOCAL_PACKAGE), str(_ROOT)]
