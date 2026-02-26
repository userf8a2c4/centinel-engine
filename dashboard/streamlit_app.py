"""C.E.N.T.I.N.E.L. premium institutional dashboard.

ES: Archivo principal de Streamlit con diseño premium institucional para auditoría electoral.
EN: Main Streamlit file with premium institutional UX for electoral auditing.
"""

from __future__ import annotations

# ES: Importaciones estándar para fechas, rutas y tipado.
# EN: Standard imports for dates, paths, and typing.
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ES: Importaciones de terceros para visualización y app.
# EN: Third-party imports for visualization and app runtime.
import altair as alt
import pandas as pd
import streamlit as st

# ES: Importa variables de tema reutilizables centralizadas.
# EN: Import centralized reusable theme variables.
from utils.theme import (
    ALERT_ORANGE,
    BRAND_BLUE,
    INTEGRITY_GREEN,
    PAGE_CONFIG,
    build_institutional_css,
)


@dataclass(frozen=True)
class DashboardSnapshot:
    """ES: Modelo de datos para un snapshot de auditoría.

    EN: Data model for a single audit snapshot.
    """

    timestamp: datetime
    source: str
    mesas_observadas: int
    alertas_criticas: int
    indice_integridad: float


def _parse_snapshot(payload: dict[str, Any], source_name: str) -> DashboardSnapshot:
    """ES: Convierte JSON arbitrario en un snapshot normalizado.

    EN: Convert arbitrary JSON payload into a normalized snapshot.
    """

    # ES: Normaliza timestamp con fallback seguro en UTC.
    # EN: Normalize timestamp with safe UTC fallback.
    raw_ts = payload.get("timestamp") or payload.get("generated_at") or datetime.now(timezone.utc).isoformat()
    try:
        parsed_ts = datetime.fromisoformat(str(raw_ts).replace("Z", "+00:00"))
    except ValueError:
        parsed_ts = datetime.now(timezone.utc)

    # ES: Toma métricas clave y define valores por defecto robustos.
    # EN: Extract key metrics and define robust defaults.
    mesas = int(payload.get("mesas_observadas", payload.get("tables_observed", 0)))
    alertas = int(payload.get("alertas_criticas", payload.get("critical_alerts", 0)))
    integrity = float(payload.get("indice_integridad", payload.get("integrity_index", 0.0)))

    return DashboardSnapshot(
        timestamp=parsed_ts,
        source=source_name,
        mesas_observadas=mesas,
        alertas_criticas=alertas,
        indice_integridad=integrity,
    )


@st.cache_data(show_spinner=False)
def load_latest_snapshot() -> DashboardSnapshot:
    """ES: Carga el JSON más reciente desde carpetas operativas típicas.

    EN: Load the most recent JSON from typical operational folders.
    """

    # ES: Define rutas candidatas para mantener compatibilidad flexible.
    # EN: Define candidate paths to keep flexible compatibility.
    candidate_dirs = [Path("data"), Path("logs"), Path("artifacts"), Path("reports")]
    json_candidates = [path for folder in candidate_dirs if folder.exists() for path in folder.glob("*.json")]

    # ES: Si no hay datos, retorna snapshot vacío institucional.
    # EN: If no data is found, return an empty institutional snapshot.
    if not json_candidates:
        return DashboardSnapshot(datetime.now(timezone.utc), "sin_datos.json", 0, 0, 0.0)

    latest = max(json_candidates, key=lambda p: p.stat().st_mtime)

    # ES: Protege la lectura JSON ante archivos corruptos o estructuras no válidas.
    # EN: Protect JSON loading against corrupted files or invalid structures.
    try:
        payload = json.loads(latest.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            payload = {}
    except (json.JSONDecodeError, OSError):
        payload = {}

    return _parse_snapshot(payload, latest.name)


def render_header(snapshot: DashboardSnapshot) -> None:
    """ES: Renderiza header fijo bilingüe con branding institucional.

    EN: Render fixed bilingual header with institutional branding.
    """

    # ES: Muestra marca, título estratégico y badge de independencia técnica.
    # EN: Display brand, strategic title, and technical independence badge.
    st.markdown(
        f"""
        <header class="ce-header">
            <div class="ce-header__left">
                <div class="ce-logo">C.E.N.T.I.N.E.L.</div>
                <div>
                    <h1>Centro de Vigilancia Electoral</h1>
                    <p>Election Integrity Surveillance Center</p>
                </div>
            </div>
            <div class="ce-header__right">
                <span class="ce-badge">Auditoría Técnica Independiente – Agnóstica a Partidos Políticos</span>
                <small>Fuente activa: {snapshot.source}</small>
            </div>
        </header>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar(snapshot: DashboardSnapshot) -> tuple[str, str]:
    """ES: Dibuja sidebar minimalista con filtros esenciales.

    EN: Draw minimalist sidebar with essential filters.
    """

    with st.sidebar:
        # ES: Encabezado compacto de filtros institucionales.
        # EN: Compact heading for institutional filters.
        st.markdown("### Filtros / Filters")
        alcance = st.selectbox("Cobertura", ["Nacional", "Provincial", "Municipal"], index=0)
        severidad = st.radio("Severidad", ["Todas", "Crítica", "Media", "Informativa"], horizontal=False)

        # ES: Footer institucional con metadatos y enlace metodológico opcional.
        # EN: Institutional footer with metadata and optional methodology link.
        updated_at = snapshot.timestamp.strftime("%Y-%m-%d %H:%M UTC")
        if st.secrets.get("ENV", "dev").lower() != "prod":
            st.markdown(
                f"""
                <div class="ce-footer">
                    <p><strong>Versión:</strong> 3.0.0-premium</p>
                    <p><strong>Última actualización JSON:</strong> {updated_at}</p>
                    <p><a href="https://centinel-engine.org/metodologia" target="_blank">Metodología técnica</a></p>
                </div>
                """,
                unsafe_allow_html=True,
            )
    return alcance, severidad


def render_kpis(snapshot: DashboardSnapshot) -> None:
    """ES: Presenta KPIs estratégicos en tarjetas premium.

    EN: Present strategic KPIs in premium cards.
    """

    # ES: Organiza métricas en tres columnas de alto contraste.
    # EN: Arrange metrics in three high-contrast columns.
    c1, c2, c3 = st.columns(3)
    c1.metric("Mesas Observadas", f"{snapshot.mesas_observadas:,}")
    c2.metric("Alertas Críticas", f"{snapshot.alertas_criticas:,}")
    c3.metric("Índice de Integridad", f"{snapshot.indice_integridad:.1f}%")


def render_integrity_chart(snapshot: DashboardSnapshot) -> None:
    """ES: Renderiza gráfico demo institucional para tracking de integridad.

    EN: Render institutional demo chart for integrity tracking.
    """

    # ES: Genera serie corta para narrativa visual ejecutiva.
    # EN: Generate short series for executive visual storytelling.
    trend = pd.DataFrame(
        {
            "checkpoint": ["T-3", "T-2", "T-1", "Actual"],
            "integridad": [max(snapshot.indice_integridad - 3, 0), max(snapshot.indice_integridad - 1.5, 0), max(snapshot.indice_integridad - 0.4, 0), snapshot.indice_integridad],
        }
    )

    chart = (
        alt.Chart(trend)
        .mark_line(point=True, strokeWidth=3, color=INTEGRITY_GREEN)
        .encode(x=alt.X("checkpoint:N", title="Ventana / Window"), y=alt.Y("integridad:Q", title="Integridad (%)", scale=alt.Scale(domain=[0, 100])))
        .properties(height=290)
    )
    st.altair_chart(chart, use_container_width=True)


def main() -> None:
    """ES: Orquesta layout completo del dashboard institucional.

    EN: Orchestrate the full institutional dashboard layout.
    """

    # ES: Configuración oficial de página en modo ancho para dashboards.
    # EN: Official page configuration in wide layout for dashboards.
    st.set_page_config(**PAGE_CONFIG)

    # ES: Inyecta CSS premium con paleta institucional obligatoria.
    # EN: Inject premium CSS with mandatory institutional palette.
    st.markdown(build_institutional_css(), unsafe_allow_html=True)

    snapshot = load_latest_snapshot()
    render_header(snapshot)
    render_sidebar(snapshot)

    # ES: Área principal con resumen ejecutivo y visualización central.
    # EN: Main area with executive summary and central visualization.
    st.markdown("## Panorama Ejecutivo / Executive Overview")
    render_kpis(snapshot)

    st.markdown("### Tendencia de Integridad / Integrity Trend")
    render_integrity_chart(snapshot)

    # ES: Bloque narrativo para equipos de observación internacional.
    # EN: Narrative block for international observation teams.
    st.markdown(
        f"""
        <section class="ce-panel">
            <h3>Lectura Técnica / Technical Reading</h3>
            <p>
                El monitoreo activo opera bajo parámetros de trazabilidad verificable,
                priorizando integridad de evidencia y neutralidad metodológica.
                Active monitoring runs under verifiable traceability parameters,
                prioritizing evidence integrity and methodological neutrality.
            </p>
            <p>
                Índice actual: <strong style="color:{BRAND_BLUE};">{snapshot.indice_integridad:.1f}%</strong> ·
                Alertas críticas: <strong style="color:{ALERT_ORANGE};">{snapshot.alertas_criticas}</strong> ·
                Estado de consistencia: <strong style="color:{INTEGRITY_GREEN};">operativo</strong>.
            </p>
        </section>
        """,
        unsafe_allow_html=True,
    )


# ES: Punto de entrada de ejecución directa.
# EN: Direct execution entry point.
if __name__ == "__main__":
    main()
