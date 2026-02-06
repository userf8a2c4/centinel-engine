"""Reglas y utilidades para la Ley de Benford.

Español: Funciones para evaluar la distribución Benford y calcular chi-cuadrado.
English: Functions to evaluate the Benford distribution and compute chi-square.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np
from scipy import stats


@dataclass(frozen=True)
class BenfordResult:
    """Resultado de Ley de Benford.

    Español: Resultado con frecuencias observadas, esperadas y p-value.
    English: Result with observed/expected frequencies and p-value.
    """

    observed: np.ndarray
    expected: np.ndarray
    chi2: float
    p_value: float


def _first_digit(values: Iterable[int]) -> np.ndarray:
    """Extrae el primer dígito de una secuencia de números.

    Español: Convierte valores a enteros positivos y devuelve su primer dígito.
    English: Converts values to positive integers and returns their first digit.
    """

    digits = []
    for value in values:
        try:
            number = int(value)
        except (TypeError, ValueError):
            continue
        number = abs(number)
        if number == 0:
            continue
        while number >= 10:
            number //= 10
        digits.append(number)
    return np.array(digits, dtype=int)


def expected_distribution() -> np.ndarray:
    """Distribución esperada de Benford para dígitos 1-9.

    Español: Retorna vector de probabilidades para dígitos 1 a 9.
    English: Returns probability vector for digits 1 to 9.
    """

    return np.array([np.log10(1 + 1 / d) for d in range(1, 10)])


def evaluate_benford(values: Sequence[int]) -> BenfordResult:
    """Evalúa la Ley de Benford sobre una lista de votos.

    Español: Calcula frecuencias observadas, chi-cuadrado y p-value.
    English: Computes observed frequencies, chi-square, and p-value.
    """

    digits = _first_digit(values)
    expected = expected_distribution()
    if digits.size == 0:
        return BenfordResult(
            observed=np.zeros(9), expected=expected, chi2=np.nan, p_value=np.nan
        )
    counts = np.array([(digits == d).sum() for d in range(1, 10)], dtype=float)
    observed = counts / counts.sum() if counts.sum() else np.zeros(9)
    chi2_stat, p_value = stats.chisquare(counts, f_exp=expected * counts.sum())
    return BenfordResult(observed=observed, expected=expected, chi2=chi2_stat, p_value=p_value)
