"""Regla avanzada de Ley de Benford (primer dígito).

Advanced Benford's Law (first digit) rule.
"""

from __future__ import annotations

import math
from typing import List, Optional

import numpy as np
from scipy.stats import chisquare

from centinel.core.rules.common import (
    extract_candidate_votes,
    extract_department,
    extract_total_votes,
    extract_numeric_list,
)
from centinel.core.rules.registry import rule


def _first_digit(number: int) -> Optional[int]:
    """Extrae el primer dígito de un entero positivo.

    Devuelve None para valores no positivos, evitando falsos positivos en la
    estadística de Benford.

    English:
        Extract the first digit from a positive integer.

        Returns None for non-positive values to avoid false positives in
        Benford calculations.
    """
    if number <= 0:
        return None
    return int(str(number)[0])


@rule(
    name="Ley de Benford (Primer Dígito)",
    severity="CRITICAL",
    description="Evalúa MAD y chi-cuadrado sobre primer dígito.",
    config_key="benford_first_digit",
)
def apply(current_data: dict, previous_data: Optional[dict], config: dict) -> List[dict]:
    """
    Evalúa la Ley de Benford para primer dígito sobre votos por candidato.

    La regla calcula el MAD (mean absolute deviation) y una prueba chi-cuadrado
    usando los votos totales por candidato y el total emitido. Si el MAD excede
    los umbrales configurados o el p-value de chi-cuadrado es pequeño, se genera
    una alerta para observadores internacionales.

    Args:
        current_data: Snapshot JSON actual del CNE.
        previous_data: Snapshot JSON anterior (None en el primer snapshot).
        config: Configuración específica de la regla.

    Returns:
        Lista de alertas en formato estándar.

    English:
        Evaluates Benford's Law for first digit on candidate vote totals.

        The rule computes MAD (mean absolute deviation) and a chi-square test
        using candidate totals and total votes. If MAD exceeds configured
        thresholds or the chi-square p-value is small, an alert is generated
        for international observers.

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
        candidate.get("votes") for candidate in extract_candidate_votes(current_data).values()
    )
    total_votes = extract_total_votes(current_data)
    if total_votes is not None:
        candidate_votes.append(total_votes)

    min_samples = int(config.get("min_samples", 15))
    if len(candidate_votes) < min_samples:
        return alerts

    digits = [digit for digit in (_first_digit(value) for value in candidate_votes) if digit]
    if len(digits) < min_samples:
        return alerts

    observed_counts = np.array([digits.count(d) for d in range(1, 10)], dtype=float)
    total = observed_counts.sum()
    if total == 0:
        return alerts

    expected_probs = np.array([math.log10(1 + 1 / d) for d in range(1, 10)])
    expected_counts = expected_probs * total
    mad = float(np.mean(np.abs((observed_counts / total) - expected_probs)))
    chi_result = chisquare(observed_counts, f_exp=expected_counts)

    mad_warning = float(config.get("mad_warning", 0.008))
    mad_critical = float(config.get("mad_critical", 0.015))
    chi_pvalue_critical = float(config.get("chi_pvalue_critical", 0.01))

    severity = "INFO"
    if mad > mad_critical or chi_result.pvalue < chi_pvalue_critical:
        severity = "CRITICAL"
    elif mad_warning <= mad <= mad_critical:
        severity = "WARNING"
    else:
        return alerts

    message = (
        "La distribución del primer dígito se desvía de Benford con MAD "
        f"{mad:.4f} y p-value {chi_result.pvalue:.4f}."
    )
    alerts.append(
        {
            "type": "Ley de Benford Primer Dígito",
            "severity": severity,
            "department": department,
            "message": message,
            "value": {"mad": mad, "p_value": float(chi_result.pvalue)},
            "threshold": {
                "mad_warning": mad_warning,
                "mad_critical": mad_critical,
                "chi_pvalue_critical": chi_pvalue_critical,
            },
            "result": (
                severity,
                message,
                {"mad": mad, "p_value": float(chi_result.pvalue)},
                {
                    "mad_warning": mad_warning,
                    "mad_critical": mad_critical,
                    "chi_pvalue_critical": chi_pvalue_critical,
                },
            ),
            "justification": (
                "Se aplicó Benford 1BL sobre votos por candidato + total emitido. "
                f"muestras={len(digits)}, MAD={mad:.4f}, "
                f"pvalue_chi2={chi_result.pvalue:.4f}."
            ),
        }
    )
    return alerts
