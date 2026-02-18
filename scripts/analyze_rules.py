"""
analyze_rules.py - Reglas temporales de detección de anomalías electorales (v4)

Este módulo orquesta reglas temporales usadas en Proyecto Centinela
para identificar posibles anomalías en datos de actas electorales scrapeadas del CNE.

**Advertencia**: Estas reglas son indicadores estadísticos, NO prueba de fraude.
Pendiente validación académica (ej. UNAH).

Autor: Proyecto Centinela (temporal)
Fecha: Enero 2026

analyze_rules.py - Temporary rules for detecting electoral anomalies (v4)

This module orchestrates temporary rules used in Proyecto Centinela
to identify potential anomalies in electoral records scraped from the CNE.

**Warning**: These rules are statistical indicators, NOT proof of fraud.
Pending academic validation (e.g., UNAH).

Author: Proyecto Centinela (temporary)
Date: January 2026
"""

from pathlib import Path
import sys
from typing import Callable, List, Optional, Tuple

# Ajusta la ruta para importar reglas desde dev-v4/command_center. / Adjust the path to import rules from dev-v4/command_center.
RULES_PATH = Path(__file__).resolve().parents[1] / "dev-v4" / "command_center"
sys.path.insert(0, str(RULES_PATH))

from rules.benford_second_digit import benford_second_digit_test  # noqa: E402
from rules.last_digit_uniformity import last_digit_uniformity_test  # noqa: E402
from rules.spike_time_series import detect_spike_in_time_series  # noqa: E402

# ---------------------------------------------------------------------------
# Core rule registry and orchestrator used by tests and pipeline.
# ---------------------------------------------------------------------------

# RULES: list of (name, apply_fn) tuples.  apply_fn signature:
#   apply_fn(current_data: dict, previous_data: dict | None, config: dict) -> list[dict]
RULES: List[Tuple[str, Callable]] = []


def run_all_rules(
    current_data: dict,
    previous_data: Optional[dict],
    config: dict,
) -> List[dict]:
    """Execute all enabled rules and return aggregated alerts.

    Respects ``config["rules"]["global_enabled"]`` as a master switch and
    ``config["rules"][rule_name]["enabled"]`` for per-rule toggling.
    """
    rules_cfg = config.get("rules", {})
    if not rules_cfg.get("global_enabled", True):
        return []

    alerts: List[dict] = []
    for name, apply_fn in RULES:
        rule_section = rules_cfg.get(name, {})
        if not rule_section.get("enabled", True):
            continue
        alerts.extend(apply_fn(current_data, previous_data, rule_section))
    return alerts


# Ejemplo de uso (main para pruebas). / Example usage (main for tests).
if __name__ == "__main__":
    # Datos de prueba (reemplaza con tus actas reales). / Test data (replace with your real records).
    sample_votes = [
        12345,
        6789,
        100000,
        54321,
        9876,
    ]  # Conteos de votos. / Vote counts.

    chi2, alert = benford_second_digit_test(sample_votes)
    print(f"2BL Test: chi2={chi2:.2f}, Alerta={alert}")

    chi2_last, alert_last = last_digit_uniformity_test(sample_votes)
    print(f"Last Digit Test: chi2={chi2_last:.2f}, Alerta={alert_last}")

    sample_times = ["01:30", "02:15", "03:40", "05:00"]
    sample_values = [10, 55, 35, 5]
    print(f"Spike Test: {detect_spike_in_time_series(sample_times, sample_values)}")
