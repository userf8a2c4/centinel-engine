"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `src/monitoring/telegram_alert.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - _collect_system_metrics
  - _collect_network_context
  - _format_uptime
  - send_security_alert
  - send_shutdown_alert
  - send_dos_detection_alert
  - _count_integrity_entries

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `src/monitoring/telegram_alert.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - _collect_system_metrics
  - _collect_network_context
  - _format_uptime
  - send_security_alert
  - send_shutdown_alert
  - send_dos_detection_alert
  - _count_integrity_entries

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
"""

# Telegram Alert Module
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

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("centinel.telegram_alert")

# ---------------------------------------------------------------------------
# Metric collection helpers (Helpers de recolección de métricas)
# ---------------------------------------------------------------------------


def _collect_system_metrics() -> dict[str, Any]:
    """Collect current system metrics for inclusion in alerts.
    (Recolectar métricas actuales del sistema para incluir en alertas.)

    Returns an empty dict if psutil is not installed, so alerts never fail
    due to a missing optional dependency.
    (Retorna dict vacío si psutil no está instalado, para que las alertas
    nunca fallen por una dependencia opcional faltante.)
    """
    try:
        import psutil
    except ImportError:
        return {}
    return {
        "cpu_percent": psutil.cpu_percent(interval=0.5),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage("/").percent,
        "open_files": len(psutil.Process().open_files()),
        "threads": psutil.Process().num_threads(),
    }


def _collect_network_context(ip: str | None = None) -> dict[str, Any]:
    """Build network forensic context for an alert.
    (Construir contexto forense de red para una alerta.)
    """
    ctx: dict[str, Any] = {}
    if ip:
        ctx["source_ip"] = ip
        # Mark private/internal IPs for Zero Trust auditing
        # (Marcar IPs privadas/internas para auditoría Zero Trust)
        try:
            import ipaddress

            addr = ipaddress.ip_address(ip)
            ctx["ip_is_private"] = addr.is_private
            ctx["ip_version"] = addr.version
        except ValueError:
            ctx["ip_parse_error"] = True
    return ctx


# ---------------------------------------------------------------------------
# Alert formatters (Formateadores de alertas)
# ---------------------------------------------------------------------------

_SECURITY_TEMPLATE = """🛡 CENTINEL SECURITY EVENT
━━━━━━━━━━━━━━━━━━━━━━
Event: {event}
Time: {timestamp}
{details}
━━━━━━━━━━━━━━━━━━━━━━
System: CPU={cpu}% MEM={mem}% DISK={disk}%
{extra}"""

_SHUTDOWN_TEMPLATE = """⚠️ CENTINEL SHUTDOWN
━━━━━━━━━━━━━━━━━━━━━━
Reason: {reason}
Time: {timestamp}
Uptime: {uptime}
{details}
━━━━━━━━━━━━━━━━━━━━━━
Final metrics: CPU={cpu}% MEM={mem}%
Hash chain entries: {chain_entries}"""


def _format_uptime(seconds: float) -> str:
    """Format seconds into human-readable uptime string.
    (Formatear segundos en string legible de uptime.)
    """
    hours, rem = divmod(int(seconds), 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours}h {minutes}m {secs}s"


# ---------------------------------------------------------------------------
# Public API (API pública)
# ---------------------------------------------------------------------------


def send_security_alert(
    event: str,
    *,
    ip: str | None = None,
    path: str | None = None,
    detail: str = "",
    extra_context: dict[str, Any] | None = None,
) -> bool:
    """Send an obsessively detailed security alert via Telegram.
    (Enviar alerta de seguridad obsesivamente detallada vía Telegram.)

    Includes system metrics, IP forensics, and any extra context.
    Returns True if the alert was dispatched (not necessarily delivered).
    (Incluye métricas del sistema, forense de IP, y contexto extra.
    Retorna True si la alerta fue despachada — no necesariamente entregada.)
    """
    try:
        from monitoring.alerts import dispatch_alert
    except ImportError:
        logger.warning("security_alert_skipped reason=alerts_module_unavailable")
        return False

    metrics = _collect_system_metrics()
    network = _collect_network_context(ip)

    detail_lines = []
    if ip:
        detail_lines.append(f"IP: {ip} (private={network.get('ip_is_private', '?')})")
    if path:
        detail_lines.append(f"Path: {path}")
    if detail:
        detail_lines.append(f"Detail: {detail}")

    message = _SECURITY_TEMPLATE.format(
        event=event,
        timestamp=datetime.now(timezone.utc).isoformat(),
        details="\n".join(detail_lines) if detail_lines else "No additional details",
        cpu=metrics.get("cpu_percent", "?"),
        mem=metrics.get("memory_percent", "?"),
        disk=metrics.get("disk_percent", "?"),
        extra=json.dumps(extra_context, ensure_ascii=False) if extra_context else "",
    )

    context = {
        "event_type": "security",
        "event": event,
        **network,
        **metrics,
        **(extra_context or {}),
    }
    return dispatch_alert("CRITICAL", message, context=context)


def send_shutdown_alert(
    reason: str = "unknown",
    uptime_seconds: float = 0,
    extra_context: dict[str, Any] | None = None,
) -> bool:
    """Send a detailed shutdown alert with final system metrics.
    (Enviar alerta detallada de apagado con métricas finales del sistema.)

    Includes integrity chain entry count so observers can verify
    no entries were lost during the shutdown.
    (Incluye conteo de entradas de cadena de integridad para que
    observadores puedan verificar que no se perdieron entradas.)
    """
    try:
        from monitoring.alerts import dispatch_alert
    except ImportError:
        logger.warning("shutdown_alert_skipped reason=alerts_module_unavailable")
        return False

    metrics = _collect_system_metrics()
    chain_entries = _count_integrity_entries()

    detail_lines = []
    if extra_context:
        for k, v in extra_context.items():
            detail_lines.append(f"{k}: {v}")

    message = _SHUTDOWN_TEMPLATE.format(
        reason=reason,
        timestamp=datetime.now(timezone.utc).isoformat(),
        uptime=_format_uptime(uptime_seconds),
        details="\n".join(detail_lines) if detail_lines else "Clean shutdown",
        cpu=metrics.get("cpu_percent", "?"),
        mem=metrics.get("memory_percent", "?"),
        chain_entries=chain_entries,
    )

    context = {
        "event_type": "shutdown",
        "reason": reason,
        "uptime_seconds": uptime_seconds,
        "chain_entries": chain_entries,
        **metrics,
        **(extra_context or {}),
    }
    return dispatch_alert("CRITICAL", message, context=context)


def send_dos_detection_alert(
    *,
    cpu: float | None = None,
    memory: float | None = None,
    request_rate: float | None = None,
    top_ips: list[str] | None = None,
) -> bool:
    """Send alert when DoS-like conditions are detected.
    (Enviar alerta cuando se detectan condiciones tipo DoS.)

    Includes the top offending IPs and resource metrics so operators
    can take immediate action.
    (Incluye las IPs más ofensivas y métricas de recursos para que
    los operadores puedan tomar acción inmediata.)
    """
    context = {
        "event_type": "dos_detection",
        "cpu": cpu,
        "memory": memory,
        "request_rate": request_rate,
        "top_ips": top_ips or [],
    }
    return send_security_alert(
        "dos_conditions_detected",
        detail=f"CPU={cpu}% MEM={memory}% rate={request_rate} req/min top_ips={top_ips}",
        extra_context=context,
    )


# ---------------------------------------------------------------------------
# Helpers (Funciones auxiliares)
# ---------------------------------------------------------------------------


def _count_integrity_entries() -> int:
    """Count entries in the integrity log for verification reporting.
    (Contar entradas en el log de integridad para reporteo de verificación.)
    """
    integrity_path = Path("logs/integrity.jsonl")
    if not integrity_path.exists():
        return 0
    try:
        return sum(1 for line in integrity_path.read_text(encoding="utf-8").splitlines() if line.strip())
    except OSError:
        return 0
