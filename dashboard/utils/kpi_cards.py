"""Utilidades para tarjetas KPI del dashboard C.E.N.T.I.N.E.L.

ES: Este módulo centraliza la construcción de tarjetas KPI institucionales
con diseño compatible con observación electoral internacional.
EN: This module centralizes institutional KPI card rendering compatible
with international election observation reporting standards.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Iterable

import altair as alt
import pandas as pd
import streamlit as st


# ES: Bandera para inyectar estilos una sola vez por ejecución.
# EN: Flag to inject styles only once per app execution.
_STYLES_INJECTED = False


def _inject_kpi_styles() -> None:
    """Inyecta CSS premium para las tarjetas KPI / Inject premium KPI card CSS."""
    global _STYLES_INJECTED
    if _STYLES_INJECTED:
        return

    st.markdown(
        """
<style>
.kpi-card-shell {
    background: linear-gradient(165deg, rgba(14,26,50,.96), rgba(10,20,40,.92));
    border: 1px solid rgba(148,163,184,.24);
    border-radius: 16px;
    padding: 14px 16px 8px 16px;
    box-shadow: 0 8px 30px rgba(0,0,0,.25);
    min-height: 278px;
}
.kpi-title {
    display:flex;
    justify-content:space-between;
    align-items:flex-start;
    color:#e2e8f0;
    font-size:.95rem;
    line-height:1.2rem;
    font-weight:700;
}
.kpi-title small {
    color:#94a3b8;
    font-weight:500;
}
.kpi-tooltip {
    color:#00A3E0;
    border:1px solid rgba(0,163,224,.45);
    border-radius:999px;
    width:22px;
    height:22px;
    display:inline-flex;
    align-items:center;
    justify-content:center;
    font-size:.8rem;
}
.kpi-subtitle {
    color:#94a3b8;
    font-size:.78rem;
    margin-top:2px;
    margin-bottom:2px;
}
.kpi-source {
    color:#64748b;
    font-size:.72rem;
    margin-top:3px;
}
/* ES: Personalización visual de st.metric / EN: st.metric visual customization */
div[data-testid="stMetric"] {
    background: transparent;
    border: none;
    padding: .2rem 0 0 0;
}
div[data-testid="stMetricValue"] {
    font-size: 2.05rem;
    color:#f8fafc;
    font-weight:800;
    line-height:1.0;
}
div[data-testid="stMetricDelta"] {
    font-size:.95rem;
    font-weight:700;
}
.cne-badge {
    display:inline-block;
    border-radius:999px;
    padding:6px 12px;
    font-size:.8rem;
    font-weight:700;
    margin: .35rem 0 .9rem 0;
}
</style>
        """,
        unsafe_allow_html=True,
    )
    _STYLES_INJECTED = True


def _format_delta(delta: float) -> tuple[str, str]:
    """ES: Formatea delta y retorna texto + color semántico.

    EN: Format delta and return text + semantic color.
    """
    arrow = "↑" if delta > 0 else "↓" if delta < 0 else "→"
    color = "normal" if delta > 0 else "inverse" if delta < 0 else "off"
    return f"{arrow} {delta:+.2f}%", color


def create_cne_update_badge(latest_timestamp: datetime | None) -> None:
    """Renderiza badge dinámico de actualización CNE / Render dynamic CNE update badge."""
    _inject_kpi_styles()
    if latest_timestamp is None:
        text = "Datos del CNE – Sin timestamp disponible"
        bg = "rgba(239,68,68,.16)"
        border = "rgba(239,68,68,.45)"
        color = "#ef4444"
    else:
        now = datetime.now(timezone.utc)
        delta_min = max(0, math.floor((now - latest_timestamp).total_seconds() / 60))
        if delta_min <= 15:
            bg, border, color = "rgba(0,200,83,.15)", "rgba(0,200,83,.45)", "#22c55e"
        elif delta_min <= 45:
            bg, border, color = "rgba(255,152,0,.15)", "rgba(255,152,0,.45)", "#f59e0b"
        else:
            bg, border, color = "rgba(239,68,68,.16)", "rgba(239,68,68,.45)", "#ef4444"
        text = f"Datos del CNE – Actualizado hace {delta_min} minutos"

    st.markdown(
        f'<span class="cne-badge" style="background:{bg}; border:1px solid {border}; color:{color};">{text}</span>',
        unsafe_allow_html=True,
    )


def create_kpi_card(
    title_es: str,
    title_en: str,
    value: str,
    delta: float,
    spark_data: Iterable[float] | pd.Series,
    tooltip_text: str,
    subtitle_text: str = "",
) -> None:
    """Renderiza una tarjeta KPI reutilizable con sparkline y tooltip.

    ES: Crea una tarjeta KPI de estilo institucional con valor principal,
    variación porcentual semántica, subtítulo explicativo y micro-gráfico.
    EN: Build an institutional KPI card with prominent value, semantic
    percentage change, explanatory subtitle and inline sparkline.
    """
    _inject_kpi_styles()

    # ES: Normalizar vector para asegurar 12 puntos históricos.
    # EN: Normalize vector to ensure 12 historical points.
    spark_values = list(spark_data)
    if not spark_values:
        spark_values = [0.0] * 12
    if len(spark_values) < 12:
        spark_values = ([spark_values[0]] * (12 - len(spark_values))) + spark_values
    else:
        spark_values = spark_values[-12:]

    delta_text, _ = _format_delta(delta)

    st.markdown(
        f"""
<div class="kpi-card-shell">
  <div class="kpi-title">
    <div>{title_es}<br/><small>{title_en}</small></div>
    <span class="kpi-tooltip" title="{tooltip_text}">ⓘ</span>
  </div>
  <div class="kpi-subtitle">{subtitle_text}</div>
</div>
        """,
        unsafe_allow_html=True,
    )

    # ES: st.metric con delta semántico; el CSS anterior lo amplifica visualmente.
    # EN: st.metric with semantic delta; CSS above scales up visual hierarchy.
    st.metric(label="Valor KPI", value=value, delta=delta_text, delta_color="normal", label_visibility="collapsed")

    spark_df = pd.DataFrame({"idx": list(range(len(spark_values))), "value": spark_values})
    chart = (
        alt.Chart(spark_df)
        .mark_line(color="#00A3E0", strokeWidth=2.4)
        .encode(x=alt.X("idx:Q", axis=None), y=alt.Y("value:Q", axis=None))
        .properties(height=42)
    )
    st.altair_chart(chart, width="stretch")

    st.markdown(f'<div class="kpi-source">{tooltip_text}</div>', unsafe_allow_html=True)
