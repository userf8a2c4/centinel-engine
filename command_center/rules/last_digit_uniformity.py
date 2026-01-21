"""Regla de uniformidad del último dígito para anomalías temporales.

Last-digit uniformity rule for temporary anomalies.
"""

from typing import List, Tuple


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
