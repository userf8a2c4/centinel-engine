"""Regla de Benford (segundo dígito) para detectar anomalías temporales.

Benford second-digit rule for detecting temporary anomalies.
"""

from typing import List, Tuple

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
