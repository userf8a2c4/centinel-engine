"""Attack forensics logging utilities.

Utilidades de bitácora forense de atacantes.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import queue
import random
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import psutil
import requests
import yaml
from flask import Flask, Request, request
from werkzeug.serving import make_server


@dataclass
class AttackLogConfig:
    """Runtime settings for the attack forensics logbook.

    Configuración de ejecución para la bitácora forense de atacantes.
    """

    enabled: bool = True
    log_path: str = "logs/attack_log.jsonl"
    rotation_interval_seconds: int = 86_400
    max_file_size_mb: int = 10
    retention_days: int = 30
    frequency_window_seconds: int = 60
    sequence_window_size: int = 40
    max_requests_per_ip: int = 20
    brute_force_paths: list[str] = field(default_factory=lambda: ["/admin", "/login", "/wp-login", "/api/internal"])
    suspicious_user_agents: list[str] = field(default_factory=lambda: ["sqlmap", "nmap", "nikto", "masscan", "acunetix"])
    tor_exit_nodes: list[str] = field(default_factory=list)
    expected_listen_ports: list[int] = field(default_factory=lambda: [443])
    external_summary_enabled: bool = False
    external_summary_on_critical_only: bool = True
    external_summary_channel: str = "webhook"
    anonymize_summaries: bool = True
    webhook_url: str = ""
    telegram_chat_id: str = ""
    honeypot_enabled: bool = False
    honeypot_host: str = "127.0.0.1"
    honeypot_port: int = 8080
    honeypot_routes: list[str] = field(default_factory=lambda: ["/debug", "/admin", "/api/internal"])
    monitor_unexpected_connections: bool = True

    @classmethod
    def from_yaml(cls, path: Path) -> "AttackLogConfig":
        """Load YAML config with safe defaults.

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
        external = raw.get("external_summary", {}) if isinstance(raw.get("external_summary"), dict) else {}
        honeypot = raw.get("honeypot", {}) if isinstance(raw.get("honeypot"), dict) else {}
        return cls(
            enabled=bool(raw.get("enabled", True)),
            log_path=str(raw.get("log_path", "logs/attack_log.jsonl")),
            rotation_interval_seconds=int(raw.get("rotation_interval", 86_400)),
            max_file_size_mb=int(raw.get("max_file_size_mb", 10)),
            retention_days=int(raw.get("retention_days", 30)),
            frequency_window_seconds=int(raw.get("frequency_window_seconds", 60)),
            sequence_window_size=int(raw.get("sequence_window_size", 40)),
            max_requests_per_ip=int(raw.get("max_requests_per_ip", 20)),
            brute_force_paths=list(raw.get("brute_force_paths", cls().brute_force_paths)),
            suspicious_user_agents=list(raw.get("suspicious_user_agents", cls().suspicious_user_agents)),
            tor_exit_nodes=list(raw.get("tor_exit_nodes", [])),
            expected_listen_ports=list(raw.get("expected_listen_ports", [443])),
            external_summary_enabled=bool(external.get("enabled", False)),
            external_summary_on_critical_only=bool(external.get("critical_only", True)),
            external_summary_channel=str(external.get("channel", "webhook")),
            anonymize_summaries=bool(external.get("anonymize", True)),
            webhook_url=str(external.get("webhook_url", "")),
            telegram_chat_id=str(external.get("telegram_chat_id", "")),
            honeypot_enabled=bool(honeypot.get("enabled", False)),
            honeypot_host=str(honeypot.get("host", "127.0.0.1")),
            honeypot_port=int(honeypot.get("port", 8080)),
            honeypot_routes=list(honeypot.get("routes", cls().honeypot_routes)),
            monitor_unexpected_connections=bool(raw.get("monitor_unexpected_connections", True)),
        )


class AttackForensicsLogbook:
    """Asynchronous JSONL attack evidence recorder.

    Registrador asíncrono de evidencia de ataques en JSONL.
    """

    def __init__(self, config: AttackLogConfig) -> None:
        self.config = config
        self.path = Path(config.log_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._events: "queue.Queue[dict[str, Any] | None]" = queue.Queue()
        self._writer_stop = threading.Event()
        self._writer_thread: threading.Thread | None = None
        self._last_rotation = time.time()
        self._per_ip_hits: dict[str, deque[float]] = defaultdict(deque)
        self._per_ip_routes: dict[str, deque[str]] = defaultdict(lambda: deque(maxlen=self.config.sequence_window_size))

    def start(self) -> None:
        """Start background writer thread.

        Inicia thread de escritura en segundo plano.
        """
        if self._writer_thread and self._writer_thread.is_alive():
            return
        self._writer_stop.clear()
        self._writer_thread = threading.Thread(target=self._writer_loop, name="attack-log-writer", daemon=True)
        self._writer_thread.start()

    def stop(self) -> None:
        """Stop writer thread gracefully.

        Detiene el thread de escritura de forma segura.
        """
        if self._writer_thread and self._writer_thread.is_alive():
            self._events.put(None)
            self._writer_stop.set()
            self._writer_thread.join(timeout=3)

    def flush(self, timeout: float = 2.0) -> None:
        """Best-effort queue flush helper for tests and shutdown.

        Helper de vaciado de cola para pruebas y apagado.
        """
        end_time = time.time() + timeout
        while (not self._events.empty()) and time.time() < end_time:
            time.sleep(0.01)

    def _writer_loop(self) -> None:
        while not self._writer_stop.is_set():
            payload = self._events.get()
            try:
                if payload is None:
                    return
                self._rotate_if_needed()
                with self.path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
            finally:
                self._events.task_done()

    def _rotate_if_needed(self) -> None:
        now = time.time()
        size_limit = self.config.max_file_size_mb * 1024 * 1024
        should_rotate = False
        if self.path.exists() and self.path.stat().st_size >= size_limit:
            should_rotate = True
        if now - self._last_rotation >= self.config.rotation_interval_seconds and self.path.exists():
            should_rotate = True
        if not should_rotate:
            return

        stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
        rotated = self.path.with_name(f"attack_log-{stamp}.jsonl")
        if rotated.exists():
            rotated = self.path.with_name(f"attack_log-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}.jsonl")
        self.path.rename(rotated)
        gz_path = rotated.with_suffix(rotated.suffix + ".gz")
        with rotated.open("rb") as src, gzip.open(gz_path, "wb") as dst:
            dst.write(src.read())
        rotated.unlink(missing_ok=True)
        self._last_rotation = now
        self._cleanup_old_files()

    def _cleanup_old_files(self) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.config.retention_days)
        for candidate in self.path.parent.glob("attack_log-*.jsonl.gz"):
            modified = datetime.fromtimestamp(candidate.stat().st_mtime, tz=timezone.utc)
            if modified < cutoff:
                candidate.unlink(missing_ok=True)

    def _event_frequency(self, ip: str) -> int:
        now = time.time()
        hits = self._per_ip_hits[ip]
        hits.append(now)
        while hits and now - hits[0] > self.config.frequency_window_seconds:
            hits.popleft()
        return len(hits)

    def _classify(self, route: str, frequency: int, ua: str, headers: dict[str, str], ip: str) -> str:
        route_lower = route.lower()
        ua_lower = ua.lower()
        proxy_chain = headers.get("X-Forwarded-For", "")
        if frequency > self.config.max_requests_per_ip:
            return "flood"
        if route_lower in {p.lower() for p in self.config.brute_force_paths}:
            return "brute"
        if any(token in ua_lower for token in self.config.suspicious_user_agents) or route_lower.count("/") >= 4:
            return "scan"
        if ip in self.config.tor_exit_nodes or proxy_chain.count(",") >= 1:
            return "proxy_suspect"
        return "suspicious"

    def _build_event(self, *, ip: str, method: str, route: str, headers: dict[str, str], content_length: int = 0) -> dict[str, Any]:
        frequency = self._event_frequency(ip)
        routes = self._per_ip_routes[ip]
        routes.append(route)
        ua = headers.get("User-Agent", "")
        classification = self._classify(route=route, frequency=frequency, ua=ua, headers=headers, ip=ip)
        return {
            "timestamp_utc": datetime.utcnow().isoformat(),
            "ip": ip,
            "user_agent": ua,
            "http_method": method,
            "route": route,
            "headers": headers,
            "content_length": int(content_length or 0),
            "frequency_window_seconds": self.config.frequency_window_seconds,
            "frequency_count": frequency,
            "sequence": list(routes),
            "classification": classification,
            "source": "honeypot_or_ingress",
        }

    def log_http_request(self, *, ip: str, method: str, route: str, headers: dict[str, str], content_length: int = 0) -> dict[str, Any]:
        """Register suspicious inbound HTTP metadata.

        Registra metadatos HTTP de entrada sospechosa.
        """
        event = self._build_event(ip=ip, method=method, route=route, headers=headers, content_length=content_length)
        self._events.put(event)
        self._maybe_send_summary(event)
        return event

    def log_connection_snapshot(self) -> None:
        """Inspect listening ports and log unexpected exposures.

        Inspecciona puertos en escucha y registra exposiciones inesperadas.
        """
        if not self.config.monitor_unexpected_connections:
            return
        try:
            unexpected = []
            for conn in psutil.net_connections(kind="inet"):
                if getattr(conn, "status", "") != psutil.CONN_LISTEN:
                    continue
                laddr = getattr(conn, "laddr", None)
                if not laddr:
                    continue
                if int(laddr.port) not in self.config.expected_listen_ports:
                    unexpected.append(int(laddr.port))
            if unexpected:
                event = {
                    "timestamp_utc": datetime.utcnow().isoformat(),
                    "classification": "scan",
                    "source": "psutil",
                    "unexpected_listen_ports": sorted(set(unexpected)),
                    "evidence": "unexpected listening ports detected",
                }
                self._events.put(event)
        except Exception as exc:  # noqa: BLE001
            self._events.put(
                {
                    "timestamp_utc": datetime.utcnow().isoformat(),
                    "classification": "suspicious",
                    "source": "psutil",
                    "error": str(exc),
                }
            )

    def _maybe_send_summary(self, event: dict[str, Any]) -> None:
        if not self.config.external_summary_enabled:
            return
        if self.config.external_summary_on_critical_only and event.get("classification") not in {"flood", "scan"}:
            return
        try:
            summary = self._anonymized_summary(event)
            self._send_summary(summary)
        except Exception:
            # Deliberately silent to avoid blocking election polling.
            # Deliberadamente silencioso para no bloquear el polling electoral.
            return

    def _anonymized_summary(self, event: dict[str, Any]) -> dict[str, Any]:
        ip = str(event.get("ip", "0.0.0.0"))
        safe_ip = self._anonymize_ip(ip) if self.config.anonymize_summaries else ip
        return {
            "event": event.get("classification", "suspicious"),
            "ip": safe_ip,
            "frequency": event.get("frequency_count", 0),
            "window_seconds": event.get("frequency_window_seconds", self.config.frequency_window_seconds),
            "route": event.get("route", ""),
            "timestamp_utc": event.get("timestamp_utc"),
        }

    def _anonymize_ip(self, ip: str) -> str:
        salt = os.getenv("ATTACK_LOG_SALT", "centinel-default-salt")
        digest = hashlib.sha256(f"{salt}:{ip}".encode("utf-8")).hexdigest()
        return f"anon-{digest[:12]}"

    def _send_summary(self, summary: dict[str, Any]) -> None:
        if self.config.external_summary_channel == "telegram":
            token = os.getenv("TELEGRAM_TOKEN", "")
            chat_id = os.getenv("TELEGRAM_CHAT_ID", self.config.telegram_chat_id)
            if token and chat_id:
                requests.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json={"chat_id": chat_id, "text": json.dumps(summary, ensure_ascii=False)},
                    timeout=5,
                )
            return

        endpoint = os.getenv("WEBHOOK_URL", self.config.webhook_url)
        if endpoint:
            requests.post(endpoint, json=summary, timeout=5)


class HoneypotServer:
    """Minimal Flask honeypot, optional and isolated.

    Honeypot Flask mínimo, opcional y aislado.
    """

    def __init__(self, config: AttackLogConfig, logbook: AttackForensicsLogbook) -> None:
        self.config = config
        self.logbook = logbook
        self.app = Flask("centinel_honeypot")
        self._server = None
        self._thread: threading.Thread | None = None
        self._install_routes()

    def _install_routes(self) -> None:
        for route in self.config.honeypot_routes:
            self.app.add_url_rule(route, route, self._handle, methods=["GET", "POST", "PUT", "DELETE", "PATCH"])

    def _extract_headers(self, req: Request) -> dict[str, str]:
        return {key: value for key, value in req.headers.items()}

    def _handle(self) -> tuple[str, int]:
        headers = self._extract_headers(request)
        self.logbook.log_http_request(
            ip=request.remote_addr or "0.0.0.0",
            method=request.method,
            route=request.path,
            headers=headers,
            content_length=int(request.content_length or 0),
        )
        code = random.choice([404, 500])
        return ("Not found", code)

    def start(self) -> None:
        """Start honeypot HTTP server.

        Inicia servidor HTTP del honeypot.
        """
        if not self.config.honeypot_enabled:
            return
        if self._thread and self._thread.is_alive():
            return
        self._server = make_server(self.config.honeypot_host, self.config.honeypot_port, self.app, threaded=True)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop honeypot HTTP server.

        Detiene servidor HTTP del honeypot.
        """
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
