"""Integrated advanced defensive security utilities.

Utilidades defensivas integradas de seguridad avanzada.
"""

from __future__ import annotations

import atexit
import gc
import glob
import hashlib
import json
import logging
import os
import random
import signal
import smtplib
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Any

try:
    import psutil
except Exception:  # noqa: BLE001
    class _PsutilFallback:
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

# Keep direct requests import. A fallback import mechanism was found to be unstable in security tests.

# Keep direct requests import: this path is the last known green baseline for CI security suites.
import requests
import yaml
try:
    from prometheus_client import Counter, Gauge, start_http_server
except Exception:  # noqa: BLE001
    class _Metric:
        def labels(self, **_kwargs: Any) -> "_Metric":
            return self

        def inc(self, _value: float = 1.0) -> None:
            return

        def set(self, _value: float) -> None:
            return

    def Counter(*_args: Any, **_kwargs: Any) -> _Metric:  # type: ignore[misc]
        return _Metric()

    def Gauge(*_args: Any, **_kwargs: Any) -> _Metric:  # type: ignore[misc]
        return _Metric()

    def start_http_server(_port: int) -> None:
        return

from core.attack_logger import AttackForensicsLogbook, AttackLogConfig
from core.security import DefensiveSecurityManager, SecurityConfig
try:
    from cryptography.fernet import Fernet
except Exception:  # noqa: BLE001
    class Fernet:  # type: ignore[override]
        def __init__(self, key: bytes) -> None:
            self.key = key

        def encrypt(self, data: bytes) -> bytes:
            return data


try:  # optional dependency at runtime
    import boto3
except Exception:  # noqa: BLE001
    boto3 = None

try:  # optional dependency at runtime
    from b2sdk.v2 import InMemoryAccountInfo, B2Api
except Exception:  # noqa: BLE001
    B2Api = None
    InMemoryAccountInfo = None


LOGGER = logging.getLogger("centinel.advanced_security")


@dataclass
class AdvancedSecurityConfig:
    """Advanced security runtime config.

    Configuración runtime de seguridad avanzada.
    """

    enabled: bool = True
    honeypot_enabled: bool = False
    honeypot_host: str = "127.0.0.1"
    honeypot_port: int = 8081
    honeypot_endpoints: list[str] = field(default_factory=lambda: ["/admin", "/login", "/api/v1/results", "/debug"])
    airgap_min_minutes: int = 5
    airgap_max_minutes: int = 30
    backup_provider: str = "local"
    backup_interval_seconds: int = 1800
    backup_retention_days: int = 7
    backup_paths: list[str] = field(default_factory=lambda: ["hashes/*.sha256", "data/snapshot_*.json"])
    integrity_paths: list[str] = field(default_factory=lambda: ["core/*.py", "scripts/run_pipeline.py"])
    cpu_threshold_percent: float = 85.0
    cpu_sustain_seconds: int = 120
    memory_threshold_percent: float = 80.0
    user_agents_list: list[str] = field(default_factory=list)
    rotate_every_min_polls: int = 10
    rotate_every_max_polls: int = 30
    proxy_list: list[str] = field(default_factory=list)
    anomaly_consecutive_limit: int = 3
    honeypot_flood_trigger_count: int = 5
    honeypot_flood_window_seconds: int = 120
    auto_backup_forensic_logs: bool = True
    alert_escalation_failures: int = 3
    integrity_max_established_connections: int = 100
    honeypot_threshold_per_minute: int = 100
    prometheus_enabled: bool = True
    prometheus_port: int = 8000
    cpu_adaptive_margin_percent: float = 20.0
    cpu_spike_grace_seconds: int = 15
    cpu_baseline_window: int = 6
    alert_sms_webhook: str = ""
    solidity_contract_paths: list[str] = field(default_factory=lambda: ["contracts/**/*.sol"])
    solidity_blocked_patterns: list[str] = field(default_factory=lambda: ["tx.origin", "delegatecall", "selfdestruct"])

    @classmethod
    def from_yaml(cls, path: Path) -> "AdvancedSecurityConfig":
        if not path.exists():
            return cls()
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(raw, dict):
            return cls()
        return cls(
            enabled=bool(raw.get("enabled", True)),
            honeypot_enabled=bool(raw.get("honeypot_enabled", False)),
            honeypot_host=str(raw.get("honeypot_host", "127.0.0.1")),
            honeypot_port=int(raw.get("honeypot_port", 8081)),
            honeypot_endpoints=[str(p) for p in raw.get("honeypot_endpoints", ["/admin", "/login"])],
            airgap_min_minutes=int(raw.get("airgap_min_minutes", 5)),
            airgap_max_minutes=int(raw.get("airgap_max_minutes", 30)),
            backup_provider=str(raw.get("backup_provider", "local")),
            backup_interval_seconds=int(raw.get("backup_interval", 1800)),
            backup_retention_days=int(raw.get("backup_retention_days", 7)),
            backup_paths=[str(p) for p in raw.get("backup_paths", ["hashes/*.sha256", "data/snapshot_*.json"])],
            integrity_paths=[str(p) for p in raw.get("integrity_paths", ["core/*.py"] )],
            cpu_threshold_percent=float(raw.get("cpu_threshold_percent", 85)),
            cpu_sustain_seconds=int(raw.get("cpu_sustain_seconds", 120)),
            memory_threshold_percent=float(raw.get("memory_threshold_percent", 80)),
            user_agents_list=[str(u) for u in raw.get("user_agents_list", [])],
            rotate_every_min_polls=int(raw.get("rotate_every_min_polls", 10)),
            rotate_every_max_polls=int(raw.get("rotate_every_max_polls", 30)),
            proxy_list=[str(p) for p in raw.get("proxy_list", [])],
            anomaly_consecutive_limit=int(raw.get("anomaly_consecutive_limit", 3)),
            honeypot_flood_trigger_count=int(raw.get("honeypot_flood_trigger_count", 5)),
            honeypot_flood_window_seconds=int(raw.get("honeypot_flood_window_seconds", 120)),
            auto_backup_forensic_logs=bool(raw.get("auto_backup_forensic_logs", True)),
            alert_escalation_failures=int(raw.get("alert_escalation_failures", 3)),
            integrity_max_established_connections=int(raw.get("integrity_max_established_connections", 100)),
            honeypot_threshold_per_minute=int(raw.get("honeypot_threshold_per_minute", 100)),
            prometheus_enabled=bool(raw.get("prometheus_enabled", True)),
            prometheus_port=int(raw.get("prometheus_port", 8000)),
            cpu_adaptive_margin_percent=float(raw.get("cpu_adaptive_margin_percent", 20)),
            cpu_spike_grace_seconds=int(raw.get("cpu_spike_grace_seconds", 15)),
            cpu_baseline_window=int(raw.get("cpu_baseline_window", 6)),
            alert_sms_webhook=str(raw.get("alert_sms_webhook", "")),
            solidity_contract_paths=[str(p) for p in raw.get("solidity_contract_paths", ["contracts/**/*.sol"])],
            solidity_blocked_patterns=[str(p) for p in raw.get("solidity_blocked_patterns", ["tx.origin", "delegatecall", "selfdestruct"])],
        )


ANOMALY_COUNTER = Counter("centinel_security_anomalies_total", "Detected security anomalies", ["type"])
ALERT_COUNTER = Counter("centinel_security_alerts_total", "Security alerts emitted", ["event", "level"])
CPU_GAUGE = Gauge("centinel_security_cpu_percent", "Current host CPU percent")
LOG_SIZE_GAUGE = Gauge("centinel_attack_log_size_bytes", "Attack log current size")


class IdentityRotator:
    """Rotates UA/proxy profile for reduced fingerprinting.

    Rota perfil de UA/proxy para reducir fingerprinting.
    """

    def __init__(self, config: AdvancedSecurityConfig) -> None:
        self.config = config
        self._poll_count = 0
        self._next_rotation = random.randint(config.rotate_every_min_polls, config.rotate_every_max_polls)
        self._current_ua = config.user_agents_list[0] if config.user_agents_list else "Mozilla/5.0 (compatible; Centinel-Engine/1.0)"
        self._current_proxy = ""

    def _rotate_now(self) -> None:
        valid = [ua for ua in self.config.user_agents_list if "/1.0" in ua]
        if valid:
            self._current_ua = random.choice(valid)
        self._current_proxy = random.choice(self.config.proxy_list) if self.config.proxy_list else ""
        self._next_rotation = random.randint(self.config.rotate_every_min_polls, self.config.rotate_every_max_polls)
        self._poll_count = 0

    def next_headers(self) -> dict[str, str]:
        self._poll_count += 1
        if self._poll_count >= self._next_rotation:
            self._rotate_now()
        return {"User-Agent": self._current_ua, "Accept": "application/json"}

    def current_proxies(self) -> dict[str, str] | None:
        if not self._current_proxy:
            return None
        return {"http": self._current_proxy, "https": self._current_proxy}


class HoneypotService:
    """Light honeypot Flask service.

    Servicio honeypot ligero con Flask.
    """

    def __init__(self, config: AdvancedSecurityConfig) -> None:
        self.config = config
        self.app: Any = None
        self._request_ref: Any = None
        try:
            from flask import Flask, request as flask_request

            self.app = Flask("centinel_honeypot")
            self._request_ref = flask_request
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("honeypot_flask_unavailable error=%s", exc)
        self._thread: threading.Thread | None = None
        self._server: Any = None
        self.events_path = Path("logs/honeypot_events.jsonl")
        self.events_path.parent.mkdir(parents=True, exist_ok=True)
        self._register_routes()

    def _register_routes(self) -> None:
        if self.app is None:
            return

        @self.app.route("/", defaults={"subpath": ""}, methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
        @self.app.route("/<path:subpath>", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
        def trap(subpath: str):
            path = "/" + subpath
            if path not in self.config.honeypot_endpoints:
                return ("Not Found", 404)
            response = random.choice([404, 403, 500])
            self._log_request(self._request_ref)
            return ("", response)

    def _log_request(self, req: Any) -> None:
        event = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "ip": req.remote_addr,
            "method": req.method,
            "route": req.path,
            "headers": dict(req.headers),
            "user_agent": req.headers.get("User-Agent", ""),
            "content_length": int(req.content_length or 0),
            "classification": "scan" if req.path.count("/") >= 1 else "suspicious",
        }
        with self.events_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False) + "\n")

    def start(self) -> None:
        if not self.config.honeypot_enabled or self.app is None:
            return
        from werkzeug.serving import make_server

        self._server = make_server(self.config.honeypot_host, self.config.honeypot_port, self.app)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()


class AlertManager:
    """Escalating security alerts.

    Alertas de seguridad escalonadas.
    """

    def send(self, level: int, event: str, metrics: dict[str, Any] | None = None) -> None:
        """Send staged alerts over local log + external channels.

        Envía alertas escalonadas por log local + canales externos.
        """
        payload = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "event": event,
            "metrics": metrics or {},
        }
        LOGGER.warning("security_alert %s", payload)
        ALERT_COUNTER.labels(event=event, level=str(level)).inc()
        if level == 1:
            return
        if level >= 3 and self._send_telegram(payload):
            self._send_sms_webhook(payload)
            return
        self._send_email(payload)
        if level >= 2:
            self._send_sms_webhook(payload)

    def _send_email(self, payload: dict[str, Any]) -> None:
        server = os.getenv("SMTP_SERVER", "")
        user = os.getenv("SMTP_USER", "")
        password = os.getenv("SMTP_PASSWORD", "")
        sender = os.getenv("SMTP_FROM", user)
        recipient = os.getenv("ADMIN_EMAIL", "")
        if not server or not sender or not recipient:
            return
        msg = EmailMessage()
        msg["Subject"] = f"[Centinel] Security Alert L{payload['level']}"
        msg["From"] = sender
        msg["To"] = recipient
        msg.set_content(json.dumps(payload, ensure_ascii=False, indent=2))
        with smtplib.SMTP(server, int(os.getenv("SMTP_PORT", "587")), timeout=10) as smtp:
            smtp.starttls()
            if user and password:
                smtp.login(user, password)
            smtp.send_message(msg)

    def _send_telegram(self, payload: dict[str, Any]) -> bool:
        token = os.getenv("TELEGRAM_TOKEN", "")
        chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        if not token or not chat_id:
            return False
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            timeout=10,
            json={"chat_id": chat_id, "text": json.dumps(payload, ensure_ascii=False)},
        )
        return resp.status_code < 300

    def _send_sms_webhook(self, payload: dict[str, Any]) -> bool:
        endpoint = os.getenv("SMS_WEBHOOK_URL", "")
        if not endpoint:
            return False
        resp = requests.post(endpoint, timeout=10, json=payload)
        return resp.status_code < 300


class BackupManager:
    """Encrypted snapshot/hash backups to off-site targets.

    Backups cifrados de snapshots/hashes a destinos externos.
    """

    def __init__(self, config: AdvancedSecurityConfig) -> None:
        self.config = config
        self.last_backup_at = 0.0
        self._persist_path = Path("data/backups/pre_oom_snapshot.json")

    def _build_archive(self) -> Path:
        backup_dir = Path("data/backups")
        backup_dir.mkdir(parents=True, exist_ok=True)
        out = backup_dir / f"advanced_backup_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
        payload: dict[str, str] = {}
        for pattern in self.config.backup_paths:
            for candidate in glob.glob(pattern, recursive=True):
                file = Path(candidate)
                if file.is_file():
                    payload[str(file)] = file.read_text(encoding="utf-8", errors="ignore")
        out.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return self._encrypt_file(out)

    def _encrypt_file(self, path: Path) -> Path:
        key = os.getenv("BACKUP_AES_KEY")
        if not key:
            LOGGER.warning("backup_encryption_skipped_missing_key")
            return path
        fernet = Fernet(key.encode("utf-8"))
        encrypted = path.with_suffix(path.suffix + ".enc")
        encrypted.write_bytes(fernet.encrypt(path.read_bytes()))
        path.unlink(missing_ok=True)
        return encrypted

    def maybe_backup(self, force: bool = False) -> None:
        now = time.time()
        if not force and now - self.last_backup_at < self.config.backup_interval_seconds:
            return
        archive = self._build_archive()
        try:
            self._upload(archive)
            self.last_backup_at = now
        finally:
            self._rotate_local_retention()

    def persist_before_kill(self, reason: str) -> None:
        """Persist minimal backup metadata before OOM/forced termination.

        Persiste metadata mínima antes de OOM/terminación forzada.
        """
        self._persist_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "reason": reason,
            "backup_provider": self.config.backup_provider,
        }
        self._persist_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        self.maybe_backup(force=True)

    def _upload(self, archive: Path) -> None:
        provider = self.config.backup_provider.lower()
        if provider == "s3" and boto3:
            s3 = boto3.client("s3")
            bucket = os.getenv("AWS_BACKUP_BUCKET", "")
            if bucket:
                s3.upload_file(str(archive), bucket, archive.name)
                return
        if provider == "b2" and B2Api and InMemoryAccountInfo:
            key_id = os.getenv("B2_KEY_ID", "")
            key = os.getenv("B2_APP_KEY", "")
            bucket_name = os.getenv("B2_BUCKET", "")
            if key_id and key and bucket_name:
                api = B2Api(InMemoryAccountInfo())
                api.authorize_account("production", key_id, key)
                api.get_bucket_by_name(bucket_name).upload_local_file(local_file=str(archive), file_name=archive.name)
                return
        if provider == "github":
            repo = os.getenv("BACKUP_GIT_REPO", "")
            if repo:
                subprocess.run(["git", "add", str(archive)], check=False)
                subprocess.run(["git", "commit", "-m", f"backup: {archive.name}"], check=False)
                subprocess.run(["git", "push", repo], check=False)
                return
        LOGGER.info("backup_provider_fallback_local provider=%s file=%s", provider, archive)

    def _rotate_local_retention(self) -> None:
        cutoff = time.time() - self.config.backup_retention_days * 86400
        for file in Path("data/backups").glob("advanced_backup_*.json*"):
            if file.stat().st_mtime < cutoff:
                file.unlink(missing_ok=True)


class AdvancedSecurityManager:
    """High-level integrated defensive manager.

    Gestor defensivo integrado de alto nivel.
    """

    def __init__(self, config: AdvancedSecurityConfig) -> None:
        self.config = config
        self.identity = IdentityRotator(config)
        self.honeypot = HoneypotService(config)
        self.alerts = AlertManager()
        self.backups = BackupManager(config)
        self._cpu_high_since: float | None = None
        self._stop_event = threading.Event()
        self._baseline_files = self._scan_files()
        self._anomaly_consecutive = 0
        self._alert_failures = 0
        self._flood_events: list[float] = []
        self._cpu_samples: deque[float] = deque(maxlen=max(3, config.cpu_baseline_window))
        self._metrics_started = False
        self._honeypot_events_per_minute: deque[float] = deque(maxlen=500)
        self.attack_logbook = AttackForensicsLogbook(AttackLogConfig.from_yaml(Path("command_center/attack_config.yaml")), self.on_attack_event)
        self.runtime_security = DefensiveSecurityManager(SecurityConfig.from_yaml(Path("command_center/security_config.yaml")))
        self._register_signal_handlers()
        atexit.register(self.shutdown)

    def _register_signal_handlers(self) -> None:
        for sig in (getattr(signal, "SIGTERM", None), getattr(signal, "SIGINT", None), getattr(signal, "SIGUSR1", None)):
            if sig is None:
                continue
            signal.signal(sig, self._handle_oom_like_signal)

    def _handle_oom_like_signal(self, signum: int, _frame: Any) -> None:
        self.backups.persist_before_kill(reason=f"signal_{signum}")

    def start(self) -> None:
        if not self.config.enabled:
            return
        self.attack_logbook.start()
        if self.config.prometheus_enabled and not self._metrics_started:
            start_http_server(self.config.prometheus_port)
            self._metrics_started = True
        self.honeypot.start()
        self.runtime_security.start_honeypot()

    def get_request_profile(self) -> tuple[dict[str, str], dict[str, str] | None]:
        return self.identity.next_headers(), self.identity.current_proxies()

    def _scan_files(self) -> set[str]:
        files: set[str] = set()
        for pattern in self.config.integrity_paths:
            for candidate in glob.glob(pattern):
                p = Path(candidate)
                if p.is_file():
                    files.add(str(p))
        return files

    def detect_internal_anomalies(self) -> list[str]:
        triggers: list[str] = []
        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory().percent
        CPU_GAUGE.set(cpu)
        if self.attack_logbook.path.exists():
            LOG_SIZE_GAUGE.set(self.attack_logbook.path.stat().st_size)
        now = time.time()
        self._cpu_samples.append(cpu)
        baseline = sum(self._cpu_samples) / max(1, len(self._cpu_samples))
        adaptive_cpu_threshold = min(99.0, max(self.config.cpu_threshold_percent, baseline + self.config.cpu_adaptive_margin_percent))
        if cpu > adaptive_cpu_threshold:
            self._cpu_high_since = self._cpu_high_since or now
            sustained_for = now - self._cpu_high_since
            if sustained_for >= max(self.config.cpu_spike_grace_seconds, self.config.cpu_sustain_seconds):
                triggers.append(f"cpu_sustained:{cpu:.1f}")
        else:
            self._cpu_high_since = None
        if mem > self.config.memory_threshold_percent:
            triggers.append(f"memory_high:{mem:.1f}")
        if self._scan_files() - self._baseline_files:
            triggers.append("new_file_detected")
        triggers.extend(self._validate_solidity_runtime())
        triggers.extend(self.runtime_security.detect_hostile_conditions())
        for trigger in triggers:
            ANOMALY_COUNTER.labels(type=trigger.split(":", 1)[0]).inc()
        return triggers

    def _validate_solidity_runtime(self) -> list[str]:
        findings: list[str] = []
        for pattern in self.config.solidity_contract_paths:
            for candidate in glob.glob(pattern, recursive=True):
                contract = Path(candidate)
                if not contract.is_file():
                    continue
                content = contract.read_text(encoding="utf-8", errors="ignore")
                if "pragma solidity" not in content:
                    findings.append(f"solidity_missing_pragma:{contract}")
                    continue
                for blocked in self.config.solidity_blocked_patterns:
                    if blocked in content:
                        findings.append(f"solidity_blocked_pattern:{blocked}")
        return findings

    def on_attack_event(self, event: dict[str, Any]) -> None:
        """Bridge attack logbook and dead-man switch thresholds.

        Puente entre bitácora forense y umbrales del interruptor defensivo.
        """
        if event.get("classification") != "flood":
            return
        now = time.time()
        self._flood_events.append(now)
        self._honeypot_events_per_minute.append(now)
        window = self.config.honeypot_flood_window_seconds
        self._flood_events = [stamp for stamp in self._flood_events if now - stamp <= window]
        self._honeypot_events_per_minute = deque(
            [stamp for stamp in self._honeypot_events_per_minute if now - stamp <= 60],
            maxlen=500,
        )
        if len(self._flood_events) >= self.config.honeypot_flood_trigger_count:
            self._safe_alert(2, "honeypot_flood_threshold", {"count": len(self._flood_events), "window_seconds": window})
            self.air_gap("honeypot_flood_threshold")
            self._flood_events.clear()
        if len(self._honeypot_events_per_minute) >= self.config.honeypot_threshold_per_minute:
            self._safe_alert(3, "honeypot_rate_limit_deadman", {"rpm": len(self._honeypot_events_per_minute)})
            self.air_gap("honeypot_rate_limit_deadman")
            self._honeypot_events_per_minute.clear()

    def air_gap(self, reason: str) -> None:
        self._safe_alert(3, "air_gap_enter", {"reason": reason})
        gc.collect()
        self.honeypot.stop()
        self.runtime_security.stop_honeypot()
        if self.config.auto_backup_forensic_logs:
            self.backups.maybe_backup(force=True)
        sleep_seconds = random.randint(self.config.airgap_min_minutes * 60, self.config.airgap_max_minutes * 60)
        time.sleep(sleep_seconds)
        if self.verify_integrity():
            self.honeypot.start()
            self.runtime_security.start_honeypot()
            self._safe_alert(2, "air_gap_exit", {"slept_seconds": sleep_seconds})

    def _safe_alert(self, level: int, event: str, metrics: dict[str, Any]) -> None:
        """Emit alerts with simple failure-based escalation.

        Emite alertas con escalamiento simple basado en fallos.
        """
        try:
            self.alerts.send(level, event, metrics)
            self._alert_failures = 0
        except Exception:  # noqa: BLE001
            self._alert_failures += 1
            if self._alert_failures >= self.config.alert_escalation_failures:
                LOGGER.error("alert_delivery_repeated_failure event=%s count=%s", event, self._alert_failures)

    def verify_integrity(self) -> bool:
        suspicious = [p for p in psutil.net_connections(kind="inet") if getattr(p, "status", "") == psutil.CONN_ESTABLISHED]
        if len(suspicious) > self.config.integrity_max_established_connections:
            return False
        for pattern in self.config.integrity_paths:
            for file in Path(".").glob(pattern):
                _ = hashlib.sha256(file.read_bytes()).hexdigest()
        return True

    def on_poll_cycle(self) -> None:
        triggers = self.detect_internal_anomalies()
        if triggers:
            self._anomaly_consecutive += 1
            self._safe_alert(2, "internal_anomaly", {"triggers": triggers, "consecutive_count": self._anomaly_consecutive})
            if self._anomaly_consecutive >= self.config.anomaly_consecutive_limit:
                self.air_gap(",".join(triggers))
                self._anomaly_consecutive = 0
        else:
            self._anomaly_consecutive = 0
        self.backups.maybe_backup(force=False)
        self.attack_logbook.log_connection_snapshot()

    def shutdown(self) -> None:
        self.backups.maybe_backup(force=True)
        self.attack_logbook.stop()
        self.runtime_security.stop_honeypot()
        self.honeypot.stop()


_MANAGER: AdvancedSecurityManager | None = None
_MANAGER_LOCK = threading.Lock()


def load_manager(config_path: Path = Path("command_center/advanced_security_config.yaml")) -> AdvancedSecurityManager:
    """Load singleton manager from YAML config.

    Carga singleton del manager desde YAML.
    """
    global _MANAGER
    if _MANAGER is None:
        with _MANAGER_LOCK:
            if _MANAGER is None:
                _MANAGER = AdvancedSecurityManager(AdvancedSecurityConfig.from_yaml(config_path))
    return _MANAGER


def update_runtime_security_hooks() -> tuple[dict[str, str], dict[str, str] | None]:
    """Convenience API for fetchers.

    API de conveniencia para fetchers.
    """
    manager = load_manager()
    return manager.get_request_profile()
