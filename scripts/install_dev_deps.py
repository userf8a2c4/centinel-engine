from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import tomllib


def _python_allows(constraint: str) -> bool:
    # Handle simple Python version markers used in pyproject.toml. (Maneja marcadores simples de versión de Python usados en pyproject.toml.)
    normalized = constraint.replace(" ", "")
    if normalized in {">=3.11", "<3.11"}:
        current = (sys.version_info.major, sys.version_info.minor)
        threshold = (3, 11)
        if normalized == ">=3.11":
            return current >= threshold
        return current < threshold
    # Default to allow when we cannot parse the marker. (Permite por defecto cuando no podemos interpretar el marcador.)
    return True


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
    if isinstance(constraint, list):
        # Select the first matching marker in a Poetry list constraint. (Selecciona el primer marcador coincidente en una lista de Poetry.)
        for entry in constraint:
            if not isinstance(entry, dict):
                continue
            python_marker = entry.get("python")
            if python_marker and not _python_allows(python_marker):
                continue
            return _format_dependency(name, entry)
    return None


def main() -> int:
    pyproject = Path("pyproject.toml")
    data = tomllib.loads(pyproject.read_text())
    dev_deps = data["tool"]["poetry"]["group"]["dev"]["dependencies"]
    requirements = [
        formatted
        for name, constraint in dev_deps.items()
        if (formatted := _format_dependency(name, constraint))
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
