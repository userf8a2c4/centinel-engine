# Install Dev Deps Module
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

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import tomllib


def _format_dependency(name: str, constraint: object) -> str | None:
    if name == "python":
        return None
    if isinstance(constraint, str):
        if constraint in {"*", ""}:
            return name
        if constraint[0].isdigit():
            return f"{name}=={constraint}"
        return f"{name}{constraint}"
    if isinstance(constraint, dict):
        extras = ""
        extra_values = constraint.get("extras")
        if extra_values:
            extras = f"[{','.join(extra_values)}]"
        version = constraint.get("version")
        if not version or version == "*":
            return f"{name}{extras}"
        return f"{name}{extras}{version}"
    return None


def main() -> int:
    pyproject = Path("pyproject.toml")
    data = tomllib.loads(pyproject.read_text())
    dev_deps = data["tool"]["poetry"]["group"]["dev"]["dependencies"]
    requirements = [
        formatted for name, constraint in dev_deps.items() if (formatted := _format_dependency(name, constraint))
    ]
    if not requirements:
        print("No dev dependencies found to install.")
        return 0
    command = [sys.executable, "-m", "pip", "install", "--upgrade", *requirements]
    print("Installing dev dependencies:", " ".join(command))
    subprocess.check_call(command)  # nosec B603
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
