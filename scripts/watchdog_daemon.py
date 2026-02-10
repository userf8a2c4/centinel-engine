#!/usr/bin/env python3
"""Obsessive self-healing watchdog daemon for C.E.N.T.I.N.E.L.
(Daemon watchdog obsesivo de auto-curación para C.E.N.T.I.N.E.L.)

Runs as an external process (systemd-compatible) that continuously monitors
the pipeline's health and autonomously heals failures:
  • System diagnostics — CPU, memory, disk via psutil
  • CNE endpoint reachability — HTTP HEAD with timeout
  • Proxy/cache reset — clears stale proxy state and temp caches
  • Pipeline restart — graceful SIGTERM → SIGKILL escalation
  • Anti-loop cooldown — prevents restart storms
  • DoS simulation — for load-testing the recovery path

(Se ejecuta como proceso externo (compatible con systemd) que monitorea
continuamente la salud del pipeline y cura fallos autónomamente:
  • Diagnóstico de sistema — CPU, memoria, disco vía psutil
  • Alcanzabilidad del endpoint CNE — HTTP HEAD con timeout
  • Reset de proxies/caches — limpia estado de proxies y caches temporales
  • Reinicio del pipeline — escalación SIGTERM → SIGKILL
  • Cooldown anti-loop — previene tormentas de reinicio
  • Simulación DoS — para stress-testing de la ruta de recuperación.)

Config: command_center/config.yaml → resilience section.
Usage:
    python scripts/watchdog_daemon.py                  # Normal mode (Modo normal)
    python scripts/watchdog_daemon.py --simulate-dos   # DoS simulation (Simulación DoS)

systemd unit example (ejemplo de unidad systemd):
    [Unit]
    Description=CENTINEL Watchdog Daemon
    After=network.target

    [Service]
    Type=simple
    ExecStart=/usr/bin/python3 /opt/centinel-engine/scripts/watchdog_daemon.py
    Restart=always
    RestartSec=10

    [Install]
    WantedBy=multi-user.target
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import shutil
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

try:
    import psutil
except ImportError:
    psutil = None  # type: ignore[assignment]

try:
    import requests as _requests_lib
except ImportError:
    _requests_lib = None  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Logging setup (Configuración de logging)
# ---------------------------------------------------------------------------

LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / "watchdog_daemon.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("centinel.watchdog_daemon")


# ---------------------------------------------------------------------------
# Configuration (Configuración)
# ---------------------------------------------------------------------------

_CONFIG_PATH = Path("command_center/config.yaml")


@dataclass
class DaemonConfig:
    """Configuration for the watchdog daemon.
    (Configuración del daemon watchdog.)

    All values have safe defaults and are overridden from config.yaml →
    resilience section when present.
    (Todos los valores tienen defaults seguros y se sobrescriben desde
    config.yaml → sección resilience cuando está presente.)
    """

    # Check interval in seconds (Intervalo de chequeo en segundos)
    check_interval_seconds: int = 30

    # Cooldown between corrective actions to prevent restart storms
    # (Cooldown entre acciones correctivas para prevenir tormentas de reinicio)
    cooldown_seconds: int = 120

    # Consecutive failures before taking action (Fallos consecutivos antes de actuar)
    failure_threshold: int = 3

    # System resource thresholds (Umbrales de recursos del sistema)
    cpu_threshold: float = 90.0
    memory_threshold: float = 90.0
    disk_threshold: float = 95.0

    # CNE endpoint to ping for reachability (Endpoint CNE para verificar alcanzabilidad)
    cne_ping_url: str = ""
    cne_ping_timeout: int = 10

    # Pipeline process identifiers (Identificadores del proceso del pipeline)
    pipeline_match: tuple[str, ...] = ("scripts/run_pipeline.py",)
    pipeline_command: tuple[str, ...] = ("python", "scripts/run_pipeline.py")

    # Paths to clean on proxy/cache reset (Rutas a limpiar en reset de proxies/cache)
    proxy_state_path: str = "data/temp/proxy_state.json"
    cache_paths: tuple[str, ...] = ("data/temp/",)

    # Temp lock files to clean on stuck detection (Archivos lock a limpiar)
    lock_files: tuple[str, ...] = (
        "data/temp/pipeline.lock",
        "data/temp/stuck.lock",
    )

    # Enable/disable the daemon entirely (Habilitar/deshabilitar el daemon)
    enabled: bool = True


def _load_daemon_config() -> DaemonConfig:
    """Load daemon config from config.yaml → resilience section.
    (Carga configuración del daemon desde config.yaml → sección resilience.)
    """
    cfg = DaemonConfig()
    if not _CONFIG_PATH.exists():
        return cfg

    try:
        raw = yaml.safe_load(_CONFIG_PATH.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        logger.warning("daemon_config_load_failed error=%s", exc)
        return cfg

    res = raw.get("resilience", {})
    if not isinstance(res, dict):
        return cfg

    # Map config keys to DaemonConfig fields (Mapear claves de config a campos)
    dos = res.get("dos_thresholds", {})
    if isinstance(dos, dict):
        cfg.cpu_threshold = float(dos.get("cpu", cfg.cpu_threshold))
        cfg.memory_threshold = float(dos.get("memory", cfg.memory_threshold))
        cfg.disk_threshold = float(dos.get("disk", cfg.disk_threshold))

    wd = res.get("watchdog_daemon", {})
    if isinstance(wd, dict):
        cfg.check_interval_seconds = int(wd.get("check_interval_seconds", cfg.check_interval_seconds))
        cfg.cooldown_seconds = int(wd.get("cooldown_seconds", cfg.cooldown_seconds))
        cfg.failure_threshold = int(wd.get("failure_threshold", cfg.failure_threshold))
        cfg.enabled = bool(wd.get("enabled", cfg.enabled))

    # CNE ping URL from endpoints (URL de ping CNE desde endpoints)
    endpoints = raw.get("endpoints", {})
    if isinstance(endpoints, dict) and not cfg.cne_ping_url:
        cfg.cne_ping_url = endpoints.get("nacional", "")

    return cfg


# ---------------------------------------------------------------------------
# Diagnostic checks (Chequeos de diagnóstico)
# ---------------------------------------------------------------------------

@dataclass
class DiagnosticResult:
    """Result of a single diagnostic check.
    (Resultado de un chequeo de diagnóstico individual.)
    """
    name: str
    ok: bool
    detail: str
    value: float | None = None


def check_cpu(cfg: DaemonConfig) -> DiagnosticResult:
    """Check CPU usage against threshold.
    (Verificar uso de CPU contra umbral.)
    """
    if psutil is None:
        return DiagnosticResult("cpu", True, "psutil_not_installed — skipped (omitido)")
    pct = psutil.cpu_percent(interval=1)
    ok = pct < cfg.cpu_threshold
    return DiagnosticResult("cpu", ok, f"cpu={pct:.1f}% threshold={cfg.cpu_threshold}%", pct)


def check_memory(cfg: DaemonConfig) -> DiagnosticResult:
    """Check memory usage against threshold.
    (Verificar uso de memoria contra umbral.)
    """
    if psutil is None:
        return DiagnosticResult("memory", True, "psutil_not_installed — skipped (omitido)")
    mem = psutil.virtual_memory()
    ok = mem.percent < cfg.memory_threshold
    return DiagnosticResult("memory", ok, f"mem={mem.percent:.1f}% threshold={cfg.memory_threshold}%", mem.percent)


def check_disk(cfg: DaemonConfig) -> DiagnosticResult:
    """Check disk usage against threshold.
    (Verificar uso de disco contra umbral.)
    """
    if psutil is None:
        return DiagnosticResult("disk", True, "psutil_not_installed — skipped (omitido)")
    disk = psutil.disk_usage("/")
    ok = disk.percent < cfg.disk_threshold
    return DiagnosticResult("disk", ok, f"disk={disk.percent:.1f}% threshold={cfg.disk_threshold}%", disk.percent)


def check_cne_reachability(cfg: DaemonConfig) -> DiagnosticResult:
    """Ping the CNE endpoint to verify it's reachable.
    (Ping al endpoint CNE para verificar que es alcanzable.)
    """
    if not cfg.cne_ping_url:
        return DiagnosticResult("cne_ping", True, "no_url_configured — skipped (omitido)")
    if _requests_lib is None:
        return DiagnosticResult("cne_ping", True, "requests_not_installed — skipped (omitido)")
    try:
        resp = _requests_lib.head(cfg.cne_ping_url, timeout=cfg.cne_ping_timeout, allow_redirects=True)
        ok = resp.status_code < 500
        return DiagnosticResult("cne_ping", ok, f"status={resp.status_code} url={cfg.cne_ping_url}")
    except _requests_lib.RequestException as exc:
        return DiagnosticResult("cne_ping", False, f"unreachable error={exc}")


def check_pipeline_alive(cfg: DaemonConfig) -> DiagnosticResult:
    """Check if the pipeline process is running.
    (Verificar si el proceso del pipeline está corriendo.)
    """
    if psutil is None:
        return DiagnosticResult("pipeline", True, "psutil_not_installed — skipped (omitido)")
    for proc in psutil.process_iter(["pid", "cmdline"]):
        cmdline = " ".join(proc.info.get("cmdline") or [])
        if any(match in cmdline for match in cfg.pipeline_match):
            return DiagnosticResult("pipeline", True, f"running pid={proc.pid}")
    return DiagnosticResult("pipeline", False, "pipeline_not_found")


def run_all_diagnostics(cfg: DaemonConfig) -> list[DiagnosticResult]:
    """Run all diagnostic checks and return results.
    (Ejecutar todos los chequeos de diagnóstico y retornar resultados.)
    """
    return [
        check_cpu(cfg),
        check_memory(cfg),
        check_disk(cfg),
        check_cne_reachability(cfg),
        check_pipeline_alive(cfg),
    ]


# ---------------------------------------------------------------------------
# Corrective actions (Acciones correctivas)
# ---------------------------------------------------------------------------

def reset_proxy_state(cfg: DaemonConfig) -> None:
    """Clear stale proxy state to force rotation.
    (Limpiar estado de proxy obsoleto para forzar rotación.)
    """
    proxy_path = Path(cfg.proxy_state_path)
    if proxy_path.exists():
        proxy_path.unlink()
        logger.info("proxy_state_reset path=%s", proxy_path)


def clear_caches(cfg: DaemonConfig) -> None:
    """Remove temp cache files (not data files).
    (Remover archivos de cache temporal — no archivos de datos.)
    """
    for cache_dir_str in cfg.cache_paths:
        cache_dir = Path(cache_dir_str)
        if not cache_dir.exists() or not cache_dir.is_dir():
            continue
        for item in cache_dir.iterdir():
            # Only remove temp/cache files, never data
            # (Solo remover archivos temp/cache, nunca datos)
            if item.suffix in (".tmp", ".cache", ".lock"):
                try:
                    item.unlink()
                    logger.info("cache_cleared file=%s", item)
                except OSError as exc:
                    logger.warning("cache_clear_failed file=%s error=%s", item, exc)


def remove_stale_locks(cfg: DaemonConfig) -> None:
    """Remove stale lock files that may block the pipeline.
    (Remover archivos lock obsoletos que puedan bloquear el pipeline.)
    """
    for lock_path_str in cfg.lock_files:
        lock = Path(lock_path_str)
        if lock.exists():
            lock.unlink()
            logger.info("stale_lock_removed path=%s", lock)


def restart_pipeline(cfg: DaemonConfig) -> bool:
    """Terminate and restart the pipeline process.
    (Terminar y reiniciar el proceso del pipeline.)

    Uses graceful SIGTERM first, escalates to SIGKILL after 15 seconds.
    (Usa SIGTERM graceful primero, escala a SIGKILL después de 15 segundos.)
    """
    if psutil is None:
        logger.warning("restart_skipped reason=psutil_not_installed")
        return False

    # Find and terminate (Encontrar y terminar)
    killed = False
    for proc in psutil.process_iter(["pid", "cmdline"]):
        cmdline = " ".join(proc.info.get("cmdline") or [])
        if any(match in cmdline for match in cfg.pipeline_match):
            try:
                proc.terminate()
                logger.info("pipeline_terminated pid=%s", proc.pid)
                killed = True
            except psutil.Error as exc:
                logger.warning("pipeline_terminate_failed pid=%s error=%s", proc.pid, exc)

    if killed:
        time.sleep(5)
        # SIGKILL any survivors (Enviar SIGKILL a sobrevivientes)
        for proc in psutil.process_iter(["pid", "cmdline"]):
            cmdline = " ".join(proc.info.get("cmdline") or [])
            if any(match in cmdline for match in cfg.pipeline_match):
                try:
                    proc.kill()
                    logger.warning("pipeline_force_killed pid=%s", proc.pid)
                except psutil.Error:
                    pass

    # Remove locks before restart (Remover locks antes de reiniciar)
    remove_stale_locks(cfg)

    # Start fresh (Iniciar de nuevo)
    try:
        subprocess.Popen(list(cfg.pipeline_command))  # noqa: S603
        logger.info("pipeline_restarted cmd=%s", cfg.pipeline_command)
        return True
    except OSError as exc:
        logger.error("pipeline_restart_failed error=%s", exc)
        return False


def execute_healing(cfg: DaemonConfig, failures: list[DiagnosticResult]) -> None:
    """Execute the full healing sequence based on diagnostic failures.
    (Ejecutar la secuencia completa de curación basada en fallos diagnósticos.)

    Order: reset proxies → clear caches → remove locks → restart pipeline.
    (Orden: reset proxies → limpiar caches → remover locks → reiniciar pipeline.)
    """
    failure_names = {f.name for f in failures}
    logger.warning(
        "healing_triggered failures=%s",
        ", ".join(f"{f.name}: {f.detail}" for f in failures),
    )

    # Always reset proxies and caches on any failure
    # (Siempre resetear proxies y caches en cualquier fallo)
    reset_proxy_state(cfg)
    clear_caches(cfg)

    # Restart pipeline if it's dead or resources are critical
    # (Reiniciar pipeline si está muerto o los recursos son críticos)
    if "pipeline" in failure_names or "cpu" in failure_names or "memory" in failure_names:
        restart_pipeline(cfg)


# ---------------------------------------------------------------------------
# Daemon state (Estado del daemon)
# ---------------------------------------------------------------------------

@dataclass
class DaemonState:
    """Tracks consecutive failures and cooldown timing.
    (Rastrea fallos consecutivos y timing de cooldown.)
    """
    consecutive_failures: int = 0
    last_action_ts: float = 0.0
    total_healings: int = 0
    started_at: str = ""

    def can_act(self, cooldown: int) -> bool:
        """Check if the cooldown period has elapsed since last action.
        (Verificar si el período de cooldown ha pasado desde la última acción.)
        """
        return (time.monotonic() - self.last_action_ts) > cooldown

    def record_action(self) -> None:
        """Record that a corrective action was taken.
        (Registrar que se tomó una acción correctiva.)
        """
        self.last_action_ts = time.monotonic()
        self.total_healings += 1
        self.consecutive_failures = 0


# ---------------------------------------------------------------------------
# DoS simulation (Simulación DoS)
# ---------------------------------------------------------------------------

def simulate_dos(cfg: DaemonConfig) -> None:
    """Simulate high resource usage to test the healing pipeline.
    (Simular alto uso de recursos para probar el pipeline de curación.)

    This does NOT actually consume resources — it fakes diagnostic results
    to trigger the full healing sequence including Telegram alerts.
    (Esto NO consume recursos realmente — falsifica resultados de diagnóstico
    para disparar la secuencia completa de curación incluyendo alertas Telegram.)
    """
    logger.warning("=== DoS SIMULATION STARTED (SIMULACIÓN DoS INICIADA) ===")

    fake_failures = [
        DiagnosticResult("cpu", False, "SIMULATED cpu=95.0% threshold=90.0%", 95.0),
        DiagnosticResult("memory", False, "SIMULATED mem=92.0% threshold=90.0%", 92.0),
        DiagnosticResult("cne_ping", False, "SIMULATED unreachable timeout=10s"),
        DiagnosticResult("pipeline", False, "SIMULATED pipeline_not_found"),
    ]

    # Log diagnostics (Loguear diagnósticos)
    for result in fake_failures:
        logger.warning("SIMULATED diagnostic: %s ok=%s detail=%s", result.name, result.ok, result.detail)

    # Attempt Telegram alert (Intentar alerta Telegram)
    _try_send_telegram_alert(fake_failures, simulated=True)

    # Show what healing *would* do (Mostrar qué haría la curación)
    logger.info("healing_sequence: reset_proxy → clear_caches → remove_locks → restart_pipeline")
    logger.info("(In simulation mode, no actual changes are made)")
    logger.info("(En modo simulación, no se realizan cambios reales)")

    logger.warning("=== DoS SIMULATION COMPLETE (SIMULACIÓN DoS COMPLETA) ===")


# ---------------------------------------------------------------------------
# Telegram integration (Integración Telegram)
# ---------------------------------------------------------------------------

def _try_send_telegram_alert(
    failures: list[DiagnosticResult],
    simulated: bool = False,
) -> None:
    """Send a Telegram alert with diagnostic details.
    (Enviar alerta Telegram con detalles de diagnóstico.)

    Uses the existing monitoring.alerts module if available.
    (Usa el módulo monitoring.alerts existente si está disponible.)
    """
    try:
        from monitoring.alerts import dispatch_alert
    except ImportError:
        logger.info("telegram_alert_skipped reason=monitoring.alerts_not_importable")
        return

    prefix = "[SIMULATION] " if simulated else ""
    lines = [f"{prefix}WATCHDOG DAEMON — {'DoS Simulation' if simulated else 'Failures Detected'}"]
    lines.append(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    lines.append("")

    for f in failures:
        status = "FAIL" if not f.ok else "OK"
        lines.append(f"  [{status}] {f.name}: {f.detail}")

    if psutil:
        lines.append("")
        lines.append(f"System: CPU={psutil.cpu_percent():.1f}% MEM={psutil.virtual_memory().percent:.1f}%")

    message = "\n".join(lines)
    dispatch_alert("CRITICAL", message)


# ---------------------------------------------------------------------------
# Main loop (Bucle principal)
# ---------------------------------------------------------------------------

_RUNNING = True


def _handle_signal(signum: int, frame: Any) -> None:
    """Handle SIGTERM/SIGINT for graceful shutdown.
    (Manejar SIGTERM/SIGINT para apagado graceful.)
    """
    global _RUNNING
    logger.info("daemon_shutdown_signal received=%s", signal.Signals(signum).name)
    _RUNNING = False


def daemon_loop(cfg: DaemonConfig) -> None:
    """Main daemon loop: diagnose → heal → cooldown → repeat.
    (Bucle principal del daemon: diagnosticar → curar → cooldown → repetir.)
    """
    state = DaemonState(started_at=datetime.now(timezone.utc).isoformat())

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    logger.info(
        "daemon_started interval=%ds cooldown=%ds cpu_thresh=%.0f%% mem_thresh=%.0f%%",
        cfg.check_interval_seconds,
        cfg.cooldown_seconds,
        cfg.cpu_threshold,
        cfg.memory_threshold,
    )

    while _RUNNING:
        try:
            results = run_all_diagnostics(cfg)

            # Log each result (Loguear cada resultado)
            for r in results:
                level = logging.INFO if r.ok else logging.WARNING
                logger.log(level, "diagnostic %s ok=%s detail=%s", r.name, r.ok, r.detail)

            failures = [r for r in results if not r.ok]

            if failures:
                state.consecutive_failures += 1
                logger.warning(
                    "failures_detected count=%d consecutive=%d threshold=%d",
                    len(failures),
                    state.consecutive_failures,
                    cfg.failure_threshold,
                )

                # Act only after threshold consecutive failures AND cooldown elapsed
                # (Actuar solo después de umbral de fallos consecutivos Y cooldown transcurrido)
                if state.consecutive_failures >= cfg.failure_threshold and state.can_act(cfg.cooldown_seconds):
                    _try_send_telegram_alert(failures)
                    execute_healing(cfg, failures)
                    state.record_action()
                    logger.info(
                        "healing_complete total_healings=%d",
                        state.total_healings,
                    )
                elif not state.can_act(cfg.cooldown_seconds):
                    remaining = cfg.cooldown_seconds - (time.monotonic() - state.last_action_ts)
                    logger.info("cooldown_active remaining=%.0fs (waiting / esperando)", remaining)
            else:
                # Reset consecutive counter on healthy cycle
                # (Resetear contador consecutivo en ciclo saludable)
                if state.consecutive_failures > 0:
                    logger.info("system_recovered after=%d consecutive failures", state.consecutive_failures)
                state.consecutive_failures = 0

        except Exception as exc:
            logger.error("daemon_loop_error error=%s", exc, exc_info=True)

        time.sleep(cfg.check_interval_seconds)

    # Graceful shutdown (Apagado graceful)
    logger.info("daemon_stopped total_healings=%d uptime_since=%s", state.total_healings, state.started_at)
    _try_send_telegram_alert(
        [DiagnosticResult("shutdown", False, "daemon_stopped_gracefully")],
    )


# ---------------------------------------------------------------------------
# CLI entry point (Punto de entrada CLI)
# ---------------------------------------------------------------------------

def main() -> None:
    """Entry point for the watchdog daemon.
    (Punto de entrada del daemon watchdog.)

    Usage:
        python scripts/watchdog_daemon.py                  # Normal mode
        python scripts/watchdog_daemon.py --simulate-dos   # DoS test
        poetry run watchdog-daemon --simulate-dos           # Via Poetry
    """
    parser = argparse.ArgumentParser(
        description="C.E.N.T.I.N.E.L. Watchdog Daemon — obsessive self-healing monitor",
    )
    parser.add_argument(
        "--simulate-dos",
        action="store_true",
        help="Simulate a DoS scenario to test healing pipeline (Simular escenario DoS para probar pipeline de curación)",
    )
    args = parser.parse_args()

    cfg = _load_daemon_config()

    if args.simulate_dos:
        simulate_dos(cfg)
        return

    if not cfg.enabled:
        logger.info("daemon_disabled — set resilience.watchdog_daemon.enabled: true in config.yaml")
        return

    daemon_loop(cfg)


if __name__ == "__main__":
    main()
