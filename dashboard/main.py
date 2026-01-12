"""English docstring: Main entry point for the Sentinel dashboard.

---
Docstring en español: Punto de entrada principal para el dashboard Sentinel.
"""

from __future__ import annotations

import streamlit as st

from dashboard.components.department_tab import render_department_tab
from dashboard.components.integrity_tab import render_integrity_tab
from dashboard.components.overview import render_overview
from dashboard.components.pdf_generator import create_pdf
from dashboard.components.temporal_tab import render_temporal_tab
from dashboard.data_loader import load_data
from dashboard.filters import filtrar_df
from dashboard.utils.constants import PARTIES, DEPARTMENTS


def _render_sidebar(df) -> tuple[bool, list[str], list[str], tuple]:
    """English docstring: Render sidebar controls and return selections.

    Args:
        df: Raw dataframe with snapshots.

    Returns:
        Tuple with (simple_mode, departments, parties, date_range).
    ---
    Docstring en español: Renderiza controles del sidebar y retorna selecciones.

    Args:
        df: Dataframe crudo con snapshots.

    Returns:
        Tupla con (modo_simple, departamentos, partidos, rango_fechas).
    """

    with st.sidebar:
        st.title("Sentinel 🇭🇳")
        st.markdown("**Monitoreo neutral de datos públicos del CNE**")
        st.caption("Solo hechos objetivos • Open-source")

        simple_mode = st.toggle("Modo Simple (solo resumen básico)", value=False)

        st.subheader("Filtros")
        depto_options = ["Todos"] + sorted(df["departamento"].unique()) if not df.empty else ["Todos"] + DEPARTMENTS
        selected_departments = st.multiselect("Departamentos", depto_options, default=["Todos"])

        party_options = [p for p in PARTIES if p in df.columns] if not df.empty else PARTIES
        default_parties = party_options[:]
        selected_parties = st.multiselect("Partidos/Candidatos", party_options, default=default_parties)

        if df.empty:
            date_range = st.date_input("Rango de fechas", [])
        else:
            min_date = df["timestamp"].min().date()
            max_date = df["timestamp"].max().date()
            date_range = st.date_input(
                "Rango de fechas",
                (min_date, max_date),
                min_value=min_date,
                max_value=max_date,
            )

    return simple_mode, selected_departments, selected_parties, date_range


def run_dashboard() -> None:
    """English docstring: Run the Sentinel Streamlit dashboard.

    ---
    Docstring en español: Ejecuta el dashboard de Streamlit de Sentinel.
    """

    st.set_page_config(
        page_title="Sentinel - Verificación Independiente CNE",
        page_icon="🇭🇳",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    df_raw = load_data()
    simple_mode, deptos, partidos, date_range = _render_sidebar(df_raw)

    df_filtered = filtrar_df(df_raw, deptos, partidos, date_range)

    # Overview always visible. / Resumen siempre visible.
    render_overview(df_filtered, partidos)

    if df_filtered.empty:
        st.warning("No hay datos en el rango seleccionado. Ajusta filtros.")
        return

    # PDF download button. / Botón de descarga PDF.
    pdf_bytes = create_pdf(df_filtered, deptos, partidos, date_range)
    st.download_button(
        "Descargar análisis como PDF",
        data=pdf_bytes,
        file_name="sentinel_analisis.pdf",
        mime="application/pdf",
    )

    if simple_mode:
        return

    st.markdown("---")
    tab_dept, tab_time, tab_integrity = st.tabs(
        ["📍 Por Departamento", "⏳ Evolución Temporal", "🔐 Integridad y Benford"]
    )

    with tab_dept:
        render_department_tab(df_filtered, partidos)

    with tab_time:
        render_temporal_tab(df_filtered, partidos)

    with tab_integrity:
        render_integrity_tab(df_filtered)
