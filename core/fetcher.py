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
