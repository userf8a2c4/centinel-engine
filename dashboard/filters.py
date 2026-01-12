"""English docstring: Filtering helpers for the Sentinel dashboard.

---
Docstring en español: Ayudantes de filtrado para el dashboard Sentinel.
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st


def _normalize_date_range(date_range: tuple[date, date] | list[date]) -> tuple[date, date]:
    """English docstring: Normalize a date input into a (start, end) tuple.

    Args:
        date_range: Streamlit date input result.

    Returns:
        Tuple with start and end dates.
    ---
    Docstring en español: Normaliza un input de fecha a una tupla (inicio, fin).

    Args:
        date_range: Resultado del date_input de Streamlit.

    Returns:
        Tupla con fechas de inicio y fin.
    """

    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        return date_range[0], date_range[1]
    if isinstance(date_range, (list, tuple)) and len(date_range) == 1:
        return date_range[0], date_range[0]
    if isinstance(date_range, tuple):
        return date_range
    return date_range, date_range


@st.cache_data
def filtrar_df(
    df: pd.DataFrame,
    deptos: list[str],
    partidos: list[str],
    date_range: tuple[date, date] | list[date],
) -> pd.DataFrame:
    """English docstring: Filter the snapshot dataframe by department, party, and date.

    Args:
        df: Raw snapshots dataframe.
        deptos: Selected departments.
        partidos: Selected parties.
        date_range: Selected date range.

    Returns:
        Filtered dataframe.
    ---
    Docstring en español: Filtra el dataframe de snapshots por departamento, partido y fecha.

    Args:
        df: Dataframe crudo de snapshots.
        deptos: Departamentos seleccionados.
        partidos: Partidos seleccionados.
        date_range: Rango de fechas seleccionado.

    Returns:
        Dataframe filtrado.
    """

    if df.empty:
        return df

    start_date, end_date = _normalize_date_range(date_range)
    filtered = df.copy()

    # Apply department filter unless "Todos" is selected. / Aplicar filtro de departamentos salvo "Todos".
    if deptos and "Todos" not in deptos:
        filtered = filtered[filtered["departamento"].isin(deptos)]

    # Date filter based on date part. / Filtro por fecha basado en la parte de fecha.
    filtered = filtered[
        (filtered["timestamp"].dt.date >= start_date)
        & (filtered["timestamp"].dt.date <= end_date)
    ]

    # Keep only requested party columns if provided. / Mantener solo columnas de partidos solicitadas.
    base_columns = ["timestamp", "departamento", "total_votos", "hash"]
    party_columns = [p for p in partidos if p in filtered.columns]

    return filtered[base_columns + party_columns]
