"""English docstring: Integrity and Benford analysis tab rendering.

---
Docstring en español: Renderizado de la pestaña de integridad y Benford.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.utils.benford import benford_analysis
from dashboard.utils.constants import BENFORD_THRESHOLD


def render_integrity_tab(df: pd.DataFrame) -> None:
    """English docstring: Render hash chain and Benford chart.

    Args:
        df: Filtered dataframe.
    ---
    Docstring en español: Renderiza cadena de hashes y gráfico Benford.

    Args:
        df: Dataframe filtrado.
    """

    if df.empty:
        st.info("No hay datos para análisis de integridad.")
        return

    st.subheader("Cadena de Hashes (últimos 5)")

    # Show last hashes for transparency. / Mostrar últimos hashes para transparencia.
    for hash_val in df["hash"].tail(5):
        st.code(hash_val)

    st.subheader("Ley de Benford")
    observed, theoretical, deviation = benford_analysis(df["total_votos"])

    if observed is None or theoretical is None or deviation is None:
        st.info("Datos insuficientes para análisis Benford.")
        return

    fig = go.Figure()
    fig.add_trace(go.Bar(x=list(range(1, 10)), y=observed, name="Observado"))
    fig.add_trace(
        go.Scatter(
            x=list(range(1, 10)),
            y=theoretical,
            mode="lines+markers",
            name="Benford",
        )
    )
    fig.update_layout(title=f"Desviación promedio: {deviation:.2f}%")
    st.plotly_chart(fig, use_container_width=True)

    # Alert if deviation exceeds threshold. / Alertar si supera el umbral.
    if deviation > BENFORD_THRESHOLD:
        st.error(f"⚠️ Posible anomalía (desviación {deviation:.2f}%)")
    else:
        st.success(f"✅ Dentro de lo esperado ({deviation:.2f}%)")
