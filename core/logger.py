"""Core logging bridge for suspicious events.

Puente de logging central para eventos sospechosos.
"""

from __future__ import annotations

from typing import Any

from core.attack_logger import AttackForensicsLogbook

_ATTACK_LOGBOOK: AttackForensicsLogbook | None = None


def register_attack_logbook(logbook: AttackForensicsLogbook | None) -> None:
    """Register global attack logbook instance.

    Registra instancia global de bitácora de ataques.
    """
    global _ATTACK_LOGBOOK
    _ATTACK_LOGBOOK = logbook


def log_suspicious_event(event: dict[str, Any]) -> None:
    """Forward suspicious event metadata to forensics logbook.

    Reenvía metadatos sospechosos a la bitácora forense.
    """
    if not _ATTACK_LOGBOOK:
        return
    _ATTACK_LOGBOOK.log_http_request(
        ip=str(event.get("ip", "0.0.0.0")),
        method=str(event.get("method", "GET")),
        route=str(event.get("route", "/unknown")),
        headers=dict(event.get("headers", {})),
        content_length=int(event.get("content_length", 0)),
    )
