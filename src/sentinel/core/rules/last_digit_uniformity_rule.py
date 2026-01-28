"""Regla de uniformidad del último dígito.

Last digit uniformity rule.
"""

from __future__ import annotations

from typing import List, Optional

import numpy as np
from scipy.stats import chisquare

from sentinel.core.rules.common import (
    extract_candidate_votes,
    extract_department,
    extract_total_votes,
    extract_numeric_list,
)
from sentinel.core.rules.registry import rule


def _last_digit(number: int) -> Optional[int]:
    """Devuelve el último dígito de un entero no negativo.

    Retorna None para valores negativos para evitar sesgos en la prueba.

    English:
        Return the last digit of a non-negative integer.

        Returns None for negative values to avoid bias in the test.
    """
    if number < 0:
        return None
    return int(str(number)[-1])


@rule(
    name="Uniformidad Último Dígito",
    severity="CRITICAL",
    description="Prueba chi-cuadrado sobre últimos dígitos 0-9.",
    config_key="last_digit_uniformity",
)
def apply(
    current_data: dict, previous_data: Optional[dict], config: dict
) -> List[dict]:
    """
    Evalúa la uniformidad del último dígito en conteos de votos.

    Aplica un test chi-cuadrado sobre los últimos dígitos (0-9) usando votos
    por candidato y total emitido. Si el p-value es menor al umbral crítico,
    se genera alerta de severidad CRITICAL.

    Args:
        current_data: Snapshot JSON actual del CNE.
        previous_data: Snapshot JSON anterior (None en el primer snapshot).
        config: Configuración específica de la regla.

    Returns:
        Lista de alertas en formato estándar.

    English:
        Evaluates last-digit uniformity for vote counts.

        Applies a chi-square test over last digits (0-9) using candidate vote
        totals and total emitted votes. If p-value is below the critical
        threshold, a CRITICAL alert is produced.

    Args:
        current_data: Current CNE JSON snapshot.
        previous_data: Previous JSON snapshot (None for the first snapshot).
        config: Rule-specific configuration section.

    Returns:
        List of alerts in the standard format.
    """
    del previous_data

    alerts: List[dict] = []
    department = extract_department(current_data)
    candidate_votes = extract_numeric_list(
        candidate.get("votes")
        for candidate in extract_candidate_votes(current_data).values()
    )
    total_votes = extract_total_votes(current_data)
    if total_votes is not None:
        candidate_votes.append(total_votes)

    min_samples = int(config.get("min_samples", 20))
    if len(candidate_votes) < min_samples:
        return alerts

    digits = [digit for digit in (_last_digit(value) for value in candidate_votes) if digit is not None]
    if len(digits) < min_samples:
        return alerts

    observed_counts = np.array([digits.count(d) for d in range(10)], dtype=float)
    total = observed_counts.sum()
    if total == 0:
        return alerts

    expected_counts = np.ones(10, dtype=float) * (total / 10)
    chi_result = chisquare(observed_counts, f_exp=expected_counts)
    critical_pvalue = float(config.get("chi_pvalue_critical", 0.001))
    if chi_result.pvalue >= critical_pvalue:
        return alerts

    message = (
        "El último dígito de los votos no es uniforme; p-value "
        f"{chi_result.pvalue:.4f}."
    )
    alerts.append(
        {
            "type": "Uniformidad Último Dígito",
            "severity": "CRITICAL",
            "department": department,
            "message": message,
            "value": {"p_value": float(chi_result.pvalue)},
            "threshold": {"chi_pvalue_critical": critical_pvalue},
            "result": (
                "CRITICAL",
                message,
                {"p_value": float(chi_result.pvalue)},
                {"chi_pvalue_critical": critical_pvalue},
            ),
            "justification": (
                "Chi-cuadrado sobre últimos dígitos (0-9) en votos. "
                f"muestras={len(digits)}, pvalue={chi_result.pvalue:.4f}."
            ),
        }
    )
    return alerts
