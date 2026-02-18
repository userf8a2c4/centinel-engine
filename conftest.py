"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `conftest.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - block_network

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `conftest.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - block_network

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
"""

# Conftest Module
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

from pathlib import Path
import socket
import sys
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parent
PARENT_ROOT = REPO_ROOT.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(PARENT_ROOT) in sys.path:
    sys.path.remove(str(PARENT_ROOT))


@pytest.fixture(autouse=True)
def block_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Impide conexiones de red reales en tests.

    English:
        Prevents real network connections in tests.
    """

    def guarded_connect(*args: Any, **kwargs: Any) -> None:
        """Español: Función guarded_connect del módulo conftest.py.

        English: Function guarded_connect defined in conftest.py.
        """
        raise RuntimeError("Network access is disabled during tests.")

    def guarded_create_connection(*args: Any, **kwargs: Any) -> None:
        """Español: Función guarded_create_connection del módulo conftest.py.

        English: Function guarded_create_connection defined in conftest.py.
        """
        raise RuntimeError("Network access is disabled during tests.")

    monkeypatch.setattr(socket.socket, "connect", guarded_connect, raising=True)
    monkeypatch.setattr(socket, "create_connection", guarded_create_connection, raising=True)
