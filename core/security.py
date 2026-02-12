"""Defensive dead man's switch for hostile runtime conditions.

Interruptor defensivo de hombre muerto para condiciones hostiles en ejecución.
"""

from __future__ import annotations

import json
import logging
import os
import random
import signal
import smtplib
import socket
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.message import EmailMessage
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib import request

import yaml

try:
    import psutil
except Exception:  # noqa: BLE001
    class _PsutilFallback:
        CONN_LISTEN = "LISTEN"
        CONN_ESTABLISHED = "ESTABLISHED"

        @staticmethod
        def cpu_percent(interval: float = 0.1) -> float:
            return 0.0

        @staticmethod
        def virtual_memory():
            return type("_VMem", (), {"percent": 0.0})()

        @staticmethod
        def net_connections(kind: str = "inet"):
            return []

    psutil = _PsutilFallback()


class DefensiveShutdown(RuntimeError):
    """Raised when defensive mode requests controlled shutdown.

    Se lanza cuando el modo defensivo solicita apagado controlado.
    """


@dataclass
class SecurityConfig:
    """Runtime configuration for defensive mode.

    Configuración en tiempo de ejecución para modo defensivo.
    """

    cpu_threshold_percent: float = 90.0
    cpu_sustain_seconds: int = 60
    memory_threshold_percent: float = 85.0
    http_errors_limit: int = 10
    http_window_seconds: int = 300
    error_log_flood_limit: int = 50
    error_log_window_seconds: int = 60
    expected_ports: list[int] = field(default_factory=lambda: [443])
    suspicious_connections_limit: int = 2
    monitor_connections: bool = False
    safe_state_dir: str = "data/safe_state"
    defensive_flag_file: str = "data/safe_state/defensive_shutdown.flag"
    max_restart_attempts: int = 5
    cooldown_min_minutes: int = 10
    cooldown_max_minutes: int = 60
    admin_email: str = "example@domain.com"
    webhook_url: str = ""
    smtp: dict[str, Any] = field(default_factory=dict)
    honeypot_enabled: bool = False
    honeypot_host: str = "127.0.0.1"
    honeypot_port: int = 8081

    @classmethod
    def from_yaml(cls, path: Path) -> "SecurityConfig":
        """Load config from YAML with safe defaults.

        Carga configuración YAML con valores seguros por defecto.
        """
        if not path.exists():
            return cls()
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            return cls()
        if not isinstance(raw, dict):
            return cls()
        smtp = raw.get("smtp_settings", {}) if isinstance(raw.get("smtp_settings", {}), dict) else {}
        return cls(
            cpu_threshold_percent=float(raw.get("cpu_threshold_percent", 90)),
            cpu_sustain_seconds=int(raw.get("cpu_sustain_seconds", 60)),
            memory_threshold_percent=float(raw.get("memory_threshold_percent", 85)),
            http_errors_limit=int(raw.get("http_errors_limit", 10)),
            http_window_seconds=int(raw.get("http_window_seconds", 300)),
            error_log_flood_limit=int(raw.get("error_log_flood_limit", 50)),
            error_log_window_seconds=int(raw.get("error_log_window_seconds", 60)),
            expected_ports=list(raw.get("expected_ports", [443])),
            suspicious_connections_limit=int(raw.get("suspicious_connections_limit", 2)),
            monitor_connections=bool(raw.get("monitor_connections", False)),
            safe_state_dir=str(raw.get("safe_state_dir", "data/safe_state")),
            defensive_flag_file=str(raw.get("defensive_flag_file", "data/safe_state/defensive_shutdown.flag")),
            max_restart_attempts=int(raw.get("max_restart_attempts", 5)),
            cooldown_min_minutes=int(raw.get("cooldown_min_minutes", 10)),
            cooldown_max_minutes=int(raw.get("cooldown_max_minutes", 60)),
            admin_email=str(raw.get("admin_email", "example@domain.com")),
            webhook_url=str(raw.get("webhook_url", "")),
            smtp=smtp,
            honeypot_enabled=bool(raw.get("honeypot", {}).get("enabled", False)),
            honeypot_host=str(raw.get("honeypot", {}).get("host", "127.0.0.1")),
            honeypot_port=int(raw.get("honeypot", {}).get("port", 8081)),
        )


class AttackLogger:
    """Structured attack event logger using JSONL.

    Bitácora estructurada de ataques usando JSONL.
    """

    def __init__(self, path: Path = Path("logs/attack_log.jsonl")) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._per_ip_hits: dict[str, deque[float]] = defaultdict(deque)

    def log_request(self, ip: str, method: str, route: str, headers: dict[str, str]) -> dict[str, Any]:
        """Log request metadata and simple threat patterns.

        Registra metadatos de solicitud y patrones simples de amenaza.
        """
        now = time.time()
        dq = self._per_ip_hits[ip]
        dq.append(now)
        while dq and now - dq[0] > 60:
            dq.popleft()

        ua = headers.get("User-Agent", "")
        patterns: list[str] = []
        lowered = ua.lower()
        if any(token in lowered for token in ("sqlmap", "nmap", "nikto", "masscan", "zap")):
            patterns.append("scanner_ua")
        if "tor" in lowered or headers.get("Via", "").lower().find("tor") >= 0:
            patterns.append("possible_tor")
        if len(dq) > 20:
            patterns.append("flood_1min")

        payload = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "ip": ip,
            "method": method,
            "route": route,
            "headers": headers,
            "user_agent": ua,
            "frequency_1min": len(dq),
            "patterns": patterns,
        }
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
        return payload


class _HoneypotHandler(BaseHTTPRequestHandler):
    """Simple honeypot handler that logs and always returns 404.

    Handler honeypot simple que registra y siempre devuelve 404.
    """

    attack_logger: AttackLogger | None = None

    def do_GET(self) -> None:  # noqa: N802
        self._capture_and_respond()

    def do_POST(self) -> None:  # noqa: N802
        self._capture_and_respond()

    def _capture_and_respond(self) -> None:
        if self.path in {"/debug", "/admin"} and self.attack_logger:
            headers = {k: v for k, v in self.headers.items()}
            self.attack_logger.log_request(
                ip=self.client_address[0],
                method=self.command,
                route=self.path,
                headers=headers,
            )
        self.send_response(404)
        self.end_headers()

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return


class DefensiveSecurityManager:
    """Monitors host signals and triggers defensive shutdown.

    Monitorea señales hostiles y activa apagado defensivo.
    """

    def __init__(self, config: SecurityConfig, logger: logging.Logger | None = None) -> None:
        self.config = config
        self.logger = logger or logging.getLogger("centinel.security")
        self.http_error_times: deque[float] = deque()
        self.error_log_times: deque[float] = deque()
        self.pending_triggers: deque[str] = deque()
        self._cpu_high_since: float | None = None
        self._stop_event = threading.Event()
        self._honeypot_server: ThreadingHTTPServer | None = None
        self._honeypot_thread: threading.Thread | None = None

    def register_signal_handlers(self) -> None:
        """Register SIGTERM/SIGINT to convert into graceful defensive trigger.

        Registra SIGTERM/SIGINT para convertirlos en trigger defensivo.
        """

        def _handler(signum: int, _frame: Any) -> None:
            self.pending_triggers.append(f"signal_{signal.Signals(signum).name}")

        signal.signal(signal.SIGINT, _handler)
        signal.signal(signal.SIGTERM, _handler)

    def start_honeypot(self, attack_logger: AttackLogger | None = None) -> None:
        """Start optional honeypot endpoint if enabled.

        Inicia endpoint honeypot opcional si está habilitado.
        """
        if not self.config.honeypot_enabled:
            return
        _HoneypotHandler.attack_logger = attack_logger or AttackLogger()
        server = ThreadingHTTPServer((self.config.honeypot_host, self.config.honeypot_port), _HoneypotHandler)
        self._honeypot_server = server
        self._honeypot_thread = threading.Thread(target=server.serve_forever, daemon=True)
        self._honeypot_thread.start()

    def stop_honeypot(self) -> None:
        """Stop honeypot server.

        Detiene el servidor honeypot.
        """
        if self._honeypot_server:
            self._honeypot_server.shutdown()
            self._honeypot_server.server_close()

    def record_http_error(self, status_code: int | None = None, *, timeout: bool = False) -> None:
        """Track HTTP failures relevant for hostile trigger logic.

        Registra fallas HTTP relevantes para lógica de trigger hostil.
        """
        if timeout or status_code in {429, 503}:
            self.http_error_times.append(time.time())

    def record_log_error(self) -> None:
        """Track error log entry timestamps.

        Registra marcas de tiempo de errores en bitácora.
        """
        self.error_log_times.append(time.time())

    def _trim(self, series: deque[float], window_seconds: int) -> None:
        now = time.time()
        while series and now - series[0] > window_seconds:
            series.popleft()

    def detect_hostile_conditions(self) -> list[str]:
        """Return list of active defensive triggers.

        Retorna lista de triggers defensivos activos.
        """
        triggers: list[str] = []
        now = time.time()

        cpu = psutil.cpu_percent(interval=0.1)
        if cpu > self.config.cpu_threshold_percent:
            if self._cpu_high_since is None:
                self._cpu_high_since = now
            elif now - self._cpu_high_since >= self.config.cpu_sustain_seconds:
                triggers.append(f"cpu_high:{cpu:.1f}")
        else:
            self._cpu_high_since = None

        mem = psutil.virtual_memory().percent
        if mem > self.config.memory_threshold_percent:
            triggers.append(f"memory_high:{mem:.1f}")

        self._trim(self.http_error_times, self.config.http_window_seconds)
        if len(self.http_error_times) > self.config.http_errors_limit:
            triggers.append("http_errors_flood")

        self._trim(self.error_log_times, self.config.error_log_window_seconds)
        if len(self.error_log_times) > self.config.error_log_flood_limit:
            triggers.append("error_log_flood")

        if self.config.monitor_connections:
            suspicious = 0
            for conn in psutil.net_connections(kind="inet"):
                laddr = getattr(conn, "laddr", ())
                status = getattr(conn, "status", "")
                if status != psutil.CONN_LISTEN or not laddr:
                    continue
                port = int(laddr.port)
                if port not in self.config.expected_ports:
                    suspicious += 1
            if suspicious >= self.config.suspicious_connections_limit:
                triggers.append(f"suspicious_ports:{suspicious}")

        while self.pending_triggers:
            triggers.append(self.pending_triggers.popleft())

        return triggers

    def _health_snapshot(self, triggers: list[str]) -> dict[str, Any]:
        return {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "pid": os.getpid(),
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "open_connections": len(psutil.net_connections(kind="inet")),
            "triggers": triggers,
        }

    def activate_defensive_mode(
        self,
        triggers: list[str],
        *,
        snapshot_state: dict[str, Any] | None = None,
        close_callbacks: list[Callable[[], None]] | None = None,
    ) -> None:
        """Persist defensive state and raise controlled shutdown exception.

        Persiste estado defensivo y lanza excepción de apagado controlado.
        """
        safe_dir = Path(self.config.safe_state_dir)
        safe_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        dump_dir = safe_dir / stamp
        dump_dir.mkdir(parents=True, exist_ok=True)

        health = self._health_snapshot(triggers)
        (dump_dir / "health.json").write_text(json.dumps(health, indent=2, ensure_ascii=False), encoding="utf-8")
        if snapshot_state:
            (dump_dir / "state_snapshot.json").write_text(
                json.dumps(snapshot_state, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        (dump_dir / "recent_triggers.json").write_text(json.dumps(triggers, indent=2), encoding="utf-8")

        flag_path = Path(self.config.defensive_flag_file)
        flag_path.parent.mkdir(parents=True, exist_ok=True)
        flag_path.write_text(
            json.dumps({"timestamp_utc": health["timestamp_utc"], "triggers": triggers, "state_dir": str(dump_dir)}),
            encoding="utf-8",
        )

        for callback in close_callbacks or []:
            try:
                callback()
            except Exception as exc:  # noqa: BLE001
                self.logger.warning("defensive_close_callback_failed error=%s", exc)

        self.stop_honeypot()
        self.logger.critical("defensive_mode_activated triggers=%s state_dir=%s", triggers, dump_dir)
        raise DefensiveShutdown(";".join(triggers))


def send_admin_alert(
    *,
    config: SecurityConfig,
    triggers: list[str],
    recent_logs: list[str],
    state_path: str,
) -> None:
    """Send final admin alert via email and/or webhook.

    Envía alerta final de administrador por email y/o webhook.
    """
    body = (
        "Sistema en hibernación defensiva; verifique host y reinicie manualmente.\n"
        f"Triggers: {', '.join(triggers)}\n"
        f"Safe state: {state_path}\n"
        "Recent logs:\n"
        + "\n".join(recent_logs[-20:])
    )

    smtp_server = os.getenv("SMTP_SERVER", config.smtp.get("server", ""))
    smtp_port = int(os.getenv("SMTP_PORT", str(config.smtp.get("port", 587))))
    smtp_user = os.getenv("SMTP_USER", config.smtp.get("user", ""))
    smtp_pass = os.getenv("SMTP_PASSWORD", config.smtp.get("password", ""))
    sender = os.getenv("SMTP_FROM", smtp_user)
    recipient = os.getenv("ADMIN_EMAIL", config.admin_email)

    if smtp_server and sender and recipient:
        msg = EmailMessage()
        msg["Subject"] = "[Centinel] Defensive hibernation requires manual intervention"
        msg["From"] = sender
        msg["To"] = recipient
        msg.set_content(body)
        with smtplib.SMTP(smtp_server, smtp_port, timeout=15) as smtp:
            smtp.starttls()
            if smtp_user and smtp_pass:
                smtp.login(smtp_user, smtp_pass)
            smtp.send_message(msg)

    webhook = os.getenv("DEFENSIVE_WEBHOOK_URL", config.webhook_url)
    if webhook:
        payload = json.dumps({"text": body}).encode("utf-8")
        req = request.Request(webhook, data=payload, headers={"Content-Type": "application/json"})
        with request.urlopen(req, timeout=10) as resp:
            if resp.status >= 400:
                raise RuntimeError(f"webhook_failed:{resp.status}")


def random_cooldown_seconds(min_minutes: int, max_minutes: int, multiplier: float = 1.0) -> int:
    """Compute randomized cooldown with optional exponential multiplier.

    Calcula cooldown aleatorio con multiplicador exponencial opcional.
    """
    base = random.uniform(min_minutes * 60, max_minutes * 60)
    return int(base * multiplier)
