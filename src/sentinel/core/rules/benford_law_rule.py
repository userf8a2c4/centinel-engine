"""Regla Benford para distribución del primer dígito en votos.

Benford rule for first-digit distribution of votes.
"""

from __future__ import annotations

import collections
import math
from typing import Dict, List, Optional

from scipy.stats import chisquare

from sentinel.core.rules.common import extract_department, safe_int_or_none
from sentinel.core.rules.registry import rule


def _collect_votes_by_candidate(data: dict) -> Dict[str, List[int]]:
    """Agrupa votos por candidato desde estructuras heterogéneas.

    Inspecciona listas de candidatos y mesas, filtrando votos inválidos o
    negativos, para construir series por candidato.

    English:
        Group votes per candidate from heterogeneous structures.

        Inspects candidate lists and tables, filtering invalid or negative
        counts to build per-candidate series.
    """
    votes_by_candidate: Dict[str, List[int]] = collections.defaultdict(list)

    def append_votes(entries: object) -> None:
        """Extrae votos desde una lista y los agrega por candidato.

        English:
            Extract votes from a list and append them per candidate.
        """
        if not isinstance(entries, list):
            return
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            candidate_id = str(
                entry.get("id")
                or entry.get("candidate_id")
                or entry.get("nombre")
                or entry.get("name")
                or entry.get("candidato")
                or "unknown"
            )
            votes = safe_int_or_none(entry.get("votos") or entry.get("votes"))
            if votes is None or votes <= 0:
                continue
            votes_by_candidate[candidate_id].append(votes)

    append_votes(data.get("votos") or data.get("candidates") or data.get("candidatos"))

    mesas = data.get("mesas") or data.get("tables") or []
    if isinstance(mesas, list):
        for mesa in mesas:
            if not isinstance(mesa, dict):
                continue
            append_votes(mesa.get("votos") or mesa.get("candidates") or [])

    return votes_by_candidate


@rule(
    name="Ley de Benford (alternativa)",
    severity="Medium",
    description="Analiza distribución del primer dígito por candidato con chi-cuadrado.",
    config_key="benford_law",
)
def apply(current_data: dict, previous_data: Optional[dict], config: dict) -> List[dict]:
    """
    Analiza la distribución del primer dígito (Ley de Benford) en votos por candidato.

    Esta regla revisa si la distribución de los primeros dígitos de los votos por
    candidato se desvía significativamente de la distribución esperada bajo la Ley
    de Benford. Se utiliza prueba chi-cuadrado y una desviación porcentual máxima para
    detectar patrones atípicos que podrían sugerir manipulación o carga artificial.

    Args:
        current_data: Snapshot JSON actual del CNE.
        previous_data: Snapshot JSON anterior (None en el primer snapshot).
        config: Sección de configuración específica de la regla desde config.yaml.

    Returns:
        Lista de alertas en formato estándar (vacía si todo normal).

    English:
        Analyzes first-digit distribution (Benford's Law) for candidate vote counts.

        This rule checks whether the first-digit distribution of candidate votes
        deviates from the expected Benford distribution using a chi-squared test and
        a maximum deviation threshold. Significant deviations can indicate abnormal
        data generation or manipulation patterns.

    Args:
        current_data: Current CNE JSON snapshot.
        previous_data: Previous JSON snapshot (None for the first snapshot).
        config: Rule-specific configuration section from config.yaml.

    Returns:
        List of alerts in the standard format (empty if normal).
    """
    alerts: List[dict] = []
    votes_by_candidate = _collect_votes_by_candidate(current_data)
    if not votes_by_candidate:
        return alerts

    min_samples = int(config.get("min_samples", 10))
    deviation_threshold = float(config.get("deviation_pct", 15))
    chi_square_threshold = float(config.get("chi_square_threshold", 0.05))

    expected_distribution = {digit: math.log10(1 + 1 / digit) * 100 for digit in range(1, 10)}
    department = extract_department(current_data)

    for candidate, votes in votes_by_candidate.items():
        if len(votes) < min_samples:
            continue
        first_digits = [int(str(vote)[0]) for vote in votes if vote and str(vote)[0].isdigit()]
        if len(first_digits) < min_samples:
            continue
        counts = collections.Counter(first_digits)
        observed_counts = [counts.get(digit, 0) for digit in range(1, 10)]
        total = sum(observed_counts)
        if total <= 0:
            continue
        expected_counts = [expected_distribution[digit] / 100 * total for digit in range(1, 10)]
        chi_result = chisquare(observed_counts, f_exp=expected_counts)
        observed_pct = {digit: (counts.get(digit, 0) / total) * 100 for digit in range(1, 10)}
        deviation_pct = max(abs(observed_pct[digit] - expected_distribution[digit]) for digit in range(1, 10))
        if chi_result.pvalue >= chi_square_threshold and deviation_pct < deviation_threshold:
            continue

        alerts.append(
            {
                "type": "Desviación Ley de Benford",
                "severity": "Medium",
                "department": department,
                "justification": (
                    "Ley de Benford detectó desviación en el primer dígito. "
                    f"Candidato={candidate}, muestras={total}, "
                    f"chi2={chi_result.statistic:.2f}, pvalue={chi_result.pvalue:.4f}, "
                    f"desviación_max={deviation_pct:.2f}% (umbral={deviation_threshold:.2f}%)."
                ),
            }
        )

    return alerts
