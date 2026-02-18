"""English docstring: Main entry point for the Sentinel dashboard.

---
Docstring en español: Punto de entrada principal para el dashboard Sentinel.
"""

from __future__ import annotations

import streamlit as st

from sentinel.dashboard.components.department_tab import render_department_tab
from sentinel.dashboard.components.integrity_tab import render_integrity_tab
from sentinel.dashboard.components.overview import render_overview
from sentinel.dashboard.components.pdf_generator import create_pdf
from sentinel.dashboard.components.temporal_tab import render_temporal_tab
from sentinel.dashboard.data_loader import load_data
from sentinel.dashboard.filters import filtrar_df
from datetime import date

from sentinel.dashboard.utils.constants import PARTIES, DEPARTMENTS


def _normalize_date_range(date_range: tuple | list | None) -> tuple[date, date]:
    """English docstring: Normalize date inputs to a safe (start, end) tuple.

    Args:
        date_range: Raw date input from Streamlit.

    Returns:
        Tuple with start and end dates (fallback to today).
    ---
    Docstring en español: Normaliza entradas de fecha a una tupla segura (inicio, fin).

    Args:
        date_range: Entrada de fecha cruda desde Streamlit.

    Returns:
        Tupla con fechas de inicio y fin (fallback a hoy).
    """

    today = date.today()
    if not date_range:
        return today, today
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        return date_range[0], date_range[1]
    if isinstance(date_range, (list, tuple)) and len(date_range) == 1:
        return date_range[0], date_range[0]
    if isinstance(date_range, tuple):
        return date_range
    return today, today


def _render_sidebar(df) -> tuple[bool, list[str], list[str], tuple[date, date]]:
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
        depto_options = (
            ["Todos"] + sorted(df["departamento"].unique())
            if not df.empty
            else ["Todos"] + DEPARTMENTS
        )
        selected_departments = st.multiselect(
            "Departamentos", depto_options, default=["Todos"]
        )

        party_options = (
            [p for p in PARTIES if p in df.columns] if not df.empty else PARTIES
        )
        default_parties = party_options[:]
        selected_parties = st.multiselect(
            "Partidos/Candidatos", party_options, default=default_parties
        )

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

    return (
        simple_mode,
        selected_departments,
        selected_parties,
        _normalize_date_range(date_range),
    )


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
        st.markdown("""
---
¿Quieres revisar el código y la metodología? Visita nuestro repositorio:
[https://github.com/userf8a2c4/sentinel](https://github.com/userf8a2c4/sentinel)
""")
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
        st.markdown("""
---
¿Quieres revisar el código y la metodología? Visita nuestro repositorio:
[https://github.com/userf8a2c4/sentinel](https://github.com/userf8a2c4/sentinel)
""")
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

    # Footer invitation. / Invitación en el footer.
    st.markdown("""
---
¿Quieres revisar el código y la metodología? Visita nuestro repositorio:
[https://github.com/userf8a2c4/sentinel](https://github.com/userf8a2c4/sentinel)
""")
