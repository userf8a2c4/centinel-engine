"""
analyze_rules.py - Reglas temporales de detección de anomalías electorales

Este módulo orquesta reglas temporales usadas en Centinel para identificar
posibles anomalías en datos de actas electorales scrapeadas del CNE.

**Advertencia**: Estas reglas son indicadores estadísticos, NO prueba de fraude.
Pendiente validación académica (ej. UNAH).

Autor: Centinel (temporal)
Fecha: Enero 2026

analyze_rules.py - Temporary rules for detecting electoral anomalies

This module orchestrates temporary rules used in Centinel to identify
potential anomalies in electoral records scraped from the CNE.

**Warning**: These rules are statistical indicators, NOT proof of fraud.
Pending academic validation (e.g., UNAH).

Author: Centinel (temporary)
Date: January 2026
"""

from pathlib import Path
import sys

# Ajusta la ruta para importar reglas desde command_center.
# Adjust the path to import rules from command_center.
RULES_PATH = Path(__file__).resolve().parents[1] / "command_center"
sys.path.insert(0, str(RULES_PATH))

from rules.benford_second_digit import benford_second_digit_test
from rules.last_digit_uniformity import last_digit_uniformity_test
from rules.spike_time_series import detect_spike_in_time_series


# Ejemplo de uso (main para pruebas).
# Example usage (main for tests).
if __name__ == "__main__":
    # Datos de prueba (reemplaza con tus actas reales).
    # Test data (replace with your real records).
    # Conteos de votos.
    # Vote counts.
    sample_votes = [12345, 6789, 100000, 54321, 9876]

    chi2, alert = benford_second_digit_test(sample_votes)
    print(f"2BL Test: chi2={chi2:.2f}, Alerta={alert}")

    chi2_last, alert_last = last_digit_uniformity_test(sample_votes)
    print(f"Last Digit Test: chi2={chi2_last:.2f}, Alerta={alert_last}")

    sample_times = ["01:30", "02:15", "03:40", "05:00"]
    sample_values = [10, 55, 35, 5]
    print(f"Spike Test: {detect_spike_in_time_series(sample_times, sample_values)}")
