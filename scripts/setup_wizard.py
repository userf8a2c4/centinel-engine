#!/usr/bin/env python3
"""Asistente de configuración interactivo para Centinel Engine.
Interactive configuration wizard for Centinel Engine.

Uso / Usage:
    python scripts/setup_wizard.py
    make wizard
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_YAML = REPO_ROOT / "command_center" / "config.yaml"
ENV_FILE = REPO_ROOT / ".env"
ENV_EXAMPLE = REPO_ROOT / ".env.example"

# ── Terminal helpers ──────────────────────────────────────────────────────────

BOLD = "\033[1m"
GREEN = "\033[32m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
RESET = "\033[0m"

_NO_COLOR = not sys.stdout.isatty() or os.environ.get("NO_COLOR")


def _c(color: str, text: str) -> str:
    return text if _NO_COLOR else f"{color}{text}{RESET}"


def _header(title: str) -> None:
    width = 62
    print()
    print(_c(CYAN, "─" * width))
    print(_c(BOLD, f"  {title}"))
    print(_c(CYAN, "─" * width))


def _ok(msg: str) -> None:
    print(f"  {_c(GREEN, '✓')} {msg}")


def _note(msg: str) -> None:
    print(f"  {_c(YELLOW, '→')} {msg}")


# ── Input helpers ─────────────────────────────────────────────────────────────


def _ask(prompt: str, default: str = "", required: bool = False) -> str:
    if default:
        full_prompt = f"  {prompt} [{_c(CYAN, default)}]: "
    else:
        full_prompt = f"  {prompt}: "
    while True:
        try:
            value = input(full_prompt).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(0)
        if value:
            return value
        if default:
            return default
        if not required:
            return ""
        print(f"  {_c(YELLOW, 'Campo obligatorio / Required field.')}")


def _ask_yn(prompt: str, default: bool = True) -> bool:
    choices = "S/n" if default else "s/N"
    raw = _ask(f"{prompt} ({choices})", default="s" if default else "n")
    return raw.lower() in ("s", "si", "sí", "y", "yes", "1", "true")


def _ask_choice(prompt: str, choices: list[str], default: str) -> str:
    options = " / ".join(
        _c(BOLD, c) if c == default else c for c in choices
    )
    print(f"  {prompt}")
    print(f"    Opciones: {options}")
    while True:
        raw = _ask("Selección / Selection", default=default)
        if raw in choices:
            return raw
        opts_str = ", ".join(choices)
        print(f"  {_c(YELLOW, 'Opciones válidas: ' + opts_str)}")


# ── YAML key updater (preserves comments) ────────────────────────────────────


def _update_yaml_line(content: str, key: str, new_value: str) -> str:
    """Replace a top-level YAML key value, preserving inline comments."""
    pattern = rf'^({re.escape(key)}:\s*)("?[^#\n]*?)(\s*(?:#[^\n]*)?)\s*$'
    if '"' in new_value or ' ' in new_value:
        replacement = rf'\g<1>"{new_value}"\g<3>'
    else:
        replacement = rf'\g<1>{new_value}\g<3>'
    updated, count = re.subn(pattern, replacement, content, count=1, flags=re.MULTILINE)
    if count == 0:
        # Key not found — append it
        updated = content.rstrip() + f'\n{key}: "{new_value}"\n'
    return updated


# ── .env helpers ──────────────────────────────────────────────────────────────


def _load_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip()
    return env


def _save_env(path: Path, env: dict[str, str], example: Path) -> None:
    """Write .env preserving comments from .env.example where possible."""
    if example.exists():
        lines = example.read_text(encoding="utf-8").splitlines()
        written = set()
        result = []
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                k = stripped.split("=", 1)[0].strip()
                if k in env:
                    # Preserve inline comment if present
                    comment_part = ""
                    if "#" in stripped:
                        comment_part = "  " + stripped[stripped.index("#"):]
                    result.append(f"{k}={env[k]}{comment_part}")
                    written.add(k)
                    continue
            result.append(line)
        # Append keys not in the example
        for k, v in env.items():
            if k not in written:
                result.append(f"{k}={v}")
        path.write_text("\n".join(result) + "\n", encoding="utf-8")
    else:
        lines = [f"{k}={v}" for k, v in env.items()]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ── Main wizard ───────────────────────────────────────────────────────────────


def main() -> None:
    print()
    print(_c(BOLD, "=" * 62))
    print(_c(BOLD, "  CENTINEL ENGINE — Asistente de Configuración / Setup Wizard"))
    print(_c(BOLD, "=" * 62))
    print()
    print("  Configuración interactiva en ~3 minutos.")
    print("  Interactive setup in ~3 minutes.")
    print()
    print("  Presiona Enter para aceptar el valor por defecto [entre corchetes].")
    print("  Press Enter to accept the default value [in brackets].")

    # Check non-interactive
    if not sys.stdin.isatty():
        print()
        print(_c(YELLOW, "  Modo no-interactivo detectado. Usa los archivos directamente:"))
        print("    command_center/config.yaml  — configuración principal")
        print("    .env                        — variables de entorno")
        print()
        sys.exit(0)

    # Load existing state
    yaml_content = CONFIG_YAML.read_text(encoding="utf-8") if CONFIG_YAML.exists() else ""
    env = _load_env(ENV_FILE) if ENV_FILE.exists() else _load_env(ENV_EXAMPLE)

    # ── PASO 1: Endpoints CNE ─────────────────────────────────────────────────
    _header("PASO 1 / STEP 1: Endpoint principal del CNE")
    print("  La URL base para el API de resultados electorales.")
    print("  Base URL for the electoral results API.")
    print()

    # Extract current base_url from YAML
    m = re.search(r'^base_url:\s*"?([^"\n#]+)"?', yaml_content, re.MULTILINE)
    current_url = m.group(1).strip() if m else "https://resultadosgenerales2025.cne.hn"

    new_url = _ask("URL base / Base URL", default=current_url, required=True)
    if new_url != current_url:
        yaml_content = _update_yaml_line(yaml_content, "base_url", new_url)
        _ok(f"base_url actualizado / updated → {new_url}")
    else:
        _ok(f"base_url sin cambios / unchanged: {new_url}")

    # ── PASO 2: Modo operativo ────────────────────────────────────────────────
    _header("PASO 2 / STEP 2: Modo operativo / Operating mode")
    print("  maintenance → pruebas locales / local testing (sin alertas reales)")
    print("  monitoring  → monitoreo pasivo / passive monitoring")
    print("  election    → elecciones en vivo / live election (máxima seguridad)")
    print()

    current_mode = env.get("CENTINEL_MODE", "monitoring")
    new_mode = _ask_choice(
        "Modo / Mode:",
        choices=["maintenance", "monitoring", "election"],
        default=current_mode,
    )
    env["CENTINEL_MODE"] = new_mode
    _ok(f"CENTINEL_MODE={new_mode}")

    # ── PASO 3: Intervalo de captura ──────────────────────────────────────────
    _header("PASO 3 / STEP 3: Intervalo de captura / Polling interval")
    print("  Segundos entre capturas de datos del CNE.")
    print("  Seconds between CNE data captures.")
    print("  Recomendado en elecciones: 120 (2 min). Fuera: 300 (5 min).")
    print()

    current_interval = env.get("CENTINEL_POLL_INTERVAL", "120")
    new_interval = _ask("Intervalo en segundos / Interval in seconds", default=current_interval)
    if new_interval.isdigit():
        env["CENTINEL_POLL_INTERVAL"] = new_interval
        _ok(f"CENTINEL_POLL_INTERVAL={new_interval}s")
    else:
        _note("Valor no numérico ignorado / Non-numeric value ignored.")

    # ── PASO 4: Master switch ─────────────────────────────────────────────────
    _header("PASO 4 / STEP 4: Interruptor maestro / Master switch")
    print("  Controla si el pipeline corre automáticamente.")
    print("  Controls whether the pipeline runs automatically.")
    print()

    m_switch = re.search(r'^master_switch:\s*"?(\w+)"?', yaml_content, re.MULTILINE)
    current_switch = (m_switch.group(1) if m_switch else "ON").upper()
    activate = _ask_yn(
        "Activar el sistema (master_switch ON)?",
        default=(current_switch == "ON"),
    )
    new_switch = "ON" if activate else "OFF"
    yaml_content = _update_yaml_line(yaml_content, "master_switch", new_switch)
    _ok(f"master_switch={new_switch}")

    # ── PASO 5: Nivel de log ──────────────────────────────────────────────────
    _header("PASO 5 / STEP 5: Nivel de log / Log level")
    current_log = env.get("LOG_LEVEL", "INFO")
    new_log = _ask_choice(
        "Nivel / Level:",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=current_log,
    )
    env["LOG_LEVEL"] = new_log
    _ok(f"LOG_LEVEL={new_log}")

    # ── PASO 6: Opciones avanzadas (opcionales) ───────────────────────────────
    _header("PASO 6 / STEP 6: Servicios opcionales / Optional services")
    print("  Estos servicios mejoran el sistema pero no son obligatorios.")
    print("  These services enhance the system but are not required.")
    print()

    # Supabase
    has_supabase = bool(env.get("SUPABASE_URL", "").strip("https://PROYECTO.supabase.co"))
    if _ask_yn("¿Configurar Supabase (base de datos en la nube)?", default=has_supabase):
        url_s = _ask("SUPABASE_URL", default=env.get("SUPABASE_URL", ""))
        key_s = _ask("SUPABASE_SERVICE_ROLE_KEY", default=env.get("SUPABASE_SERVICE_ROLE_KEY", ""))
        anon_s = _ask("SUPABASE_ANON_KEY", default=env.get("SUPABASE_ANON_KEY", ""))
        if url_s:
            env["SUPABASE_URL"] = url_s
        if key_s:
            env["SUPABASE_SERVICE_ROLE_KEY"] = key_s
        if anon_s:
            env["SUPABASE_ANON_KEY"] = anon_s
        _ok("Supabase configurado")
    else:
        _note("Supabase omitido — el análisis local funciona sin él.")

    # GitHub token
    has_gh = bool(env.get("GITHUB_TOKEN", "").strip("ghp_..."))
    if _ask_yn("¿Configurar GitHub token (para publicación de emergencia)?", default=has_gh):
        gh_token = _ask("GITHUB_TOKEN", default=env.get("GITHUB_TOKEN", ""))
        gh_repo = _ask(
            "GITHUB_REPOSITORY",
            default=env.get("GITHUB_REPOSITORY", "userf8a2c4/centinel-engine"),
        )
        if gh_token:
            env["GITHUB_TOKEN"] = gh_token
        if gh_repo:
            env["GITHUB_REPOSITORY"] = gh_repo
        _ok("GitHub token configurado")
    else:
        _note("GitHub token omitido — la publicación de emergencia no estará disponible.")

    # OTS
    ots_raw = env.get("OTS_ENABLED", "false").lower()
    ots_on = ots_raw in ("true", "1", "yes")
    if _ask_yn("¿Activar anclaje Bitcoin/OpenTimestamps (prueba criptográfica de tiempo)?", default=ots_on):
        env["OTS_ENABLED"] = "true"
        _ok("OpenTimestamps activado")
    else:
        env["OTS_ENABLED"] = "false"
        _note("OpenTimestamps desactivado.")

    # ── Guardar cambios ───────────────────────────────────────────────────────
    _header("Guardando configuración / Saving configuration")

    if CONFIG_YAML.exists() or yaml_content:
        CONFIG_YAML.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_YAML.write_text(yaml_content, encoding="utf-8")
        _ok(f"YAML guardado / saved: {CONFIG_YAML.relative_to(REPO_ROOT)}")

    _save_env(ENV_FILE, env, ENV_EXAMPLE)
    _ok(f".env guardado / saved: {ENV_FILE.relative_to(REPO_ROOT)}")

    # ── Resumen y próximos pasos ──────────────────────────────────────────────
    print()
    print(_c(BOLD, "=" * 62))
    print(_c(BOLD, "  PRÓXIMOS PASOS / NEXT STEPS"))
    print(_c(BOLD, "=" * 62))
    print()
    print(f"  {_c(CYAN, 'make start')}     → Iniciar el pipeline (autónomo, cada hora)")
    print( "                  Start the pipeline (autonomous, every hour)")
    print()
    print(f"  {_c(CYAN, 'make status')}    → Ver si el pipeline está corriendo")
    print( "                  Check if the pipeline is running")
    print()
    print(f"  {_c(CYAN, 'make logs')}      → Ver logs en tiempo real")
    print( "                  View logs in real time")
    print()
    print(f"  {_c(CYAN, 'make pipeline')} → Ejecutar UNA vez (manual, sin scheduler)")
    print( "                  Run ONCE manually (no scheduler)")
    print()
    print(f"  {_c(CYAN, 'make stop')}      → Detener el pipeline")
    print( "                  Stop the pipeline")
    print()
    print(f"  {_c(CYAN, 'centinel doctor')} → Verificar que todo está listo")
    print( "                    Verify everything is ready (GO/NO-GO)")
    print()
    print(_c(GREEN, "  Configuración completada / Configuration complete."))
    print()


if __name__ == "__main__":
    main()
