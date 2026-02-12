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

from core.advanced_security import AlertManager
from core.security import SecurityConfig, send_admin_alert

DEFAULT_COMMAND = [sys.executable, "scripts/run_pipeline.py"]
CONFIG_PATH = Path("command_center/security_config.yaml")
CLEAN_SHUTDOWN_FLAG = Path("/tmp/clean_shutdown.flag")


def _host_still_hostile(config: SecurityConfig) -> bool:
    return False


def random_cooldown_seconds(min_minutes: int, max_minutes: int, multiplier: float = 1.0) -> int:
    base = random.uniform(min_minutes * 60, max_minutes * 60)
    return int(base * multiplier)


def run_supervisor(command: list[str], logger: logging.Logger) -> int:
    """Run main process and restart on forced exits.

    Ejecuta proceso principal y reinicia en salidas forzadas.
    """
    cfg = SecurityConfig.from_yaml(CONFIG_PATH)
    retries = 0
    alerts = AlertManager()

    while retries < cfg.max_restart_attempts:
        logger.info("supervisor_launch command=%s", command)
        proc = subprocess.run(command, check=False)
        returncode = proc.returncode

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
        cooldown = random_cooldown_seconds(max(20, cfg.cooldown_min_minutes), max(90, cfg.cooldown_max_minutes), multiplier)
        cooldown = min(cooldown, 6 * 3600)
        reason = signal.Signals(-returncode).name if returncode < 0 else f"exit_{returncode}"

        logger.warning("supervisor_restart retries=%s reason=%s cooldown=%ss", retries, reason, cooldown)
        alerts.send(3, "supervisor_forced_restart", {"reason": reason, "retries": retries, "cooldown_seconds": cooldown})
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
