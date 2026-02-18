# Sitecustomize Module
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

"""Ajusta sys.path para priorizar el paquete local de Centinel.

English:
    Adjusts sys.path to prioritize the local Centinel package.
"""

from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent
SRC_ROOT = REPO_ROOT / "src"
PARENT_ROOT = REPO_ROOT.parent
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
if str(REPO_ROOT) in sys.path:
    sys.path.remove(str(REPO_ROOT))
if str(PARENT_ROOT) in sys.path:
    sys.path.remove(str(PARENT_ROOT))
