"""English docstring: Overview metrics for national snapshot.

---
Docstring en español: Métricas de resumen para el snapshot nacional.
"""

from __future__ import annotations

import streamlit as st
import pandas as pd


def render_overview(df: pd.DataFrame, partidos: list[str]) -> None:
    """English docstring: Render national metrics for the latest snapshot.

    Args:
        df: Filtered dataframe.
        partidos: Selected parties to display.
    ---
    Docstring en español: Renderiza métricas nacionales del último snapshot.

    Args:
        df: Dataframe filtrado.
        partidos: Partidos seleccionados a mostrar.
    """

    st.header("Resumen Nacional (Último Snapshot)")

    if df.empty:
        st.warning("No hay datos disponibles para el resumen.")
        return

    latest = df.iloc[-1]
    columns = st.columns(len(partidos) + 1)

    # Total votes metric. / Métrica de votos totales.
    columns[0].metric("Total Votos", f"{int(latest['total_votos']):,}")

    for index, party in enumerate(partidos, start=1):
        value = int(latest.get(party, 0))
        total = float(latest.get("total_votos", 0))
        pct = (value / total * 100) if total > 0 else 0
        columns[index].metric(party, f"{value:,}", f"{pct:.1f}%")
