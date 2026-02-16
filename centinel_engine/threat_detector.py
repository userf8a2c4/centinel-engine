"""Passive threat detection and legal quiescence controls for Centinel Engine.

ES: Este módulo implementa detección pasiva y pausa inteligente (quiescence)
para reducir presión sobre fuentes públicas cuando hay señales de riesgo.
EN: This module implements passive detection and smart quiescence pauses to
reduce pressure on public sources when risk signals are detected.
"""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from random import randint
from typing import Any

from centinel_engine.vital_signs import check_vital_signs

logger = logging.getLogger(__name__)

THREAT_NONE = "none"
THREAT_RATE_LIMIT = "rate_limit"
THREAT_SERVER_ERROR = "server_error"
THREAT_SUSPICIOUS_HEADER = "suspicious_header"


class ThreatDetector:
    """ES: Detector pasivo de amenazas para scraping ético y resiliente.

    EN: Passive threat detector for ethical and resilient scraping.
    """

    def __init__(self, config: dict):
        """ES: Inicializa umbrales y controles desde configuración.

        EN: Initialize thresholds and controls from configuration.
        """
        self.config = config or {}
        self.rate_limit_threshold = int(self.config.get("rate_limit_threshold", 3))
        self.server_error_threshold = int(self.config.get("server_error_threshold", 4))

    def detect_threats(self, recent_responses: list[dict]) -> str:
        """ES: Detecta amenazas pasivas observando respuestas recientes.

        EN: Detect passive threats by inspecting recent responses.

        Input shape / Estructura esperada:
        - status_code: int
        - response_time: float
        - headers: dict
        - error: str | None
        """
        if not recent_responses:
            return THREAT_NONE

        # ES: Solo análisis pasivo de telemetría; no evasión activa.
        # EN: Passive telemetry analysis only; no active evasion.
        rate_limited_count = 0
        server_error_count = 0

        for response in recent_responses:
            status_code = int(response.get("status_code", 0) or 0)
            headers = response.get("headers", {}) or {}
            headers_text = " ".join(f"{k}:{v}" for k, v in headers.items()).lower()

            if status_code in {403, 429}:
                rate_limited_count += 1
            if 500 <= status_code <= 599:
                server_error_count += 1

            # ES: Señales de bloqueo/CDN; no se intenta bypass.
            # EN: Blocking/CDN signals; no bypass attempt is made.
            if "cloudflare" in headers_text or "blocked" in headers_text:
                return THREAT_SUSPICIOUS_HEADER

        if rate_limited_count > self.rate_limit_threshold:
            return THREAT_RATE_LIMIT
        if server_error_count > self.server_error_threshold:
            return THREAT_SERVER_ERROR

        return THREAT_NONE

    def get_quiescence_duration(self, threat_level: str) -> int:
        """ES: Retorna pausa recomendada en segundos por nivel de amenaza.

        EN: Return recommended pause duration in seconds by threat level.
        """
        if threat_level == THREAT_RATE_LIMIT:
            # ES: ventana aleatoria para aliviar presión y evitar patrones rígidos.
            # EN: random window to reduce pressure and avoid rigid patterns.
            return randint(900, 1800)
        if threat_level == THREAT_SERVER_ERROR:
            return int(self.config.get("server_error_quiescence_seconds", 3600))
        if threat_level == THREAT_SUSPICIOUS_HEADER:
            return int(self.config.get("suspicious_header_quiescence_seconds", 2700))
        return 0


def send_silent_alert(metrics: dict[str, Any], threat: str, config: dict[str, Any] | None = None) -> None:
    """ES: Envía alerta silenciosa (logs + email opcional con placeholder seguro).

    EN: Send silent alert (logs + optional email with safe placeholder).
    """
    config = config or {}
    logger.warning("silent_alert threat=%s metrics=%s", threat, metrics)

    email_config = config.get("silent_email", {})
    if not email_config.get("enabled", False):
        return

    smtp_host = email_config.get("smtp_host")
    sender = email_config.get("from")
    recipient = email_config.get("to")

    # ES: Placeholder seguro: solo envío si hay credenciales explícitas.
    # EN: Safe placeholder: only sends if explicit credentials exist.
    if not (smtp_host and sender and recipient):
        logger.info("silent_email_skipped_missing_secure_config")
        return

    message = EmailMessage()
    message["Subject"] = "[Centinel] Silent Threat Alert"
    message["From"] = sender
    message["To"] = recipient
    message.set_content(
        "Threat detected in passive monitoring.\\n"
        "No bypass/spoofing actions were taken.\\n"
        f"threat={threat}\\nmetrics={metrics}\\n"
    )

    try:
        with smtplib.SMTP(smtp_host, int(email_config.get("smtp_port", 587)), timeout=10) as smtp:
            if email_config.get("starttls", True):
                smtp.starttls()
            username = email_config.get("username")
            password = email_config.get("password")
            if username and password:
                smtp.login(username, password)
            smtp.send_message(message)
    except Exception as exc:  # pragma: no cover - defensive logging path
        logger.error("silent_email_failed error=%s", exc)


def evaluate_resilience_mode(
    *,
    metrics: dict[str, Any],
    recent_responses: list[dict[str, Any]],
    config: dict[str, Any],
) -> dict[str, Any]:
    """ES: Combina signos vitales + detector de amenazas para el modo operativo.

    EN: Combine vital signs + threat detector to derive operating mode.
    """
    vital_result = check_vital_signs(metrics=metrics, config=config)
    threat_detector = ThreatDetector(config=config)
    threat = threat_detector.detect_threats(recent_responses)

    mode = vital_result.get("mode", "normal")
    delay_seconds = int(vital_result.get("delay_seconds", 0))

    # ES: Si hay amenaza, escalamos a estado crítico/quiescence de forma legal.
    # EN: If threat exists, we escalate to legal critical/quiescence state.
    if threat in {THREAT_RATE_LIMIT, THREAT_SERVER_ERROR, THREAT_SUSPICIOUS_HEADER}:
        if threat in {THREAT_SERVER_ERROR, THREAT_SUSPICIOUS_HEADER}:
            mode = "critical"
        else:
            mode = "elevated" if mode != "critical" else mode

        delay_seconds = max(delay_seconds, threat_detector.get_quiescence_duration(threat))
        send_silent_alert(metrics=metrics, threat=threat, config=config)

    return {
        "mode": mode,
        "delay_seconds": delay_seconds,
        "threat": threat,
        "vital_signs": vital_result,
        # ES: Cumplimiento explícito de límites éticos y legales.
        # EN: Explicit compliance with ethical and legal limits.
        "compliance": {
            "fixed_user_agent_pool_only": True,
            "dynamic_ua_mutation": False,
            "spoofing": False,
            "robots_txt_respected": True,
        },
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    sample_config = {
        "cpu_warn": 75,
        "cpu_critical": 90,
        "silent_email": {"enabled": False},
    }
    sample_metrics = {
        "cpu_percent": 42,
        "error_rate": 0.02,
    }
    sample_recent_responses = [
        {"status_code": 200, "response_time": 0.21, "headers": {"Server": "nginx"}, "error": None},
        {"status_code": 429, "response_time": 0.44, "headers": {"Server": "CNE"}, "error": "too many"},
        {"status_code": 429, "response_time": 0.45, "headers": {"Server": "CNE"}, "error": "too many"},
        {"status_code": 403, "response_time": 0.33, "headers": {"Server": "CNE"}, "error": "forbidden"},
        {"status_code": 429, "response_time": 0.51, "headers": {"Server": "CNE"}, "error": "too many"},
    ]

    result = evaluate_resilience_mode(
        metrics=sample_metrics,
        recent_responses=sample_recent_responses,
        config=sample_config,
    )
    logger.info("resilience_evaluation=%s", result)
