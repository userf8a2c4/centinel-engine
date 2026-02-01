"""Reglas estadísticas para auditoría presidencial.

Este módulo incluye funciones específicas para auditorías de distribución de
votos usando la Ley de Benford y pruebas chi-cuadrado.

Presidential audit statistical rules.

This module includes specific functions for auditing vote distributions using
Benford's Law and chi-square tests.
"""

from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd
from scipy.stats import chisquare


def _first_digits(values: Iterable[int]) -> list[int]:
    """Extrae el primer dígito (1-9) de una lista de votos.

    Ignora ceros y valores nulos, devolviendo dígitos del 1 al 9.

    English:
        Extract the first digit (1-9) from a list of vote counts.

        Ignores zeros and null values, returning digits from 1 to 9.
    """
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
    """Aplica Ley de Benford al primer dígito y prueba chi-cuadrado.

    Calcula la distribución de primer dígito y la compara con la distribución
    esperada P(d) = log10(1 + 1/d). La prueba chi-cuadrado evalúa:
    chi2 = Σ (O_d - E_d)^2 / E_d, donde O_d son observados y E_d esperados.

    English:
        Apply Benford's Law to the first digit and run a chi-square test.

        It computes the first-digit distribution and compares it with the
        expected distribution P(d) = log10(1 + 1/d). The chi-square test uses:
        chi2 = Σ (O_d - E_d)^2 / E_d, where O_d are observed and E_d expected.
    """
    digits = _first_digits(votes_list)
    if not digits:
        return {
            "status": "OK",
            "p_value": 1.0,
            "detalle": "Sin datos válidos para evaluar Benford.",
        }

    observed = (
        pd.Series(digits).value_counts().reindex(range(1, 10), fill_value=0).sort_index()
    )
    total = observed.sum()
    # Distribución Benford: P(d) = log10(1 + 1/d).
    expected_prob = np.array([np.log10(1 + 1 / d) for d in range(1, 10)])
    expected_counts = expected_prob * total

    chi_result = chisquare(observed.values, f_exp=expected_counts)
    p_value = float(chi_result.pvalue)
    status = "ANOMALIA" if p_value < 0.05 else "OK"
    detalle = (
        "Benford primer dígito: chi2="
        f"{chi_result.statistic:.2f}, p_value={p_value:.4f}, "
        f"muestras={int(total)}."
    )
    return {"status": status, "p_value": p_value, "detalle": detalle}


def check_distribution_chi2(df_normalized: pd.DataFrame) -> dict:
    """Prueba chi-cuadrado sobre distribución partido/departamento.

    Agrupa votos observados por partido y departamento, y compara contra
    esperados proporcionales a la participación global del partido.
    Esperado = total_departamento * (votos_partido_global / votos_global).
    La prueba usa chi2 = Σ (O - E)^2 / E sobre todas las celdas.

    English:
        Chi-square test over party/department distribution.

        It groups observed votes by party and department, and compares them to
        expected counts proportional to each party's global share.
        Expected = department_total * (party_global_votes / global_votes).
        The test uses chi2 = Σ (O - E)^2 / E over all cells.
    """
    if df_normalized is None or df_normalized.empty:
        return {
            "status": "OK",
            "p_value": 1.0,
            "detalle": "Sin datos para evaluar distribución chi-cuadrado.",
        }

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
        (col for col in ["votos", "votes", "vote_total", "total_votes"] if col in df_normalized),
        None,
    )

    if not dept_col or not party_col or not votes_col:
        return {
            "status": "OK",
            "p_value": 1.0,
            "detalle": "Columnas requeridas faltantes para distribución chi-cuadrado.",
        }

    df = df_normalized[[dept_col, party_col, votes_col]].copy()
    df[votes_col] = pd.to_numeric(df[votes_col], errors="coerce").fillna(0)
    df = df[df[votes_col] >= 0]

    observed_table = (
        df.groupby([dept_col, party_col])[votes_col].sum().unstack(fill_value=0)
    )
    if observed_table.empty:
        return {
            "status": "OK",
            "p_value": 1.0,
            "detalle": "Tabla de observados vacía para chi-cuadrado.",
        }

    party_totals = observed_table.sum(axis=0)
    total_votes = party_totals.sum()
    if total_votes == 0:
        return {
            "status": "OK",
            "p_value": 1.0,
            "detalle": "Total de votos igual a cero para chi-cuadrado.",
        }

    party_share = party_totals / total_votes
    dept_totals = observed_table.sum(axis=1)
    # Esperado por celda: E_{d,p} = total_departamento_d * share_partido_p.
    expected_table = pd.DataFrame(
        np.outer(dept_totals.values, party_share.values),
        index=dept_totals.index,
        columns=party_share.index,
    )

    observed_flat = observed_table.values.ravel()
    expected_flat = expected_table.values.ravel()
    valid_mask = expected_flat > 0
    if not np.any(valid_mask):
        return {
            "status": "OK",
            "p_value": 1.0,
            "detalle": "Esperados nulos para chi-cuadrado.",
        }

    chi_result = chisquare(observed_flat[valid_mask], f_exp=expected_flat[valid_mask])
    p_value = float(chi_result.pvalue)
    status = "ANOMALIA" if p_value < 0.05 else "OK"
    detalle = (
        "Distribución partido/departamento: chi2="
        f"{chi_result.statistic:.2f}, p_value={p_value:.4f}, "
        f"celdas={int(valid_mask.sum())}."
    )
    return {"status": status, "p_value": p_value, "detalle": detalle}
