"""English docstring: Temporal evolution tab rendering.

---
Docstring en español: Renderizado de la pestaña de evolución temporal.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st


def render_temporal_tab(df: pd.DataFrame, partidos: list[str]) -> None:
    """English docstring: Render line chart for vote evolution over time.

    Args:
        df: Filtered dataframe.
        partidos: Selected parties to display.
    ---
    Docstring en español: Renderiza gráfico de líneas para evolución temporal.

    Args:
        df: Dataframe filtrado.
        partidos: Partidos seleccionados a mostrar.
    """

    if df.empty:
        st.info("No hay datos suficientes para la evolución temporal.")
        return

    melted = df.melt(
        id_vars="timestamp",
        value_vars=partidos,
        var_name="Partido",
        value_name="Votos",
    )

    fig = px.line(
        melted,
        x="timestamp",
        y="Votos",
        color="Partido",
        title="Evolución temporal de votos",
    )
    st.plotly_chart(fig, use_container_width=True)
