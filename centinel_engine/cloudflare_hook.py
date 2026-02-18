"""Cloudflare protection extension hook (disabled by default).

Provides a no-op integration point for future Cloudflare edge protections.

Provee un punto de integracion no operativo para protecciones futuras de borde
con Cloudflare.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def apply_cloudflare_protection(config: dict[str, Any]) -> None:
    """Apply Cloudflare protection when enabled (stub currently disabled).

    English:
        This extension point intentionally does nothing at runtime today.
        It preserves API compatibility for future security hardening.

    Español:
        Este punto de extension intencionalmente no hace nada hoy en runtime.
        Preserva compatibilidad de API para endurecimiento futuro de seguridad.

    Args:
        config: Runtime configuration dictionary. Uses ``ENABLE_CLOUDFLARE``
            (default: ``False``) to decide whether the integration is active.

    Returns:
        ``None`` always.
    """
    # Keep default disabled for safety / Mantener desactivado por seguridad.
    enabled: bool = bool(config.get("ENABLE_CLOUDFLARE", False))
    if not enabled:
        logger.info("Cloudflare integration disabled")
        return

    # Future implementation placeholder / Placeholder para implementacion futura.
    logger.info("Cloudflare integration stub active but not implemented yet")
