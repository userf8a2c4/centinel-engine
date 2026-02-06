"""Dashboard Streamlit para C.E.N.T.I.N.E.L. Honduras 2029."""

from __future__ import annotations

from datetime import datetime
import json
from typing import Dict, List, Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils import (
    DEPARTMENT_COORDS,
    DEPARTMENTS,
    ParsedResult,
    build_export_bundle,
    build_locations,
    build_metrics,
    load_payload,
    parse_cne_payload,
)

try:
    from streamlit_autorefresh import st_autorefresh
except ModuleNotFoundError:
    st_autorefresh = None


st.set_page_config(
    page_title="CENTINEL – Auditor Electoral Honduras 2029",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded",
)


def inject_css() -> None:
    """Inyecta estilos CSS para tema oscuro estilo bento grid."""

    st.markdown(
        """
        <style>
            :root {
                color-scheme: dark;
            }
            html, body, [class*="css"] {
                font-family: 'Inter', 'Segoe UI', sans-serif;
                background-color: #0F0F0F;
                color: #E0E0E0;
            }
            .main {
                background-color: #0F0F0F;
            }
            .centinel-header {
                position: sticky;
                top: 0;
                z-index: 999;
                background: linear-gradient(180deg, #0F0F0F 0%, #0F0F0F 70%, rgba(15,15,15,0));
                padding-bottom: 0.5rem;
            }
            .bento-card {
                background: #141414;
                border: 1px solid #333333;
                border-radius: 16px;
                padding: 1rem 1.2rem;
                box-shadow: 0 8px 20px rgba(0,0,0,0.35);
            }
            .bento-card h3 {
                color: #E0E0E0;
                margin-bottom: 0.5rem;
            }
            .accent-cyan { color: #00D4FF; }
            .accent-red { color: #FF6B6B; }
            .accent-green { color: #4CAF50; }
            .small-muted { color: #9E9E9E; font-size: 0.85rem; }
            .alert-pill {
                display: inline-block;
                padding: 0.15rem 0.6rem;
                border-radius: 999px;
                font-size: 0.75rem;
                margin-right: 0.4rem;
                border: 1px solid #333;
            }
            .alert-high { background-color: rgba(255,107,107,0.15); color: #FF6B6B; }
            .alert-med { background-color: rgba(0,212,255,0.12); color: #00D4FF; }
            .alert-low { background-color: rgba(76,175,80,0.15); color: #4CAF50; }
            .footer {
                text-align: center;
                padding: 2rem 0 1rem 0;
                color: #7A7A7A;
                font-size: 0.85rem;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header(last_update: Optional[datetime]) -> None:
    """Renderiza el header principal con metadata y control de refresco."""

    st.markdown("<div class='centinel-header'>", unsafe_allow_html=True)
    col_title, col_meta, col_button = st.columns([2.5, 1.5, 1])
    with col_title:
        st.markdown(
            "<h1 class='accent-cyan'>CENTINEL – Auditor Electoral Honduras 2029</h1>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div class='small-muted'>Auditoría automática con evidencia cuantitativa.</div>",
            unsafe_allow_html=True,
        )
    with col_meta:
        if last_update:
            st.markdown(
                f"<div class='small-muted'>Última actualización<br><strong>{last_update}</strong></div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<div class='small-muted'>Última actualización<br><strong>Sin datos</strong></div>",
                unsafe_allow_html=True,
            )
    with col_button:
        if st.button("Actualizar ahora", use_container_width=True):
            st.cache_data.clear()
            st.session_state["manual_refresh"] = datetime.utcnow().isoformat()
            st.experimental_rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def load_all_data(source: str, base: str) -> tuple[Optional[ParsedResult], List[ParsedResult], Dict[str, str]]:
    """Carga los 19 JSON y los normaliza."""

    locations = build_locations(source, base)
    errors: Dict[str, str] = {}
    national: Optional[ParsedResult] = None
    departments: List[ParsedResult] = []

    for dept, location in locations.items():
        payload, error = load_payload(source, location)
        if error:
            errors[dept] = error
            continue
        parsed = parse_cne_payload(payload, dept)
        if dept == "Nacional":
            national = parsed
        else:
            departments.append(parsed)
    return national, departments, errors


@st.cache_data(show_spinner=False, ttl=300)
def cached_load(source: str, base: str, _refresh_key: str) -> tuple[Optional[ParsedResult], List[ParsedResult], Dict[str, str]]:
    """Carga con cache y expiración de 5 minutos."""

    return load_all_data(source, base)


def render_alerts(alerts) -> None:
    """Renderiza el panel de alertas."""

    st.markdown("<div class='bento-card'>", unsafe_allow_html=True)
    st.markdown("<h3>Alertas críticas</h3>", unsafe_allow_html=True)
    if not alerts:
        st.markdown("<div class='accent-green'>Sin anomalías críticas detectadas.</div>")
    else:
        for alert in alerts[:6]:
            severity_class = {
                "alta": "alert-high",
                "media": "alert-med",
                "baja": "alert-low",
            }.get(alert.severity, "alert-low")
            st.markdown(
                f"<div><span class='alert-pill {severity_class}'>{alert.rule}</span>{alert.message}</div>",
                unsafe_allow_html=True,
            )
    st.markdown("</div>", unsafe_allow_html=True)


def plot_national_results(national: ParsedResult) -> go.Figure:
    """Crea gráfico de resultados nacionales."""

    df = national.candidates.copy()
    if df.empty:
        return go.Figure()
    df["percent"] = df["votos"] / df["votos"].sum() * 100
    fig = px.pie(
        df,
        names="candidato",
        values="votos",
        hole=0.55,
        color_discrete_sequence=px.colors.sequential.Blues,
    )
    fig.update_traces(textinfo="label+percent")
    fig.update_layout(
        template="plotly_dark",
        height=340,
        margin=dict(t=20, b=20, l=20, r=20),
    )
    return fig


def plot_turnout_map(turnout_df: pd.DataFrame) -> go.Figure:
    """Crea mapa simple de turnout por departamento."""

    if turnout_df.empty:
        return go.Figure()
    df = turnout_df.copy()
    df["lat"] = df["departamento"].map(lambda d: DEPARTMENT_COORDS.get(d, (0, 0))[0])
    df["lon"] = df["departamento"].map(lambda d: DEPARTMENT_COORDS.get(d, (0, 0))[1])
    fig = px.scatter_geo(
        df,
        lat="lat",
        lon="lon",
        color="turnout",
        size="turnout",
        hover_name="departamento",
        color_continuous_scale="Turbo",
    )
    fig.update_layout(
        template="plotly_dark",
        height=280,
        margin=dict(t=10, b=0, l=0, r=0),
        geo=dict(
            scope="north america",
            center=dict(lat=14.8, lon=-86.8),
            projection_scale=8,
            showland=True,
            landcolor="#0F0F0F",
            showcountries=False,
            showcoastlines=False,
        ),
    )
    return fig


def plot_benford(benford_result) -> go.Figure:
    """Grafica Benford para un candidato."""

    digits = list(range(1, 10))
    fig = go.Figure()
    fig.add_trace(
        go.Bar(x=digits, y=benford_result.expected, name="Esperado", marker_color="#00D4FF")
    )
    fig.add_trace(
        go.Scatter(
            x=digits,
            y=benford_result.observed,
            mode="lines+markers",
            name="Observado",
            marker_color="#FF6B6B",
        )
    )
    fig.update_layout(
        template="plotly_dark",
        height=260,
        margin=dict(t=10, b=20, l=20, r=20),
        yaxis_title="Frecuencia",
    )
    return fig


def plot_correlation_heatmap(corr_df: pd.DataFrame) -> go.Figure:
    """Heatmap de correlación entre departamentos."""

    if corr_df.empty:
        return go.Figure()
    fig = px.imshow(
        corr_df,
        color_continuous_scale="RdBu",
        zmin=-1,
        zmax=1,
        aspect="auto",
    )
    fig.update_layout(
        template="plotly_dark",
        height=280,
        margin=dict(t=20, b=20, l=20, r=20),
    )
    return fig


def plot_null_turnout(null_turnout_df: pd.DataFrame) -> go.Figure:
    """Scatter nulos vs turnout con regresión."""

    if null_turnout_df.empty:
        return go.Figure()
    fig = px.scatter(
        null_turnout_df,
        x="turnout",
        y="null_rate",
        color="outlier",
        hover_name="departamento",
        color_discrete_map={True: "#FF6B6B", False: "#00D4FF"},
    )
    fig.update_layout(
        template="plotly_dark",
        height=260,
        margin=dict(t=20, b=20, l=20, r=20),
        xaxis_title="Turnout",
        yaxis_title="Nulos + inválidos",
    )
    return fig


def main() -> None:
    """Función principal del dashboard."""

    inject_css()

    st.sidebar.markdown("## Configuración de datos")
    source = st.sidebar.radio("Fuente", ["url", "local"], format_func=lambda x: "URLs" if x == "url" else "Carpeta local")
    base = st.sidebar.text_input(
        "Base",
        value="https://datos.cne.gob.hn/elecciones/2029",
        help="URL base o carpeta local con los 19 JSON.",
    )
    department_selected = st.sidebar.selectbox("Departamento", ["Nacional"] + DEPARTMENTS)

    refresh_key = st.session_state.get("manual_refresh", "")
    national, departments, errors = cached_load(source, base, refresh_key)

    if st_autorefresh:
        st_autorefresh(interval=300000, key="auto_refresh")
    else:
        last_check = st.session_state.get("last_auto_check")
        now = datetime.utcnow()
        if last_check:
            elapsed = (now - last_check).total_seconds()
            if elapsed >= 300:
                st.session_state["last_auto_check"] = now
                st.experimental_rerun()
        else:
            st.session_state["last_auto_check"] = now

    last_update = None
    if national and national.timestamp:
        last_update = national.timestamp
    elif departments:
        last_update = max([dept.timestamp for dept in departments if dept.timestamp], default=None)

    render_header(last_update)

    if errors:
        st.warning("Algunos archivos no se pudieron cargar:")
        st.json(errors)

    if not national or not departments:
        st.error("No hay suficientes datos para renderizar el dashboard.")
        return

    metrics = build_metrics(national, departments)

    col_left, col_right = st.columns([2.2, 1.2])
    with col_left:
        st.markdown("<div class='bento-card'>", unsafe_allow_html=True)
        st.markdown("<h3>Resultados nacionales actuales</h3>", unsafe_allow_html=True)
        st.plotly_chart(plot_national_results(national), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_right:
        st.markdown("<div class='bento-card'>", unsafe_allow_html=True)
        st.markdown("<h3>Turnout nacional & mapa</h3>", unsafe_allow_html=True)
        turnout = metrics.turnout_df["turnout"].mean() if not metrics.turnout_df.empty else 0
        st.markdown(
            f"<div><strong class='accent-cyan'>{turnout:.1%}</strong> turnout promedio.</div>",
            unsafe_allow_html=True,
        )
        if not metrics.turnout_df.empty:
            max_row = metrics.turnout_df.loc[metrics.turnout_df["turnout"].idxmax()]
            min_row = metrics.turnout_df.loc[metrics.turnout_df["turnout"].idxmin()]
            st.markdown(
                f"<div class='small-muted'>Mayor: {max_row['departamento']} ({max_row['turnout']:.1%})<br>"
                f"Menor: {min_row['departamento']} ({min_row['turnout']:.1%})</div>",
                unsafe_allow_html=True,
            )
        st.plotly_chart(plot_turnout_map(metrics.turnout_df), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    col_alerts, col_benford = st.columns([1.6, 1.4])
    with col_alerts:
        render_alerts(metrics.alerts)

    with col_benford:
        st.markdown("<div class='bento-card'>", unsafe_allow_html=True)
        st.markdown("<h3>Ley de Benford</h3>", unsafe_allow_html=True)
        candidate_options = sorted(metrics.benford_results.keys())
        candidate = st.selectbox("Candidato", candidate_options) if candidate_options else None
        if candidate:
            benford_result = metrics.benford_results[candidate]
            st.plotly_chart(plot_benford(benford_result), use_container_width=True)
            st.markdown(
                f"<div class='small-muted'>Chi²: {benford_result.chi2:.2f} | p-value: {benford_result.p_value:.3f}</div>",
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

    col_consistency, col_nulls = st.columns([1.2, 1.2])
    with col_consistency:
        st.markdown("<div class='bento-card'>", unsafe_allow_html=True)
        st.markdown("<h3>Consistencia nacional vs departamental</h3>", unsafe_allow_html=True)
        st.dataframe(metrics.consistency_df, use_container_width=True, height=220)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_nulls:
        st.markdown("<div class='bento-card'>", unsafe_allow_html=True)
        st.markdown("<h3>Nulos vs turnout</h3>", unsafe_allow_html=True)
        st.plotly_chart(plot_null_turnout(metrics.null_turnout_df), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    col_corr, col_department = st.columns([1.6, 0.8])
    with col_corr:
        st.markdown("<div class='bento-card'>", unsafe_allow_html=True)
        st.markdown("<h3>Correlaciones departamentales</h3>", unsafe_allow_html=True)
        st.plotly_chart(plot_correlation_heatmap(metrics.correlation_df), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_department:
        st.markdown("<div class='bento-card'>", unsafe_allow_html=True)
        st.markdown("<h3>Vista departamental</h3>", unsafe_allow_html=True)
        selected = next((d for d in metrics.departments if d.department == department_selected), None)
        if department_selected == "Nacional":
            selected = metrics.national
        if selected:
            st.markdown(
                f"<div><strong>{selected.department}</strong></div>", unsafe_allow_html=True
            )
            st.markdown(
                f"<div class='small-muted'>Registrados: {selected.registered:,}</div>",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"<div class='small-muted'>Válidos: {selected.total_valid:,}</div>",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"<div class='small-muted'>Nulos: {selected.null_votes:,} | Inválidos: {selected.invalid_votes:,}</div>",
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='bento-card'>", unsafe_allow_html=True)
    st.markdown("<h3>Exportar reporte</h3>", unsafe_allow_html=True)
    metrics_df, alerts_df = build_export_bundle(metrics)
    export_json = {
        "generated_at": datetime.utcnow().isoformat(),
        "consistency": metrics_df.to_dict(orient="records"),
        "alerts": alerts_df.to_dict(orient="records"),
    }
    st.download_button(
        "Descargar JSON",
        data=json.dumps(export_json, ensure_ascii=False, indent=2),
        file_name="centinel_report.json",
        mime="application/json",
    )
    st.download_button(
        "Descargar CSV",
        data=metrics_df.to_csv(index=False).encode("utf-8"),
        file_name="centinel_metrics.csv",
        mime="text/csv",
    )
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(
        """
        <div class="footer">
            CENTINEL v1.0 · Auditoría automatizada · <a href="https://github.com/centinel" target="_blank">GitHub</a><br>
            Disclaimer: Datos con fines de auditoría; verificar siempre con el CNE.
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
