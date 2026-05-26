#!/usr/bin/env python3
"""Asistente de configuración interactivo para Centinel Engine.
Interactive configuration wizard for Centinel Engine.

Uso / Usage:
    python scripts/setup_wizard.py
    make wizard
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import string
import sys
from pathlib import Path

REPO_ROOT   = Path(__file__).resolve().parent.parent
CONFIG_YAML = REPO_ROOT / "command_center" / "config.yaml"
ENV_FILE    = REPO_ROOT / ".env"
ENV_EXAMPLE = REPO_ROOT / ".env.example"
ACCESS_JSON = REPO_ROOT / "web" / "access.json"

SEED1_SALT   = "centinel-admin-salt-v1"
SEED1_ITERS  = 600_000
SEED1_LABELS = list("ABCDEFGHIJKL")

_COUNTRY_LABELS = {
    "HN": "Honduras        (CNE — production-ready)",
    "GT": "Guatemala       (TSE — configured)",
    "SV": "El Salvador     (TSE — configured)",
    "NI": "Nicaragua       (CSE — configured)",
    "MX": "Mexico          (INE — configured)",
    "CO": "Colombia        (Registraduría — configured)",
}
_DEFAULT_URLS = {
    "HN": "https://resultadosgenerales2025.cne.hn",
    "GT": "https://resultados.tse.org.gt",
    "SV": "https://resultados.tse.gob.sv",
    "NI": "https://resultados.cse.gob.ni",
    "MX": "https://prep2024.ine.mx",
    "CO": "https://resultados.registraduria.gov.co",
}

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


# ── Seed 1 generation ────────────────────────────────────────────────────────


def _generate_seed1() -> None:
    """Generate Seed 1 (S1-A … S1-L) and write web/access.json."""
    _header("SEED 1 — Generación de accesos de administrador")
    print("  Se generarán 12 seeds de acceso (S1-A … S1-L).")
    print("  Cada seed tiene 24 caracteres alfanuméricos.")
    print("  Los hashes PBKDF2-SHA256 se guardan en web/access.json.")
    print("  LOS SEEDS REALES no se guardan en el repo — cópialos ahora.")
    print()

    if ACCESS_JSON.exists():
        if not _ask_yn("¿Regenerar access.json existente? (esto invalida seeds anteriores)", default=False):
            _note("Generación de Seed 1 omitida.")
            return

    alphabet = string.ascii_letters + string.digits
    seeds: dict[str, str] = {}
    hashes: dict[str, str] = {}

    for label in SEED1_LABELS:
        seed = "".join(secrets.choice(alphabet) for _ in range(24))
        dk = hashlib.pbkdf2_hmac("sha256", seed.encode(), SEED1_SALT.encode(), SEED1_ITERS)
        key = f"S1-{label}"
        seeds[key] = seed
        hashes[key] = dk.hex()

    width = 58
    print()
    print(_c(BOLD, "  " + "═" * width))
    print(_c(BOLD, "  ▶  SEEDS — COPIA ESTO EN UN LUGAR SEGURO (no se guarda)"))
    print(_c(BOLD, "  " + "═" * width))
    for k, v in seeds.items():
        print(f"  {_c(CYAN, k)}  {v}")
    print(_c(BOLD, "  " + "═" * width))
    print()

    access = {
        "version": 1,
        "algo": "PBKDF2-SHA256",
        "salt": SEED1_SALT,
        "iterations": SEED1_ITERS,
        "seeds": hashes,
    }
    ACCESS_JSON.parent.mkdir(parents=True, exist_ok=True)
    ACCESS_JSON.write_text(json.dumps(access, indent=2) + "\n", encoding="utf-8")
    _ok(f"web/access.json escrito con {len(hashes)} hashes.")
    print()
    print("  El archivo web/access.json se commitea al repo (solo hashes).")
    print("  Después del commit haz 'git push' para publicarlo en Pages.")
    print()


# ── Main wizard ───────────────────────────────────────────────────────────────


def main() -> None:
    inner = 60  # visible characters between ║ borders
    def _banner_line(text: str = "") -> None:
        pad = inner - len(text)
        left = pad // 2
        right = pad - left
        print(_c(CYAN, "║") + " " * left + text + " " * right + _c(CYAN, "║"))

    print()
    print(_c(CYAN, "╔" + "═" * inner + "╗"))
    _banner_line()
    _banner_line("CENTINEL")
    _banner_line("Trustless Electoral Integrity Verification")
    _banner_line("Latin America")
    _banner_line()
    _banner_line("Auditoría electoral independiente, reproducible y")
    _banner_line("verificable por cualquier tercero — costo cero.")
    _banner_line()
    print(_c(CYAN, "╚" + "═" * inner + "╝"))
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

    # ── PASO 0: País / Country ────────────────────────────────────────────────
    _header("PASO 0 / STEP 0: País a auditar / Country to audit")
    print("  Selecciona el país. El wizard cargará los endpoints y departamentos.")
    print("  Select the country. The wizard will load the correct endpoints and divisions.")
    print()

    for code, label in _COUNTRY_LABELS.items():
        marker = _c(GREEN, "◉") if code == env.get("CENTINEL_COUNTRY", "HN") else "○"
        print(f"    {marker}  {code}  {label}")
    print()

    current_country = env.get("CENTINEL_COUNTRY", "HN")
    new_country = _ask(
        "Código de país / Country code (HN/GT/SV/NI/MX/CO)",
        default=current_country,
        required=True,
    ).upper()
    if new_country not in _COUNTRY_LABELS:
        _note(f"País desconocido '{new_country}' — usando HN como fallback.")
        new_country = "HN"
    env["CENTINEL_COUNTRY"] = new_country
    _ok(f"CENTINEL_COUNTRY={new_country}  ({_COUNTRY_LABELS[new_country].strip()})")

    # Auto-set election year if not set
    if not env.get("CENTINEL_YEAR"):
        import datetime
        env["CENTINEL_YEAR"] = str(datetime.date.today().year)
        _note(f"CENTINEL_YEAR={env['CENTINEL_YEAR']} (auto-set)")

    # ── PASO 1: Endpoints ─────────────────────────────────────────────────────
    _header("PASO 1 / STEP 1: Endpoint de la autoridad electoral / Electoral authority endpoint")
    print("  URL base del API de resultados. El wizard propone el default del país seleccionado.")
    print("  Base URL for the results API. Defaults to the selected country's known endpoint.")
    print()

    # Extract current base_url from YAML, fall back to country default
    m = re.search(r'^base_url:\s*"?([^"\n#]+)"?', yaml_content, re.MULTILINE)
    current_url = m.group(1).strip() if m else _DEFAULT_URLS.get(new_country, "")

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
        interval_int = int(new_interval)
        if interval_int < 60:
            _note(
                f"⚠  Intervalo {interval_int}s es muy agresivo — puede sobrecargar la fuente. "
                "Mínimo recomendado: 60s."
            )
            if not _ask_yn("¿Continuar de todas formas?", default=False):
                new_interval = "120"
                _note("Usando 120s como valor seguro.")
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

    # OTS — default ON (free, no registration, no API key needed)
    ots_raw = env.get("OTS_ENABLED", "true").lower()
    ots_on = ots_raw in ("true", "1", "yes")
    print("  OpenTimestamps (OTS) — Anclaje a Bitcoin")
    print("  " + "─" * 42)
    print("  Cada snapshot queda sellado en el blockchain de Bitcoin.")
    print("  Sin costo. Sin cuenta. Sin API key.")
    print()
    print("  Resultado: prueba criptográfica independiente de que los datos")
    print("  existían en ese momento exacto — imposible de falsificar.")
    print()
    print(f"  {_c(GREEN, '✓')} Activado por defecto  "
          f"{_c(GREEN, '✓')} Gratis para siempre  "
          f"{_c(GREEN, '✓')} Descentralizado")
    print()
    if _ask_yn("¿Activar anclaje Bitcoin/OpenTimestamps?", default=True):
        env["OTS_ENABLED"] = "true"
        ots_mode = _ask_choice(
            "¿Red? / Network?",
            choices=["mainnet", "testnet"],
            default="mainnet",
        )
        env["OTS_NETWORK"] = ots_mode
        _ok(f"OpenTimestamps activado — {ots_mode}")
    else:
        env["OTS_ENABLED"] = "false"
        _note("OpenTimestamps desactivado — los snapshots no tendrán anclaje temporal externo.")
    ots_mode = env.get("OTS_NETWORK", "mainnet")

    # Backup encryption key (optional but strongly recommended)
    print()
    print("  Clave de backup cifrado (recomendado)")
    print("  " + "─" * 38)
    print("  Cifra tus snapshots para recuperación ante desastres.")
    print("  Si no la configuras ahora, puedes añadirla luego en .env.")
    print()
    backup_key = env.get("CENTINEL_BACKUP_KEY", "")
    if not backup_key:
        if _ask_yn("¿Generar clave de backup automáticamente?", default=True):
            backup_key = secrets.token_urlsafe(32)
            print()
            print(_c(BOLD, "  ⚠  COPIA ESTO EN UN LUGAR SEGURO (no se guarda en el repo):"))
            print(f"  CENTINEL_BACKUP_KEY={_c(CYAN, backup_key)}")
            print()
            env["CENTINEL_BACKUP_KEY"] = backup_key
            _ok("CENTINEL_BACKUP_KEY generada y guardada en .env")
        else:
            _note("Backup key omitida — configura CENTINEL_BACKUP_KEY en .env antes de producción.")
    else:
        _ok("CENTINEL_BACKUP_KEY ya configurada")

    # ── PASO 7: Seed 1 (admin passwords) ─────────────────────────────────────
    _header("PASO 7 / STEP 7: Accesos de administrador (Seed 1)")
    print("  Genera o regenera los 12 seeds de acceso al panel de administración.")
    print("  Solo se guardan los hashes en web/access.json (los seeds reales no se commitean).")
    print()
    if _ask_yn("¿Generar Seed 1 ahora?", default=not ACCESS_JSON.exists()):
        _generate_seed1()
    else:
        _note("Seed 1 omitido.")

    # ── Guardar cambios ───────────────────────────────────────────────────────
    _header("Guardando configuración / Saving configuration")

    if CONFIG_YAML.exists() or yaml_content:
        CONFIG_YAML.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_YAML.write_text(yaml_content, encoding="utf-8")
        _ok(f"YAML guardado / saved: {CONFIG_YAML.relative_to(REPO_ROOT)}")

    _save_env(ENV_FILE, env, ENV_EXAMPLE)
    _ok(f".env guardado / saved: {ENV_FILE.relative_to(REPO_ROOT)}")

    # ── Resumen y próximos pasos ──────────────────────────────────────────────
    country_label = _COUNTRY_LABELS.get(new_country, new_country)
    has_backup = bool(env.get("CENTINEL_BACKUP_KEY", ""))
    seeds_status = "✓ generadas" if ACCESS_JSON.exists() else "— omitidas"

    print()
    print(_c(BOLD, "─" * 62))
    print(_c(BOLD, "  Configuración guardada / Configuration saved"))
    print(_c(BOLD, "─" * 62))
    print(f"  País          {_c(CYAN, new_country)}  {country_label.strip()}")
    print(f"  Endpoint      {_c(CYAN, new_url)}")
    print(f"  Modo          {_c(CYAN, new_mode)}")
    print(f"  Intervalo     {_c(CYAN, new_interval + 's')}")
    ots_display = f"✓ {ots_mode}" if env.get('OTS_ENABLED') == 'true' else "— desactivado"
    print(f"  OpenTimestamps {_c(GREEN if env.get('OTS_ENABLED') == 'true' else YELLOW, ots_display)}")
    print(f"  Backup key    {_c(GREEN, '✓ configurada') if has_backup else _c(YELLOW, '— omitida')}")
    print(f"  Seeds S1      {_c(GREEN, seeds_status)}")
    print(_c(BOLD, "─" * 62))
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
    print(_c(GREEN, "  CENTINEL está listo. Tu instancia es completamente independiente"))
    print(_c(GREEN, "  de cualquier autoridad electoral o institución."))
    print()
    print(_c(GREEN, "  Configuración completada / Configuration complete."))
    print()


if __name__ == "__main__":
    main()
