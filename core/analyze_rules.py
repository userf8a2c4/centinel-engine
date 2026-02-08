"""Reglas estadísticas para auditoría presidencial.

Este módulo incluye funciones específicas para auditorías de distribución de
votos usando la Ley de Benford y pruebas chi-cuadrado.

Presidential audit statistical rules.

This module includes specific functions for auditing vote distributions using
Benford's Law and chi-square tests.
"""

from __future__ import annotations

from typing import Iterable

import logging
import math
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from scipy.stats import chisquare

logger = logging.getLogger(__name__)

_DEFAULT_RULES_CONFIG = {
    "benford_law": {"p_threshold": 0.05, "min_samples": 10},
    "distribution_chi2": {
        "p_threshold": 0.05,
        "min_groups": 2,
        "min_expected": 1.0,
        "expected_basis": "uniform",
        "historical_shares": {},
    },
}


def _load_rules_config() -> dict:
    """/** Carga reglas desde command_center/rules.yaml. / Load rules from command_center/rules.yaml. **"""
    rules_path = Path(__file__).resolve().parents[1] / "command_center" / "rules.yaml"
    if not rules_path.exists():
        return {}
    try:
        with rules_path.open("r", encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}
    except (OSError, yaml.YAMLError) as exc:
        logger.warning("No se pudo leer rules.yaml: %s", exc)
        return {}


def _get_rule_param(config: dict, *keys: str, default):
    """/** Obtiene un parámetro de reglas con múltiples llaves. / Fetch a rules parameter using multiple keys. **"""
    for key in keys:
        if key in config:
            return config[key]
    return default


def _first_digits(values: Iterable[int]) -> list[int]:
    """/** Extrae primer dígito (1-9) de una lista. / Extract first digit (1-9) from a list. **"""
    digits: list[int] = []
    for value in values:
        if value is None:
            continue
        value = abs(int(value))
        if value == 0:
            continue
        digits.append(int(str(value)[0]))
    return digits


def apply_benford_law(votes_list: list[int]) -> dict:
    """/** Aplica Benford y chi-cuadrado al primer dígito. / Apply Benford and chi-square to the first digit. **"""
    config = _load_rules_config()
    benford_config = config.get("benford_law", {})
    p_threshold = float(
        _get_rule_param(
            config,
            "benford_p_threshold",
            default=benford_config.get(
                "p_threshold", _DEFAULT_RULES_CONFIG["benford_law"]["p_threshold"]
            ),
        )
    )
    min_samples = int(
        _get_rule_param(
            config,
            "benford_min_samples",
            default=benford_config.get(
                "min_samples", _DEFAULT_RULES_CONFIG["benford_law"]["min_samples"]
            ),
        )
    )
    min_required = max(10, min_samples)
    if not votes_list or len(votes_list) < min_required:
        return {
            "status": "INSUFICIENTE_DATOS",
            "p_value": 1.0,
            "observed_freq": {},
            "expected_freq": {},
            "detalle": "No hay suficientes votos para análisis",
        }

    digits = _first_digits(votes_list)
    if len(digits) < min_required:
        return {
            "status": "INSUFICIENTE_DATOS",
            "p_value": 1.0,
            "observed_freq": {},
            "expected_freq": {},
            "detalle": "No hay suficientes votos para análisis",
        }

    observed_counts = (
        pd.Series(digits)
        .value_counts()
        .reindex(range(1, 10), fill_value=0)
        .sort_index()
    )
    total_observed_count = observed_counts.sum()
    if total_observed_count == 0:
        return {
            "status": "OK",
            "p_value": 1.0,
            "detalle": "Total de votos igual a cero; Benford omitido.",
        }
    # Distribución Benford: P(d) = log10(1 + 1/d). / Benford distribution formula.
    expected_probabilities = np.array(
        [math.log10(1 + 1 / digit_value) for digit_value in range(1, 10)]
    )
    expected_counts = expected_probabilities * total_observed_count
    observed_freq = {
        str(k): float(v) for k, v in (observed_counts / total_observed_count).items()
    }
    expected_freq = {
        str(digit_index + 1): float(value)
        for digit_index, value in enumerate(expected_probabilities)
    }

    try:
        # Chi-cuadrado = Σ((O - E)^2 / E). / Chi-square = Σ((O - E)^2 / E).
        chi_result = chisquare(observed_counts.values, f_exp=expected_counts)
        p_value = float(chi_result.pvalue)
    except (ValueError, ZeroDivisionError, FloatingPointError):
        # Evita división por cero en chi2. / Avoid divide-by-zero in chi2.
        return {
            "status": "OK",
            "p_value": 1.0,
            "detalle": "Benford omitido por datos inválidos (chi2 no válido).",
        }

    status = "ANOMALIA" if p_value < p_threshold else "OK"
    detalle = (
        "Benford primer dígito: chi2="
        f"{chi_result.statistic:.2f}, p_value={p_value:.4f}, "
        f"muestras={total_observed_count}, umbral={p_threshold:.2f}."
    )
    if status == "ANOMALIA":
        logger.warning("Benford detectó anomalía: %s", detalle)
    return {
        "status": status,
        "p_value": p_value,
        "observed_freq": observed_freq,
        "expected_freq": expected_freq,
        "detalle": detalle,
    }


def check_distribution_chi2(df_normalized: pd.DataFrame) -> dict:
    """/** Prueba chi-cuadrado de distribución por grupos. / Chi-square test for group distributions. **"""
    if df_normalized is None or df_normalized.empty:
        return {
            "status": "OK",
            "p_value": 1.0,
            "chi2_stat": 0.0,
            "detalle": "Sin datos para evaluar distribución chi-cuadrado.",
        }

    config = _load_rules_config()
    dist_config = config.get("distribution_chi2", {})
    p_threshold = float(
        _get_rule_param(
            config,
            "chi2_p_critical",
            default=dist_config.get(
                "p_threshold", _DEFAULT_RULES_CONFIG["distribution_chi2"]["p_threshold"]
            ),
        )
    )
    min_groups = int(
        dist_config.get(
            "min_groups", _DEFAULT_RULES_CONFIG["distribution_chi2"]["min_groups"]
        )
    )
    min_expected = float(
        dist_config.get(
            "min_expected", _DEFAULT_RULES_CONFIG["distribution_chi2"]["min_expected"]
        )
    )
    expected_basis = dist_config.get(
        "expected_basis", _DEFAULT_RULES_CONFIG["distribution_chi2"]["expected_basis"]
    )
    historical_shares = dist_config.get(
        "historical_shares",
        _DEFAULT_RULES_CONFIG["distribution_chi2"]["historical_shares"],
    )

    dept_col = next(
        (col for col in ["departamento", "department", "dep"] if col in df_normalized),
        None,
    )
    party_col = next(
        (
            col
            for col in ["partido", "party", "candidate_name", "candidate_id"]
            if col in df_normalized
        ),
        None,
    )
    votes_col = next(
        (
            col
            for col in ["votos", "votes", "vote_total", "total_votes"]
            if col in df_normalized
        ),
        None,
    )

    group_col = party_col or dept_col
    if not group_col or not votes_col:
        return {
            "status": "OK",
            "p_value": 1.0,
            "chi2_stat": 0.0,
            "detalle": "Columnas requeridas faltantes para distribución chi-cuadrado.",
        }

    grouped_votes_frame = df_normalized[[group_col, votes_col]].copy()
    grouped_votes_frame[votes_col] = pd.to_numeric(
        grouped_votes_frame[votes_col], errors="coerce"
    ).fillna(0)
    grouped_votes_frame = grouped_votes_frame[grouped_votes_frame[votes_col] >= 0]
    votes_list = grouped_votes_frame[votes_col].tolist()
    if not votes_list or len(votes_list) < 10:
        return {
            "status": "INSUFICIENTE_DATOS",
            "p_value": 1.0,
            "chi2_stat": 0.0,
            "detalle": "No hay suficientes votos para análisis",
        }

    observed_series = grouped_votes_frame.groupby(group_col)[votes_col].sum()
    if observed_series.empty:
        return {
            "status": "OK",
            "p_value": 1.0,
            "chi2_stat": 0.0,
            "detalle": "Tabla de observados vacía para chi-cuadrado.",
        }

    total_votes = float(observed_series.sum())
    if total_votes == 0:
        return {
            "status": "OK",
            "p_value": 1.0,
            "chi2_stat": 0.0,
            "detalle": "Total de votos igual a cero para chi-cuadrado.",
        }

    group_names = list(observed_series.index.astype(str))
    if len(group_names) < min_groups:
        return {
            "status": "OK",
            "p_value": 1.0,
            "chi2_stat": 0.0,
            "detalle": f"Grupos insuficientes (min={min_groups}, actuales={len(group_names)}).",
        }

    use_historical = (
        expected_basis == "historical"
        and isinstance(historical_shares, dict)
        and set(group_names).issubset(historical_shares.keys())
    )
    if use_historical:
        raw_shares = np.array([float(historical_shares[name]) for name in group_names])
        share_total = float(raw_shares.sum())
        if share_total <= 0:
            use_historical = False
    if use_historical:
        expected_share = raw_shares / raw_shares.sum()
        basis_label = "historica"
    else:
        # Distribución uniforme: cada grupo recibe 1 / n. / Uniform distribution: each group gets 1 / n.
        expected_share = np.array([1.0 / len(group_names)] * len(group_names))
        basis_label = "uniforme"

    expected_counts = expected_share * total_votes
    if np.any(expected_counts < min_expected):
        return {
            "status": "OK",
            "p_value": 1.0,
            "chi2_stat": 0.0,
            "detalle": "Esperados demasiado bajos para chi-cuadrado.",
        }

    try:
        observed_values = observed_series.values.astype(float)
        expected_values = expected_counts.astype(float)
        # Chi-cuadrado = Σ((O - E)^2 / E). / Chi-square = Σ((O - E)^2 / E).
        chi_result = chisquare(observed_values, f_exp=expected_values)
        p_value = float(chi_result.pvalue)
    except (ValueError, ZeroDivisionError, FloatingPointError):
        # Evita división por cero en chi2. / Avoid divide-by-zero in chi2.
        return {
            "status": "OK",
            "p_value": 1.0,
            "chi2_stat": 0.0,
            "detalle": "Chi-cuadrado omitido por datos inválidos.",
        }

    chi2_stat = float(chi_result.statistic)
    status = "ANOMALIA" if p_value < p_threshold else "OK"
    detalle = (
        f"Distribución {group_col} ({basis_label}): chi2={chi2_stat:.2f}, "
        f"p_value={p_value:.4f}, grupos={len(group_names)}, umbral={p_threshold:.2f}."
    )
    if status == "ANOMALIA":
        logger.warning("Chi-cuadrado detectó anomalía: %s", detalle)
    return {
        "status": status,
        "p_value": p_value,
        "chi2_stat": chi2_stat,
        "detalle": detalle,
    }


if __name__ == "__main__":
    # Ejemplo de uso / Usage example.
    sample_votes = [120, 340, 560, 780, 910, 101, 230, 456, 789, 905]
    logger.info("benford_sample_result %s", apply_benford_law(sample_votes))

    sample_votes_frame = pd.DataFrame(
        {
            "departamento": ["Atlántida", "Atlántida", "Cortés", "Cortés"],
            "partido": ["PARTIDO A", "PARTIDO B", "PARTIDO A", "PARTIDO B"],
            "votos": [1200, 800, 2400, 1600],
        }
    )
    logger.info("chi2_sample_result %s", check_distribution_chi2(sample_votes_frame))
