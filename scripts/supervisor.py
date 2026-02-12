"""Supervisor wrapper for defensive restarts.

Wrapper supervisor para reinicios defensivos.
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
import time
from pathlib import Path

import psutil

from core.security import SecurityConfig, random_cooldown_seconds, send_admin_alert

CONFIG_PATH = Path("command_center/security_config.yaml")
DEFAULT_COMMAND = [sys.executable, "scripts/run_pipeline.py"]


def _load_recent_logs(path: Path, limit: int = 40) -> list[str]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    return lines[-limit:]


def _host_still_hostile(config: SecurityConfig) -> bool:
    cpu = psutil.cpu_percent(interval=0.3)
    mem = psutil.virtual_memory().percent
    return cpu > config.cpu_threshold_percent or mem > config.memory_threshold_percent


def run_supervisor(command: list[str], logger: logging.Logger) -> int:
    """Run pipeline with randomized cooldown and bounded retries.

    Ejecuta pipeline con cooldown aleatorio y reintentos acotados.
    """
    config = SecurityConfig.from_yaml(CONFIG_PATH)
    failures = 0
    attempt = 0

    while attempt < config.max_restart_attempts:
        attempt += 1
        started = time.time()
        logger.info("supervisor_launch attempt=%s command=%s", attempt, command)
        proc = subprocess.run(command, check=False)
        runtime = time.time() - started

        flag = Path(config.defensive_flag_file)
        defensive_shutdown = flag.exists()

        if proc.returncode == 0 and not defensive_shutdown:
            logger.info("supervisor_exit_clean runtime=%.1fs", runtime)
            return 0

        if runtime < 300:
            failures += 1

        multiplier = 2 ** max(failures - 1, 0)
        if _host_still_hostile(config):
            multiplier *= 2

        cooldown = random_cooldown_seconds(config.cooldown_min_minutes, config.cooldown_max_minutes, multiplier)
        logger.warning(
            "supervisor_cooldown attempt=%s failures=%s cooldown_seconds=%s defensive=%s return_code=%s",
            attempt,
            failures,
            cooldown,
            defensive_shutdown,
            proc.returncode,
        )
        time.sleep(cooldown)

    triggers: list[str] = ["max_retries_reached"]
    state_dir = "unknown"
    flag = Path(config.defensive_flag_file)
    if flag.exists():
        try:
            payload = json.loads(flag.read_text(encoding="utf-8"))
            triggers = payload.get("triggers", triggers)
            state_dir = payload.get("state_dir", state_dir)
        except json.JSONDecodeError:
            pass

    send_admin_alert(
        config=config,
        triggers=triggers,
        recent_logs=_load_recent_logs(Path("logs/centinel.log")),
        state_path=state_dir,
    )
    return 1


def main() -> int:
    """Parse args and start supervisor.

    Parsea argumentos e inicia supervisor.
    """
    parser = argparse.ArgumentParser(description="Defensive supervisor for Centinel pipeline")
    parser.add_argument("--", dest="sep", nargs="?")
    parser.add_argument("command", nargs="*")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logger = logging.getLogger("centinel.supervisor")

    command = args.command if args.command else DEFAULT_COMMAND
    return run_supervisor(command, logger)


if __name__ == "__main__":
    raise SystemExit(main())
