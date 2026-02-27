"""ES: Utilidades de visualización científica para el dashboard Streamlit.

EN: Scientific-grade visualization utilities for the Streamlit dashboard.

This module centralizes:
- ES: Cálculo de filtros cruzados con caché.
- EN: Cached cross-filter calculations.
- ES: Figuras Plotly para Benford y timeline de cambios.
- EN: Plotly figures for Benford and change timeline.
"""

from __future__ import annotations

from math import sqrt
from statistics import NormalDist

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


@st.cache_data(show_spinner=False)
def get_cross_filter_options(df: pd.DataFrame) -> dict[str, list[str]]:
    """ES: Construye opciones únicas de filtros cruzados para departamento, hora y regla.

    EN: Build unique cross-filter options for department, hour, and rule type.

    Args:
        df: ES: DataFrame base del dashboard. EN: Base dashboard DataFrame.

    Returns:
        Dict con listas ordenadas para cada selector del panel lateral.
        Dict with sorted lists for each sidebar selector.
    """
    if df.empty:
        return {"departments": ["Todos"], "hours": [], "rule_types": []}

    work_df = df.copy()
    if "hour" not in work_df.columns:
        work_df["hour"] = pd.to_datetime(work_df.get("timestamp"), errors="coerce", utc=True).dt.strftime("%H:%M")

    departments = sorted([str(item) for item in work_df.get("department", pd.Series(dtype=str)).dropna().unique()])
    hours = sorted([str(item) for item in work_df.get("hour", pd.Series(dtype=str)).dropna().unique()])

    if "rule_type" in work_df.columns:
        rule_types = sorted([str(item) for item in work_df["rule_type"].dropna().unique()])
    else:
        # ES: Reglas sintéticas mínimas cuando el dataset no trae etiqueta explícita.
        # EN: Minimal synthetic rules when dataset has no explicit label.
        rule_types = ["Benford 1er dígito", "Delta negativo", "Outlier de crecimiento"]

    return {"departments": ["Todos"] + departments, "hours": hours, "rule_types": rule_types}


@st.cache_data(show_spinner=False)
def apply_cross_filters(
    df: pd.DataFrame,
    selected_department: str,
    selected_hours: list[str],
    selected_rule_types: list[str],
    anomalies_only: bool,
) -> pd.DataFrame:
    """ES: Aplica filtros cruzados (departamento, hora, tipo de regla y modo anomalías).

    EN: Apply cross-filters (department, hour, rule type, and anomalies-only mode).

    The function is cached to keep the dashboard responsive under heavy interaction.
    """
    if df.empty:
        return df.copy()

    filtered_df = df.copy()

    if selected_department != "Todos":
        filtered_df = filtered_df[filtered_df["department"] == selected_department]

    if "hour" not in filtered_df.columns:
        filtered_df["hour"] = pd.to_datetime(filtered_df.get("timestamp"), errors="coerce", utc=True).dt.strftime("%H:%M")

    if selected_hours:
        filtered_df = filtered_df[filtered_df["hour"].isin(selected_hours)]

    if "rule_type" not in filtered_df.columns:
        # ES: Derivación básica de tipo de regla para habilitar multiselect funcional.
        # EN: Basic rule-type derivation to keep multiselect functional.
        filtered_df["rule_type"] = filtered_df.apply(
            lambda row: "Delta negativo"
            if row.get("delta", 0) < 0
            else ("Outlier de crecimiento" if row.get("status") == "REVISAR" else "Benford 1er dígito"),
            axis=1,
        )

    if selected_rule_types:
        filtered_df = filtered_df[filtered_df["rule_type"].isin(selected_rule_types)]

    if anomalies_only:
        filtered_df = filtered_df[filtered_df["status"].isin(["ALERTA", "REVISAR"])]

    return filtered_df


def compute_benford_statistics(benford_df: pd.DataFrame, sample_size: int) -> tuple[float, float]:
    """ES: Calcula p-value aproximado y z-score máximo para Benford 1er dígito.

    EN: Compute approximate p-value and maximum z-score for first-digit Benford fit.

    Notes / Notas:
    - ES: Usa residuales estandarizados por dígito: z_i = (obs-exp)/sqrt(exp*(1-exp)/N).
    - EN: Uses per-digit standardized residuals: z_i = (obs-exp)/sqrt(exp*(1-exp)/N).
    - ES: El p-value se aproxima con una prueba bilateral sobre el z-score máximo absoluto.
    - EN: The p-value is approximated as a two-tailed probability over the max absolute z-score.
    """
    if benford_df.empty or sample_size <= 0:
        return 1.0, 0.0

    work_df = benford_df.copy().sort_values("digit")
    expected = (work_df["expected"] / 100.0).astype(float)
    observed = (work_df["observed"] / 100.0).astype(float)

    denominator = (expected * (1 - expected) / float(sample_size)).apply(lambda value: sqrt(max(value, 1e-12)))
    z_scores = (observed - expected) / denominator
    max_abs_z = float(z_scores.abs().max())

    p_value = float(2.0 * (1.0 - NormalDist().cdf(max_abs_z)))
    return max(min(p_value, 1.0), 0.0), max_abs_z


def make_benford_first_digit_figure(
    benford_df: pd.DataFrame,
    p_value: float,
    z_score: float,
    sample_size: int,
    institutional_colors: dict[str, str],
) -> go.Figure:
    """ES: Genera gráfico científico de Benford (1er dígito) con barras observadas vs esperadas.

    EN: Create scientific-grade Benford (first-digit) chart with observed vs expected bars.

    Includes:
    - ES: Anotaciones de p-value y z-score.
    - EN: p-value and z-score annotations.
    - ES: Tooltips matemáticos explicativos.
    - EN: Explanatory mathematical tooltips.
    """
    work_df = benford_df.copy().sort_values("digit")
    test_explanation = (
        "Benford’s Law test – p-value = "
        f"{p_value:.3f} → {'evidencia moderada de anomalía' if p_value < 0.05 else 'sin evidencia fuerte de anomalía'}"
    )

    observed_hover = [
        (
            f"Dígito {int(row.digit)}<br>"
            f"Observado: {row.observed:.2f}%<br>"
            f"Esperado: {row.expected:.2f}%<br>"
            f"N={sample_size}<br>{test_explanation}"
        )
        for row in work_df.itertuples(index=False)
    ]

    expected_hover = [
        (
            f"Dígito {int(row.digit)}<br>"
            f"Esperado Benford: {row.expected:.2f}%<br>"
            f"Modelo: P(d)=log10(1+1/d)<br>{test_explanation}"
        )
        for row in work_df.itertuples(index=False)
    ]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=work_df["digit"],
            y=work_df["observed"],
            name="Observado / Observed",
            marker_color=institutional_colors["observed"],
            hovertemplate="%{customdata}<extra></extra>",
            customdata=observed_hover,
        )
    )
    fig.add_trace(
        go.Bar(
            x=work_df["digit"],
            y=work_df["expected"],
            name="Esperado / Expected",
            marker_color=institutional_colors["expected"],
            opacity=0.75,
            hovertemplate="%{customdata}<extra></extra>",
            customdata=expected_hover,
        )
    )

    fig.update_layout(
        barmode="group",
        title="Benford 1er dígito / Benford First Digit",
        xaxis_title="Dígito / Digit",
        yaxis_title="Porcentaje (%)",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend_title="Serie",
        margin=dict(l=20, r=20, t=70, b=20),
    )
    fig.add_annotation(
        x=0.01,
        y=1.16,
        xref="paper",
        yref="paper",
        text=f"p-value = {p_value:.3f} | z-score = {z_score:.2f}",
        showarrow=False,
        font=dict(color=institutional_colors["annotation"], size=13),
        align="left",
    )
    return fig


def make_changes_timeline_figure(
    timeline_df: pd.DataFrame,
    institutional_colors: dict[str, str],
    alert_threshold: float,
) -> go.Figure:
    """ES: Construye timeline de evolución de cambios con banda de confianza y alertas.

    EN: Build change-evolution timeline with confidence band and shaded alert zones.

    Mathematical details:
    - ES: Usa media móvil + desviación estándar para banda de confianza aproximada.
    - EN: Uses moving mean + standard deviation for an approximate confidence band.
    """
    if timeline_df.empty:
        return go.Figure()

    work_df = timeline_df.copy()
    work_df["timestamp_dt"] = pd.to_datetime(work_df["timestamp"], errors="coerce", utc=True)
    work_df = work_df.sort_values("timestamp_dt")

    work_df["changes_mean"] = work_df["changes"].rolling(window=4, min_periods=1).mean()
    work_df["changes_std"] = work_df["changes"].rolling(window=4, min_periods=1).std().fillna(0.0)
    work_df["ci_upper"] = work_df["changes_mean"] + 1.96 * work_df["changes_std"]
    work_df["ci_lower"] = (work_df["changes_mean"] - 1.96 * work_df["changes_std"]).clip(lower=0)

    hover_text = [
        (
            f"Hora: {ts}<br>Cambios: {chg:.2f}<br>"
            f"IC95%: [{lo:.2f}, {hi:.2f}]<br>"
            f"Umbral alerta: {alert_threshold:.2f}"
        )
        for ts, chg, lo, hi in zip(
            work_df["timestamp_dt"].dt.strftime("%Y-%m-%d %H:%M UTC"),
            work_df["changes"],
            work_df["ci_lower"],
            work_df["ci_upper"],
            strict=False,
        )
    ]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=work_df["timestamp_dt"],
            y=work_df["ci_upper"],
            mode="lines",
            line=dict(width=0),
            showlegend=False,
            hoverinfo="skip",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=work_df["timestamp_dt"],
            y=work_df["ci_lower"],
            mode="lines",
            line=dict(width=0),
            fill="tonexty",
            fillcolor=institutional_colors["confidence_band"],
            name="IC95%",
            hoverinfo="skip",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=work_df["timestamp_dt"],
            y=work_df["changes"],
            mode="lines+markers",
            name="Cambios observados",
            line=dict(color=institutional_colors["line"], width=3),
            marker=dict(size=7),
            customdata=hover_text,
            hovertemplate="%{customdata}<extra></extra>",
        )
    )

    fig.add_hrect(
        y0=alert_threshold,
        y1=max(float(work_df["changes"].max()), float(alert_threshold)) * 1.15,
        fillcolor=institutional_colors["alert_zone"],
        opacity=0.17,
        line_width=0,
        annotation_text="Zona de alerta / Alert zone",
        annotation_position="top left",
    )

    fig.update_layout(
        title="Evolución de cambios / Change Evolution Timeline",
        xaxis_title="Tiempo",
        yaxis_title="Cambios",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=20, r=20, t=50, b=20),
        legend_title="Series",
    )
    return fig
