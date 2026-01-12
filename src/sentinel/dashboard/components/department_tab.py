"""English docstring: Department breakdown tab rendering.

---
Docstring en español: Renderizado de la pestaña por departamento.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st


def render_department_tab(df: pd.DataFrame, partidos: list[str]) -> None:
    """English docstring: Render department table and bar chart.

    Args:
        df: Filtered dataframe.
        partidos: Selected parties to display.
    ---
    Docstring en español: Renderiza tabla y gráfico de barras por departamento.

    Args:
        df: Dataframe filtrado.
        partidos: Partidos seleccionados a mostrar.
    """

    if df.empty:
        st.info("No hay datos por departamento con los filtros actuales.")
        return

    # Aggregate latest snapshot per department. / Agregar último snapshot por departamento.
    latest_by_dept = (
        df.groupby("departamento")[["total_votos"] + partidos]
        .last()
        .reset_index()
    )

    st.dataframe(
        latest_by_dept.style.format({col: "{:,}" for col in latest_by_dept.columns if col != "departamento"})
    )

    melted = latest_by_dept.melt(
        id_vars="departamento",
        value_vars=partidos,
        var_name="Partido",
        value_name="Votos",
    )

    fig = px.bar(
        melted,
        x="departamento",
        y="Votos",
        color="Partido",
        barmode="group",
        title="Distribución de votos por departamento",
    )
    st.plotly_chart(fig, use_container_width=True)
