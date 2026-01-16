"""
analyze_rules.py - Reglas temporales de detección de anomalías electorales (v4)

Este módulo contiene las reglas matemáticas temporales usadas en Proyecto Centinela
para identificar posibles anomalías en datos de actas electorales scrapeadas del CNE.

**Advertencia**: Estas reglas son indicadores estadísticos, NO prueba de fraude.
Pendiente validación académica (ej. UNAH).

Autor: Proyecto Centinela (temporal)
Fecha: Enero 2026

analyze_rules.py - Temporary rules for detecting electoral anomalies (v4)

This module contains the temporary mathematical rules used in Proyecto Centinela
to identify potential anomalies in electoral records scraped from the CNE.

**Warning**: These rules are statistical indicators, NOT proof of fraud.
Pending academic validation (e.g., UNAH).

Author: Proyecto Centinela (temporary)
Date: January 2026
"""

import math
from typing import Dict, List, Any, Tuple

# Probabilidades esperadas para segundo dígito según la Ley de Benford.
# Expected probabilities for the second digit under Benford's Law.
BENFORD_SECOND_DIGIT_PROBS = {
    0: 0.11968,
    1: 0.11389,
    2: 0.10882,
    3: 0.10433,
    4: 0.10031,
    5: 0.09668,
    6: 0.09337,
    7: 0.09035,
    8: 0.08757,
    9: 0.08500,
}  # Probabilidades esperadas para el segundo dígito (Benford 2BL). / Expected probabilities for the second digit (Benford 2BL).


def extract_second_digit(number: int) -> int:
    """
    Extrae el segundo dígito significativo de un número entero.
    Extracts the second significant digit from an integer.

    Ejemplo: 12345 → segundo dígito = 2
    Example: 12345 → second digit = 2

    Args:
        number (int): Número del que extraer el dígito (ej. votos totales).
        number (int): Number from which to extract the digit (e.g., total votes).

    Returns:
        int: Segundo dígito (0-9), o -1 si el número es inválido.
        int: Second digit (0-9), or -1 if the number is invalid.
    """
    if number <= 0:
        return -1
    str_num = str(number)
    if len(str_num) < 2:
        return 0  # Para números de 1 dígito, consideramos 0 como segundo. / For 1-digit numbers, we treat 0 as the second digit.
    return int(str_num[1])


def benford_second_digit_test(vote_counts: List[int]) -> Tuple[float, str]:
    """
    Aplica el test de segundo dígito de Benford (2BL) a una lista de conteos.
    Applies the Benford second-digit test (2BL) to a list of counts.

    Calcula chi-cuadrado y compara contra distribución esperada.
    Umbral temporal: chi2 > 20 → CRÍTICO (sospechoso).

    Computes chi-square and compares against the expected distribution.
    Temporary threshold: chi2 > 20 → CRITICAL (suspicious).

    Args:
        vote_counts (List[int]): Lista de conteos de votos (por acta/candidato).
        vote_counts (List[int]): List of vote counts (per record/candidate).

    Returns:
        Tuple[float, str]: (chi_cuadrado, nivel_alerta)
        Tuple[float, str]: (chi_square, alert_level)
    """
    if not vote_counts:
        return 0.0, "NO_DATA"

    observed = [0] * 10  # Conteo observado por dígito 0-9. / Observed count per digit 0-9.
    valid_count = 0

    for count in vote_counts:
        digit = extract_second_digit(count)
        if digit >= 0:
            observed[digit] += 1
            valid_count += 1

    if valid_count < 50:  # Muy pocos datos → no confiable. / Too few data points → not reliable.
        return 0.0, "INSUFFICIENT_DATA"

    chi2 = 0.0
    for d in range(10):
        expected = valid_count * BENFORD_SECOND_DIGIT_PROBS[d]
        observed_freq = observed[d]
        if expected > 0:
            chi2 += ((observed_freq - expected) ** 2) / expected

    if chi2 > 20:
        return chi2, "CRITICO"   # Alto riesgo de anomalía. / High anomaly risk.
    if chi2 > 12:
        return chi2, "ALTO"
    return chi2, "NORMAL"


def last_digit_uniformity_test(vote_counts: List[int]) -> Tuple[float, str]:
    """
    Test de uniformidad en el último dígito (debe ser ~10% cada 0-9).
    Uniformity test for the last digit (should be ~10% each 0-9).

    Args:
        vote_counts (List[int]): Lista de conteos.
        vote_counts (List[int]): List of counts.

    Returns:
        Tuple[float, str]: (chi_cuadrado, nivel_alerta)
        Tuple[float, str]: (chi_square, alert_level)
    """
    if not vote_counts:
        return 0.0, "NO_DATA"

    observed = [0] * 10
    valid_count = 0

    for count in vote_counts:
        last_digit = count % 10
        observed[last_digit] += 1
        valid_count += 1

    if valid_count < 50:
        return 0.0, "INSUFFICIENT_DATA"

    expected_per_digit = valid_count / 10.0
    chi2 = sum(((o - expected_per_digit) ** 2) / expected_per_digit for o in observed)

    if chi2 > 18:
        return chi2, "CRITICO"
    if chi2 > 12:
        return chi2, "ALTO"
    return chi2, "NORMAL"


def detect_spike_in_time_series(
    timestamps: List[str],
    values: List[int],
    suspicious_window_start: str = "02:00",
    suspicious_window_end: str = "04:00",
) -> bool:
    """
    Detecta spikes sospechosos en ventana horaria (ej. madrugada).
    Detects suspicious spikes within a time window (e.g., early morning).

    Args:
        timestamps (List[str]): Lista de timestamps (formato HH:MM).
        timestamps (List[str]): List of timestamps (HH:MM format).
        values (List[int]): Valores acumulados o incrementos.
        values (List[int]): Accumulated values or increments.
        suspicious_window_start/end (str): Ventana horaria sospechosa.
        suspicious_window_start/end (str): Suspicious time window.

    Returns:
        bool: True si hay spike significativo en la ventana.
        bool: True if there is a significant spike within the window.
    """
    # Implementación simple: suma de incrementos en ventana > 30% del total.
    # Simple implementation: sum of increments in window > 30% of total.
    total = sum(values)
    if total == 0:
        return False

    spike_sum = 0
    for ts, val in zip(timestamps, values):
        hour = int(ts.split(":")[0])
        if int(suspicious_window_start.split(":")[0]) <= hour < int(suspicious_window_end.split(":")[0]):
            spike_sum += val

    return (spike_sum / total) > 0.30  # Umbral temporal 30%. / Temporary threshold 30%.


# Ejemplo de uso (main para pruebas). / Example usage (main for tests).
if __name__ == "__main__":
    # Datos de prueba (reemplaza con tus actas reales). / Test data (replace with your real records).
    sample_votes = [12345, 6789, 100000, 54321, 9876]  # Conteos de votos. / Vote counts.

    chi2, alert = benford_second_digit_test(sample_votes)
    print(f"2BL Test: chi2={chi2:.2f}, Alerta={alert}")

    chi2_last, alert_last = last_digit_uniformity_test(sample_votes)
    print(f"Last Digit Test: chi2={chi2_last:.2f}, Alerta={alert_last}")
