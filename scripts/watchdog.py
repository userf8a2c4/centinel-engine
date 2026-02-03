"""Watchdog de resiliencia para Centinel Engine.

Resilience watchdog for Centinel Engine.
"""

from __future__ import annotations

import json
import logging
import os
import signal
import socket
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import psutil
import requests
import yaml

from scripts.logging_utils import configure_logging, log_event


@dataclass
class WatchdogConfig:
    """Español: Clase WatchdogConfig del módulo scripts/watchdog.py.

    English: WatchdogConfig class defined in scripts/watchdog.py.
    """
    check_interval_minutes: int = 3
    max_inactivity_minutes: int = 30
    heartbeat_timeout: int = 10
    failure_grace_minutes: int = 5
    action_cooldown_minutes: int = 10
    aggressive_restart: bool = False
    alert_urls: list[str] = field(default_factory=list)
    data_dir: str = "data"
    snapshot_glob: str = "*.json"
    snapshot_exclude: tuple[str, ...] = (
        "pipeline_state.json",
        "heartbeat.json",
        "alerts.json",
        "snapshot_index.json",
        "pipeline_checkpoint.json",
        "checkpoint.json",
    )
    log_path: str = "logs/centinel.log"
    max_log_size_mb: int = 200
    max_log_growth_mb_per_min: int = 30
    lock_files: tuple[str, ...] = (
        "data/temp/pipeline.lock",
        "data/temp/stuck.lock",
    )
    lock_timeout_minutes: int = 30
    heartbeat_path: str = "data/heartbeat.json"
    pipeline_process_match: tuple[str, ...] = ("scripts/run_pipeline.py",)
    pipeline_command: tuple[str, ...] = ("python", "scripts/run_pipeline.py")
    restart_timeout_seconds: int = 30
    docker_socket_path: str = "/var/run/docker.sock"
    docker_container_name: str = "centinel-engine"
    state_path: str = "data/watchdog_state.json"


def _utcnow() -> datetime:
    """Español: Función _utcnow del módulo scripts/watchdog.py.

    English: Function _utcnow defined in scripts/watchdog.py.
    """
    return datetime.now(timezone.utc)


def _load_config(path: Path) -> WatchdogConfig:
    """Español: Función _load_config del módulo scripts/watchdog.py.

    English: Function _load_config defined in scripts/watchdog.py.
    """
    if not path.exists():
        return WatchdogConfig()
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        logger = logging.getLogger("centinel.watchdog")
        logger.warning("watchdog_config_invalid path=%s error=%s", path, exc)
        return WatchdogConfig()
    if not isinstance(raw, dict):
        return WatchdogConfig()
    cfg = WatchdogConfig()
    for field_name in cfg.__dataclass_fields__:
        if field_name in raw:
            setattr(cfg, field_name, raw[field_name])
    cfg.check_interval_minutes = max(3, min(5, int(cfg.check_interval_minutes)))
    cfg.max_inactivity_minutes = int(cfg.max_inactivity_minutes)
    cfg.heartbeat_timeout = int(cfg.heartbeat_timeout)
    cfg.failure_grace_minutes = int(cfg.failure_grace_minutes)
    cfg.action_cooldown_minutes = int(cfg.action_cooldown_minutes)
    cfg.max_log_size_mb = int(cfg.max_log_size_mb)
    cfg.max_log_growth_mb_per_min = int(cfg.max_log_growth_mb_per_min)
    cfg.lock_timeout_minutes = int(cfg.lock_timeout_minutes)
    cfg.restart_timeout_seconds = int(cfg.restart_timeout_seconds)
    return cfg


def _load_state(path: Path) -> dict[str, Any]:
    """Español: Función _load_state del módulo scripts/watchdog.py.

    English: Function _load_state defined in scripts/watchdog.py.
    """
    if not path.exists():
        return {"failures": {}, "last_action": None, "log_state": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"failures": {}, "last_action": None, "log_state": {}}
    if not isinstance(payload, dict):
        return {"failures": {}, "last_action": None, "log_state": {}}
    payload.setdefault("failures", {})
    payload.setdefault("last_action", None)
    payload.setdefault("log_state", {})
    return payload


def _save_state(path: Path, payload: dict[str, Any]) -> None:
    """Español: Función _save_state del módulo scripts/watchdog.py.

    English: Function _save_state defined in scripts/watchdog.py.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _find_latest_snapshot(config: WatchdogConfig) -> tuple[Path | None, float | None]:
    """Español: Función _find_latest_snapshot del módulo scripts/watchdog.py.

    English: Function _find_latest_snapshot defined in scripts/watchdog.py.
    """
    data_dir = Path(config.data_dir)
    if not data_dir.exists():
        return None, None
    candidates = sorted(
        data_dir.glob(config.snapshot_glob),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for snapshot in candidates:
        if snapshot.name in config.snapshot_exclude:
            continue
        try:
            json.loads(snapshot.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        return snapshot, snapshot.stat().st_mtime
    return None, None


def _check_snapshot(config: WatchdogConfig) -> tuple[bool, str]:
    """Español: Función _check_snapshot del módulo scripts/watchdog.py.

    English: Function _check_snapshot defined in scripts/watchdog.py.
    """
    snapshot, mtime = _find_latest_snapshot(config)
    if not snapshot or not mtime:
        return False, "snapshot_missing"
    age = _utcnow() - datetime.fromtimestamp(mtime, timezone.utc)
    if age > timedelta(minutes=config.max_inactivity_minutes):
        return False, f"snapshot_stale age_minutes={age.total_seconds() / 60:.1f}"
    return True, f"snapshot_ok file={snapshot.name}"


def _check_log_growth(config: WatchdogConfig, state: dict[str, Any]) -> tuple[bool, str]:
    """Español: Función _check_log_growth del módulo scripts/watchdog.py.

    English: Function _check_log_growth defined in scripts/watchdog.py.
    """
    log_path = Path(config.log_path)
    if not log_path.exists():
        return False, "log_missing"
    size_mb = log_path.stat().st_size / (1024 * 1024)
    if size_mb > config.max_log_size_mb:
        return False, f"log_too_large size_mb={size_mb:.1f}"
    log_state = state.setdefault("log_state", {})
    last_size = log_state.get("last_size_mb")
    last_ts = log_state.get("last_ts")
    now_ts = _utcnow().timestamp()
    if last_size is not None and last_ts is not None:
        elapsed_min = max((now_ts - last_ts) / 60, 1e-6)
        growth = (size_mb - float(last_size)) / elapsed_min
        if growth > config.max_log_growth_mb_per_min:
            return False, f"log_growth_fast growth_mb_min={growth:.2f}"
    log_state["last_size_mb"] = size_mb
    log_state["last_ts"] = now_ts
    return True, f"log_ok size_mb={size_mb:.1f}"


def _check_locks(config: WatchdogConfig) -> tuple[bool, str]:
    """Español: Función _check_locks del módulo scripts/watchdog.py.

    English: Function _check_locks defined in scripts/watchdog.py.
    """
    stuck = []
    now = _utcnow()
    for lock_path_str in config.lock_files:
        lock_path = Path(lock_path_str)
        if not lock_path.exists():
            continue
        age = now - datetime.fromtimestamp(lock_path.stat().st_mtime, timezone.utc)
        if age > timedelta(minutes=config.lock_timeout_minutes):
            stuck.append(f"{lock_path}:{age.total_seconds() / 60:.1f}m")
    if stuck:
        return False, "lock_stuck " + ",".join(stuck)
    return True, "locks_ok"


def _check_heartbeat(config: WatchdogConfig) -> tuple[bool, str]:
    """Español: Función _check_heartbeat del módulo scripts/watchdog.py.

    English: Function _check_heartbeat defined in scripts/watchdog.py.
    """
    heartbeat_path = Path(config.heartbeat_path)
    if not heartbeat_path.exists():
        return False, "heartbeat_missing"
    age = _utcnow() - datetime.fromtimestamp(
        heartbeat_path.stat().st_mtime, timezone.utc
    )
    if age > timedelta(minutes=config.heartbeat_timeout):
        return False, f"heartbeat_stale age_minutes={age.total_seconds() / 60:.1f}"
    return True, "heartbeat_ok"


def _record_failures(
    failures: dict[str, str], state: dict[str, Any], logger: logging.Logger
) -> dict[str, dict[str, Any]]:
    """Español: Función _record_failures del módulo scripts/watchdog.py.

    English: Function _record_failures defined in scripts/watchdog.py.
    """
    now_iso = _utcnow().isoformat()
    tracked = state.setdefault("failures", {})
    for name, reason in failures.items():
        entry = tracked.get(name)
        if not entry:
            tracked[name] = {"first_seen": now_iso, "last_seen": now_iso, "reason": reason}
        else:
            entry["last_seen"] = now_iso
            entry["reason"] = reason
    for name in list(tracked.keys()):
        if name not in failures:
            logger.info("watchdog_recovered check=%s", name)
            tracked.pop(name, None)
    return tracked


def _should_act(state: dict[str, Any], config: WatchdogConfig) -> tuple[bool, list[str]]:
    """Español: Función _should_act del módulo scripts/watchdog.py.

    English: Function _should_act defined in scripts/watchdog.py.
    """
    failures = state.get("failures", {})
    if not failures:
        return False, []
    now = _utcnow()
    reasons = []
    for name, entry in failures.items():
        first_seen = entry.get("first_seen")
        if not first_seen:
            continue
        try:
            first_dt = datetime.fromisoformat(first_seen)
        except ValueError:
            continue
        if now - first_dt >= timedelta(minutes=config.failure_grace_minutes):
            reasons.append(f"{name}:{entry.get('reason')}")
    if not reasons:
        return False, []
    last_action = state.get("last_action")
    if last_action:
        try:
            last_dt = datetime.fromisoformat(last_action)
            if now - last_dt < timedelta(minutes=config.action_cooldown_minutes):
                return False, reasons
        except ValueError:
            pass
    return True, reasons


def _send_alerts(config: WatchdogConfig, message: str, logger: logging.Logger) -> None:
    """Español: Función _send_alerts del módulo scripts/watchdog.py.

    English: Function _send_alerts defined in scripts/watchdog.py.
    """
    print(f"[WATCHDOG ALERT] {message}")
    for url in config.alert_urls:
        try:
            response = requests.post(
                url,
                json={"event": "watchdog_alert", "message": message},
                timeout=10,
            )
            logger.info("watchdog_alert_sent url=%s status=%s", url, response.status_code)
        except requests.RequestException as exc:
            logger.warning("watchdog_alert_failed url=%s error=%s", url, exc)


def _terminate_pipeline(config: WatchdogConfig, logger: logging.Logger) -> bool:
    """Español: Función _terminate_pipeline del módulo scripts/watchdog.py.

    English: Function _terminate_pipeline defined in scripts/watchdog.py.
    """
    matched = []
    for proc in psutil.process_iter(["pid", "cmdline"]):
        cmdline = proc.info.get("cmdline") or []
        joined = " ".join(cmdline)
        if any(match in joined for match in config.pipeline_process_match):
            matched.append(proc)
    if not matched:
        logger.warning("watchdog_pipeline_not_found")
        return False
    for proc in matched:
        try:
            proc.terminate()
        except psutil.Error as exc:
            logger.warning("watchdog_pipeline_terminate_failed pid=%s error=%s", proc.pid, exc)
    gone, alive = psutil.wait_procs(matched, timeout=config.restart_timeout_seconds)
    if alive:
        for proc in alive:
            try:
                proc.kill()
            except psutil.Error as exc:
                logger.warning("watchdog_pipeline_kill_failed pid=%s error=%s", proc.pid, exc)
        psutil.wait_procs(alive, timeout=5)
    logger.info("watchdog_pipeline_terminated count=%s", len(matched))
    return True


def _start_pipeline(config: WatchdogConfig, logger: logging.Logger) -> None:
    """Español: Función _start_pipeline del módulo scripts/watchdog.py.

    English: Function _start_pipeline defined in scripts/watchdog.py.
    """
    try:
        subprocess.Popen(list(config.pipeline_command))  # noqa: S603,S607
        logger.info("watchdog_pipeline_started cmd=%s", config.pipeline_command)
    except OSError as exc:
        logger.warning("watchdog_pipeline_start_failed error=%s", exc)


def _docker_restart(config: WatchdogConfig, logger: logging.Logger) -> bool:
    """Español: Función _docker_restart del módulo scripts/watchdog.py.

    English: Function _docker_restart defined in scripts/watchdog.py.
    """
    socket_path = config.docker_socket_path
    if not Path(socket_path).exists():
        logger.warning("watchdog_docker_socket_missing path=%s", socket_path)
        return False
    request_line = f"POST /containers/{config.docker_container_name}/restart HTTP/1.1\r\n"
    headers = (
        f"Host: localhost\r\nContent-Length: 0\r\nConnection: close\r\n\r\n"
    )
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(10)
            client.connect(socket_path)
            client.sendall(request_line.encode("utf-8") + headers.encode("utf-8"))
            response = client.recv(1024).decode("utf-8", errors="ignore")
    except OSError as exc:
        logger.warning("watchdog_docker_restart_failed error=%s", exc)
        return False
    if "204 No Content" in response or "304 Not Modified" in response:
        logger.info("watchdog_docker_restart_ok container=%s", config.docker_container_name)
        return True
    logger.warning("watchdog_docker_restart_unexpected response=%s", response.splitlines()[:1])
    return False


def _force_restart_self(logger: logging.Logger) -> None:
    """Español: Función _force_restart_self del módulo scripts/watchdog.py.

    English: Function _force_restart_self defined in scripts/watchdog.py.
    """
    logger.critical("watchdog_force_restart_self pid=1")
    try:
        os.kill(1, signal.SIGTERM)
        time.sleep(5)
        os.kill(1, signal.SIGKILL)
    except OSError as exc:
        logger.warning("watchdog_force_restart_failed error=%s", exc)


def _handle_failure(config: WatchdogConfig, reasons: list[str], logger: logging.Logger) -> None:
    """Español: Función _handle_failure del módulo scripts/watchdog.py.

    English: Function _handle_failure defined in scripts/watchdog.py.
    """
    summary = "; ".join(reasons)
    log_event(logger, logging.CRITICAL, "watchdog_failure", reasons=summary)
    _send_alerts(config, summary, logger)
    _terminate_pipeline(config, logger)
    _start_pipeline(config, logger)
    if config.aggressive_restart:
        if not _docker_restart(config, logger):
            _force_restart_self(logger)


def run_watchdog(config: WatchdogConfig, logger: logging.Logger) -> None:
    """Español: Función run_watchdog del módulo scripts/watchdog.py.

    English: Function run_watchdog defined in scripts/watchdog.py.
    """
    state_path = Path(config.state_path)
    while True:
        state = _load_state(state_path)
        failures: dict[str, str] = {}
        ok, message = _check_snapshot(config)
        if not ok:
            failures["snapshot"] = message
        logger.info("watchdog_snapshot %s", message)
        ok, message = _check_log_growth(config, state)
        if not ok:
            failures["log"] = message
        logger.info("watchdog_log %s", message)
        ok, message = _check_locks(config)
        if not ok:
            failures["locks"] = message
        logger.info("watchdog_locks %s", message)
        ok, message = _check_heartbeat(config)
        if not ok:
            failures["heartbeat"] = message
        logger.info("watchdog_heartbeat %s", message)
        _record_failures(failures, state, logger)
        should_act, reasons = _should_act(state, config)
        if should_act:
            _handle_failure(config, reasons, logger)
            state["last_action"] = _utcnow().isoformat()
        _save_state(state_path, state)
        time.sleep(config.check_interval_minutes * 60)


def main() -> None:
    """Español: Función main del módulo scripts/watchdog.py.

    English: Function main defined in scripts/watchdog.py.
    """
    config_path = Path(os.getenv("WATCHDOG_CONFIG", "watchdog.yaml"))
    logger = configure_logging("centinel.watchdog", log_file="logs/watchdog.log")
    logger.info("watchdog_start config=%s", config_path)
    config = _load_config(config_path)
    run_watchdog(config, logger)


if __name__ == "__main__":
    main()
