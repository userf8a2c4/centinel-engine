"""Simulación retroactiva de snapshots históricos para Centinel.

Uso:
    python simulate_retroactiva.py --config config/simulation_2025.yaml
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import yaml

BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR / "src"))

from simulation_engine import RetroSimulationEngine  # noqa: E402


def load_simulation_config(path: Path) -> dict:
    """Carga configuración YAML de simulación."""
    if not path.exists():
        raise FileNotFoundError(f"No existe archivo de configuración: {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def build_parser() -> argparse.ArgumentParser:
    """CLI principal de simulación."""
    parser = argparse.ArgumentParser(
        description="Ejecuta simulación retroactiva con snapshots históricos JSON."
    )
    parser.add_argument(
        "--config",
        default="config/simulation_2025.yaml",
        help="Ruta al archivo YAML de configuración.",
    )
    parser.add_argument(
        "--sleep",
        action="store_true",
        help="Activa el sleep real entre snapshots (respeta simulation_interval_seconds).",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    config_path = Path(args.config)
    config = load_simulation_config(config_path)

    if args.sleep:
        config["sleep_between_snapshots"] = True

    logging.basicConfig(
        level=config.get("log_level", "INFO"),
        format="%(asctime)s %(levelname)s %(message)s",
    )

    engine = RetroSimulationEngine(config)
    try:
        results = engine.run()
    finally:
        engine.close()

    summary = {
        "snapshots_processed": len(results),
        "results_dir": str(config.get("results_dir", "results/simulation")),
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
