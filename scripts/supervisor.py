# Supervisor Module
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

"""External defensive supervisor wrapper.

Supervisor externo defensivo.
"""

from __future__ import annotations

import argparse
import logging
import random
import signal
import subprocess
import sys
import time
from pathlib import Path

import psutil

from core.advanced_security import AlertManager
from core.security import SecurityConfig, send_admin_alert

DEFAULT_COMMAND = [sys.executable, "scripts/run_pipeline.py"]
CONFIG_PATH = Path("command_center/security_config.yaml")
CLEAN_SHUTDOWN_FLAG = Path("/tmp/clean_shutdown.flag")  # nosec B108 - ephemeral flag, no sensitive data
OOM_PERSIST_FILE = Path("data/backups/supervisor_pre_oom.json")


def _host_still_hostile(config: SecurityConfig) -> bool:
    """Check coarse hostile signals before restart.

    Verifica señales hostiles básicas antes de reiniciar.
    """
    cpu = psutil.cpu_percent(interval=0.1)
    mem = psutil.virtual_memory().percent
    return cpu > config.cpu_threshold_percent or mem > config.memory_threshold_percent


def random_cooldown_seconds(min_minutes: int, max_minutes: int, multiplier: float = 1.0) -> int:
    base = random.uniform(min_minutes * 60, max_minutes * 60)
    return int(base * multiplier)


def _too_many_python_workers(max_workers: int = 8) -> bool:
    """Prevent restart storms with too many python worker processes.

    Previene tormentas de reinicio con demasiados procesos python.
    """
    workers = 0
    for proc in psutil.process_iter(attrs=["name", "cmdline"]):
        cmdline = " ".join(proc.info.get("cmdline") or [])
        name = (proc.info.get("name") or "").lower()
        if "python" in name and "run_pipeline.py" in cmdline:
            workers += 1
    return workers >= max_workers


def run_supervisor(command: list[str], logger: logging.Logger) -> int:
    """Run main process and restart on forced exits.

    Ejecuta proceso principal y reinicia en salidas forzadas.
    """
    cfg = SecurityConfig.from_yaml(CONFIG_PATH)
    retries = 0
    alerts = AlertManager()

    while retries < cfg.max_restart_attempts:
        if _too_many_python_workers():
            logger.error("supervisor_concurrency_guard_triggered")
            alerts.send(3, "supervisor_concurrency_guard", {"max_workers": 8})
            time.sleep(30)
            continue

        logger.info("supervisor_launch command=%s", command)
        proc = subprocess.run(command, check=False)
        returncode = proc.returncode

        if returncode in {-9, -15}:
            OOM_PERSIST_FILE.parent.mkdir(parents=True, exist_ok=True)
            OOM_PERSIST_FILE.write_text(
                f'{{"reason":"signal_{abs(returncode)}","timestamp":{int(time.time())}}}',
                encoding="utf-8",
            )

        clean_shutdown = CLEAN_SHUTDOWN_FLAG.exists()
        if clean_shutdown:
            CLEAN_SHUTDOWN_FLAG.unlink(missing_ok=True)

        if returncode == 0 and clean_shutdown:
            logger.info("supervisor_clean_shutdown")
            return 0

        retries += 1
        multiplier = max(1, 2 ** (retries - 1))
        if _host_still_hostile(cfg):
            multiplier *= 2
        cooldown = random_cooldown_seconds(
            max(20, cfg.cooldown_min_minutes), max(90, cfg.cooldown_max_minutes), multiplier
        )
        cooldown = min(cooldown, 6 * 3600)
        reason = signal.Signals(-returncode).name if returncode < 0 else f"exit_{returncode}"

        logger.warning("supervisor_restart retries=%s reason=%s cooldown=%ss", retries, reason, cooldown)
        alerts.send(
            3, "supervisor_forced_restart", {"reason": reason, "retries": retries, "cooldown_seconds": cooldown}
        )
        time.sleep(cooldown)

    send_admin_alert(config=cfg, triggers=["supervisor_max_retries"], recent_logs=[], state_path="unknown")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Centinel external defensive supervisor")
    parser.add_argument("command", nargs="*", help="Optional command override")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    command = args.command or DEFAULT_COMMAND
    return run_supervisor(command, logging.getLogger("centinel.supervisor"))


if __name__ == "__main__":
    raise SystemExit(main())
