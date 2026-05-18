#!/usr/bin/env bash
# Gestor de servicio Centinel Engine / Centinel Engine service manager.
#
# Uso / Usage:
#   scripts/centinel_service.sh start   — Iniciar pipeline en segundo plano
#   scripts/centinel_service.sh stop    — Detener pipeline
#   scripts/centinel_service.sh restart — Reiniciar
#   scripts/centinel_service.sh status  — Ver estado
#   scripts/centinel_service.sh logs    — Ver logs en tiempo real
#
# No requiere Docker ni systemd.
# Does not require Docker or systemd.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

PID_FILE=".centinel.pid"
WATCHDOG_PID_FILE=".centinel-watchdog.pid"
LOG_FILE="logs/pipeline.log"
WATCHDOG_LOG="logs/watchdog.log"

mkdir -p logs

# ── Color helpers ─────────────────────────────────────────────────────────────
if [ -t 1 ]; then
  BOLD='\033[1m'; GREEN='\033[32m'; YELLOW='\033[33m'; RED='\033[31m'; CYAN='\033[36m'; RESET='\033[0m'
else
  BOLD=''; GREEN=''; YELLOW=''; RED=''; CYAN=''; RESET=''
fi

ok()   { printf "  ${GREEN}✓${RESET} %s\n" "$1"; }
warn() { printf "  ${YELLOW}→${RESET} %s\n" "$1"; }
fail() { printf "  ${RED}✗${RESET} %s\n" "$1"; }

# ── Detect run prefix (poetry or direct python) ───────────────────────────────
if command -v poetry >/dev/null 2>&1 && [ -f "pyproject.toml" ]; then
  RUN="poetry run"
else
  # Try .venv if it exists
  if [ -f ".venv/bin/python" ]; then
    . .venv/bin/activate 2>/dev/null || true
  fi
  RUN=""
fi

# ── Load .env if present ──────────────────────────────────────────────────────
if [ -f ".env" ]; then
  set -o allexport
  # shellcheck disable=SC1091
  source .env 2>/dev/null || true
  set +o allexport
fi

export PYTHONPATH="${REPO_ROOT}/src:${PYTHONPATH:-}"
export CENTINEL_MODE="${CENTINEL_MODE:-monitoring}"

# ── is_running helper ─────────────────────────────────────────────────────────
is_running() {
  local pid_file="$1"
  [ -f "$pid_file" ] && kill -0 "$(cat "$pid_file")" 2>/dev/null
}

# ── Commands ──────────────────────────────────────────────────────────────────

cmd_start() {
  printf "\n${BOLD}Iniciando / Starting Centinel Engine${RESET}\n"
  printf "  CENTINEL_MODE=%s\n\n" "$CENTINEL_MODE"

  if is_running "$PID_FILE"; then
    warn "Pipeline ya está corriendo (PID: $(cat "$PID_FILE"))."
    warn "Pipeline already running. Use 'make restart' to restart."
    return 0
  fi

  # Start pipeline with scheduler
  nohup $RUN python scripts/run_pipeline.py --run-now \
    >> "$LOG_FILE" 2>&1 &
  echo $! > "$PID_FILE"
  ok "Pipeline iniciado (PID: $(cat "$PID_FILE"))"
  ok "Logs: $LOG_FILE"

  # Start watchdog if it exists
  if [ -f "scripts/watchdog_daemon.py" ]; then
    if is_running "$WATCHDOG_PID_FILE"; then
      warn "Watchdog ya está corriendo."
    else
      nohup $RUN python scripts/watchdog_daemon.py \
        >> "$WATCHDOG_LOG" 2>&1 &
      echo $! > "$WATCHDOG_PID_FILE"
      ok "Watchdog iniciado (PID: $(cat "$WATCHDOG_PID_FILE"))"
    fi
  fi

  printf "\n  ${CYAN}make status${RESET} → verificar estado\n"
  printf "  ${CYAN}make logs${RESET}   → ver logs en tiempo real\n\n"
}

cmd_stop() {
  printf "\n${BOLD}Deteniendo / Stopping Centinel Engine${RESET}\n\n"
  local stopped=0

  if is_running "$PID_FILE"; then
    kill "$(cat "$PID_FILE")" 2>/dev/null && ok "Pipeline detenido." || fail "Error deteniendo pipeline."
    rm -f "$PID_FILE"
    stopped=1
  else
    warn "Pipeline no estaba corriendo."
  fi

  if is_running "$WATCHDOG_PID_FILE"; then
    kill "$(cat "$WATCHDOG_PID_FILE")" 2>/dev/null && ok "Watchdog detenido." || fail "Error deteniendo watchdog."
    rm -f "$WATCHDOG_PID_FILE"
    stopped=1
  fi

  [ "$stopped" -eq 0 ] && warn "No había procesos activos." || true
  echo
}

cmd_restart() {
  cmd_stop
  sleep 1
  cmd_start
}

cmd_status() {
  printf "\n${BOLD}Estado / Status — Centinel Engine${RESET}\n\n"

  # Pipeline
  if is_running "$PID_FILE"; then
    ok "Pipeline CORRIENDO / RUNNING (PID: $(cat "$PID_FILE"))"
  else
    fail "Pipeline DETENIDO / STOPPED"
  fi

  # Watchdog
  if is_running "$WATCHDOG_PID_FILE"; then
    ok "Watchdog CORRIENDO / RUNNING (PID: $(cat "$WATCHDOG_PID_FILE"))"
  else
    warn "Watchdog no está corriendo."
  fi

  # Last log activity
  if [ -f "$LOG_FILE" ]; then
    printf "\n  Últimas líneas del log / Last log lines:\n"
    printf "  %s\n" "$(tail -5 "$LOG_FILE" | sed 's/^/  /')"
  fi

  # Recent alerts
  if [ -f "data/alerts.json" ]; then
    alert_count=$(python3 -c "import json; d=json.load(open('data/alerts.json')); print(len(d))" 2>/dev/null || echo "?")
    printf "\n  Alertas recientes / Recent alerts: %s\n" "$alert_count"
  fi

  # Master switch
  if [ -f "command_center/config.yaml" ]; then
    switch=$(grep -m1 '^master_switch:' command_center/config.yaml | sed 's/master_switch: *//; s/"//g' | tr -d '[:space:]')
    printf "  Master switch: ${BOLD}%s${RESET}\n" "$switch"
  fi

  echo
}

cmd_logs() {
  if [ ! -f "$LOG_FILE" ]; then
    warn "No hay log todavía. Inicia el pipeline con 'make start'."
    exit 0
  fi
  printf "\n  ${CYAN}Ctrl-C${RESET} para salir / to exit\n\n"
  tail -f "$LOG_FILE"
}

# ── Dispatch ──────────────────────────────────────────────────────────────────

case "${1:-help}" in
  start)   cmd_start ;;
  stop)    cmd_stop ;;
  restart) cmd_restart ;;
  status)  cmd_status ;;
  logs)    cmd_logs ;;
  *)
    printf "\nUso / Usage:\n"
    printf "  %s {start|stop|restart|status|logs}\n\n" "$0"
    exit 1
    ;;
esac
