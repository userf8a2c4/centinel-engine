# Fetcher Module
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

"""Fetcher security helpers.

Ayudantes de seguridad para fetcher.
"""

from __future__ import annotations

from pathlib import Path

from core.advanced_security import load_manager


def build_rotating_request_profile(
    config_path: Path = Path("command_center/advanced_security_config.yaml"),
) -> tuple[dict[str, str], dict[str, str] | None]:
    """Return rotating headers and optional proxies.

    Retorna headers rotativos y proxies opcionales.
    """
    manager = load_manager(config_path)
    return manager.get_request_profile()
