from __future__ import annotations

import subprocess
import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import toml as tomllib
    except ModuleNotFoundError:
        print("`toml` not found for Python < 3.11. Installing...", file=sys.stderr)
        subprocess.check_call([sys.executable, "-m", "pip", "install", "toml"])
        import toml as tomllib


def _format_dependency(name: str, constraint: object) -> str | None:
    if name == "python":
        return None
    if isinstance(constraint, str):
        if constraint in {"*", ""}:
            return name
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
    dev_deps = data.get("tool", {}).get("poetry", {}).get("group", {}).get("dev", {}).get("dependencies", {})
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
    subprocess.check_call(command)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
