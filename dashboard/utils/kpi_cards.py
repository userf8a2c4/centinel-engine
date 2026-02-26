"""
======================== INDICE / INDEX ========================
1. Descripcion general / Overview
2. Componentes KPI / KPI components
3. Sparklines con Altair / Altair sparklines
4. Badge de actualizacion / Update badge

======================== ESPANOL ========================
Archivo: `dashboard/utils/kpi_cards.py`.
Modulo de tarjetas KPI de grado institucional para informes de
observacion electoral internacional (OEA, UE, Carter Center).

Cada tarjeta incluye:
  - Valor principal grande con tipografia de impacto
  - Delta porcentual con flecha y color semantico
  - Subtitulo explicativo bilingue
  - Tooltip con definicion estadistica y fuente exacta del JSON CNE
  - Sparkline Altair incrustado con evolucion de las ultimas 12 horas

======================== ENGLISH ========================
File: `dashboard/utils/kpi_cards.py`.
Institutional-grade KPI card module for international electoral
observation reports (OEA, EU, Carter Center).

Each card includes:
  - Large primary value with impact typography
  - Percentage delta with arrow and semantic color
  - Bilingual explanatory subtitle
  - Tooltip with statistical definition and exact CNE JSON source
  - Embedded Altair sparkline with last 12 hours evolution
"""

from __future__ import annotations

import base64
import io
import math
from typing import Any

import altair as alt
import pandas as pd

# ES: Streamlit se importa de forma diferida para permitir tests unitarios
#     sin dependencia de streamlit instalado.
# EN: Streamlit is lazily imported to allow unit tests without requiring
#     streamlit to be installed.
try:
    import streamlit as st
except ModuleNotFoundError:  # pragma: no cover — ES: entorno de test / EN: test env
    st = None  # type: ignore[assignment]

# ES: Importar paleta institucional / EN: Import institutional palette
from dashboard.utils.theme import (
    ACCENT_BLUE,
    ACCENT_BLUE_BORDER,
    ACCENT_BLUE_MUTED,
    ALERT_ORANGE,
    ALERT_ORANGE_BG,
    ALERT_ORANGE_BORDER,
    BG_PANEL_SOFT,
    BG_SECONDARY,
    BORDER_DEFAULT,
    BORDER_RADIUS,
    BORDER_RADIUS_LG,
    BORDER_RADIUS_PILL,
    DANGER_RED,
    DANGER_RED_BG,
    DANGER_RED_BORDER,
    GREEN_BG,
    GREEN_BORDER,
    GREEN_INTEGRITY,
    SHADOW_DEFAULT,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


# =========================================================================
# ES: CSS especifico para la grilla KPI de grado institucional
# EN: CSS specific to the institutional-grade KPI grid
# =========================================================================
def get_kpi_grid_css() -> str:
    """ES: Genera CSS dedicado para la grilla KPI responsiva 2x3 (desktop)
    y 1x2 (mobile). Incluye estilos para sparklines, deltas, tooltips
    y badge de actualizacion.

    EN: Generate dedicated CSS for the responsive 2x3 (desktop)
    and 1x2 (mobile) KPI grid. Includes styles for sparklines, deltas,
    tooltips, and update badge.
    """
    return f"""
<style>
    /* ============================================================
       ES: Grilla KPI responsiva 2x3 / EN: Responsive 2x3 KPI grid
       ============================================================ */
    .kpi-grid {{
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 16px;
        margin: 16px 0 20px;
    }}
    @media (max-width: 992px) {{
        .kpi-grid {{ grid-template-columns: repeat(2, 1fr); }}
    }}
    @media (max-width: 576px) {{
        .kpi-grid {{ grid-template-columns: 1fr; }}
    }}

    /* ============================================================
       ES: Tarjeta KPI institucional grande / EN: Large institutional KPI card
       ============================================================ */
    .kpi-card-lg {{
        background: {BG_PANEL_SOFT};
        border-radius: {BORDER_RADIUS_LG};
        padding: 22px 24px 18px;
        border: 1px solid {BORDER_DEFAULT};
        box-shadow: {SHADOW_DEFAULT};
        transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.25s ease;
        position: relative;
        overflow: hidden;
        min-height: 178px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }}
    .kpi-card-lg:hover {{
        transform: translateY(-3px);
        box-shadow: 0 10px 36px rgba(0, 0, 0, 0.45);
        border-color: {ACCENT_BLUE_BORDER};
    }}

    /* ES: Indicador superior de color semantico / EN: Top semantic color indicator */
    .kpi-card-lg::before {{
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: var(--kpi-accent, {ACCENT_BLUE});
    }}

    /* ES: Encabezado de la tarjeta / EN: Card header */
    .kpi-card-lg .kpi-header {{
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 8px;
        margin-bottom: 4px;
    }}
    .kpi-card-lg .kpi-label {{
        font-size: 0.70rem;
        text-transform: uppercase;
        letter-spacing: 0.13em;
        color: {TEXT_MUTED};
        font-weight: 700;
        line-height: 1.3;
    }}
    .kpi-card-lg .kpi-label-en {{
        font-size: 0.62rem;
        color: {TEXT_MUTED};
        font-weight: 400;
        letter-spacing: 0.06em;
        text-transform: none;
        opacity: 0.7;
    }}

    /* ES: Icono de info con tooltip / EN: Info icon with tooltip */
    .kpi-info-icon {{
        position: relative;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 18px;
        height: 18px;
        border-radius: 50%;
        background: rgba(148, 163, 184, 0.12);
        color: {TEXT_MUTED};
        font-size: 0.62rem;
        font-weight: 700;
        cursor: help;
        flex-shrink: 0;
        margin-top: 1px;
    }}
    .kpi-info-icon .kpi-tooltip {{
        visibility: hidden;
        opacity: 0;
        position: absolute;
        top: 100%;
        right: -8px;
        margin-top: 8px;
        width: 280px;
        padding: 14px 16px;
        background: {BG_SECONDARY};
        border: 1px solid {ACCENT_BLUE_BORDER};
        border-radius: {BORDER_RADIUS};
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.5);
        font-size: 0.72rem;
        font-weight: 400;
        color: {TEXT_SECONDARY};
        line-height: 1.55;
        text-transform: none;
        letter-spacing: 0;
        z-index: 1000;
        transition: visibility 0.15s, opacity 0.15s ease;
        pointer-events: none;
    }}
    .kpi-info-icon:hover .kpi-tooltip {{
        visibility: visible;
        opacity: 1;
    }}
    .kpi-tooltip strong {{
        color: {TEXT_PRIMARY};
        display: block;
        margin-bottom: 4px;
        font-size: 0.74rem;
    }}
    .kpi-tooltip .tooltip-source {{
        display: block;
        margin-top: 8px;
        padding-top: 6px;
        border-top: 1px solid {BORDER_DEFAULT};
        font-size: 0.65rem;
        color: {TEXT_MUTED};
    }}
    .kpi-tooltip .tooltip-source code {{
        color: {ACCENT_BLUE};
        font-size: 0.64rem;
    }}

    /* ES: Valor principal grande / EN: Large main value */
    .kpi-card-lg .kpi-main-value {{
        font-size: 2.0rem;
        font-weight: 800;
        color: {TEXT_PRIMARY};
        line-height: 1.1;
        letter-spacing: -0.03em;
        margin: 2px 0;
    }}

    /* ES: Linea de delta / EN: Delta row */
    .kpi-delta-row {{
        display: flex;
        align-items: center;
        gap: 8px;
        margin: 4px 0 6px;
    }}
    .kpi-delta {{
        display: inline-flex;
        align-items: center;
        gap: 3px;
        padding: 2px 8px;
        border-radius: {BORDER_RADIUS_PILL};
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.01em;
    }}
    .kpi-delta--positive {{
        background: {GREEN_BG};
        color: {GREEN_INTEGRITY};
        border: 1px solid {GREEN_BORDER};
    }}
    .kpi-delta--negative {{
        background: {DANGER_RED_BG};
        color: {DANGER_RED};
        border: 1px solid {DANGER_RED_BORDER};
    }}
    .kpi-delta--neutral {{
        background: rgba(148, 163, 184, 0.10);
        color: {TEXT_SECONDARY};
        border: 1px solid {BORDER_DEFAULT};
    }}
    .kpi-delta--warning {{
        background: {ALERT_ORANGE_BG};
        color: {ALERT_ORANGE};
        border: 1px solid {ALERT_ORANGE_BORDER};
    }}
    .kpi-subtitle {{
        font-size: 0.74rem;
        color: {TEXT_SECONDARY};
        line-height: 1.4;
    }}

    /* ES: Contenedor de sparkline / EN: Sparkline container */
    .kpi-sparkline {{
        margin-top: 6px;
        height: 36px;
        overflow: hidden;
        border-radius: 6px;
    }}
    .kpi-sparkline img {{
        width: 100%;
        height: 36px;
        object-fit: cover;
        display: block;
    }}

    /* ============================================================
       ES: Badge de actualizacion CNE / EN: CNE update badge
       ============================================================ */
    .cne-update-badge {{
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 8px 18px;
        border-radius: {BORDER_RADIUS_PILL};
        font-size: 0.76rem;
        font-weight: 600;
        letter-spacing: 0.02em;
        margin-bottom: 12px;
        transition: background 0.3s ease;
    }}
    .cne-badge--fresh {{
        background: {GREEN_BG};
        color: {GREEN_INTEGRITY};
        border: 1px solid {GREEN_BORDER};
    }}
    .cne-badge--stale {{
        background: {ALERT_ORANGE_BG};
        color: {ALERT_ORANGE};
        border: 1px solid {ALERT_ORANGE_BORDER};
    }}
    .cne-badge--critical {{
        background: {DANGER_RED_BG};
        color: {DANGER_RED};
        border: 1px solid {DANGER_RED_BORDER};
    }}
    .cne-badge-dot {{
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: currentColor;
        animation: cne-pulse 2s ease-in-out infinite;
    }}
    @keyframes cne-pulse {{
        0%, 100% {{ opacity: 1; }}
        50% {{ opacity: 0.4; }}
    }}
</style>
"""


# =========================================================================
# ES: Generador de sparklines con Altair
# EN: Altair sparkline generator
# =========================================================================
def _render_sparkline_base64(
    data: list[float | int],
    color: str = ACCENT_BLUE,
    width: int = 220,
    height: int = 36,
) -> str:
    """ES: Renderiza un sparkline Altair como imagen PNG codificada en base64.
    Recibe una lista de valores numericos y devuelve un string base64
    listo para incrustar en un tag <img>.

    EN: Render an Altair sparkline as a base64-encoded PNG image.
    Receives a list of numeric values and returns a base64 string
    ready to embed in an <img> tag.

    Args:
        data: ES: Lista de valores numericos (ej. ultimas 12 horas)
              EN: List of numeric values (e.g. last 12 hours)
        color: ES: Color hexadecimal de la linea
               EN: Hex color of the line
        width: ES: Ancho del grafico en pixeles
               EN: Chart width in pixels
        height: ES: Alto del grafico en pixeles
                EN: Chart height in pixels

    Returns:
        ES: String base64 de la imagen PNG (vacio si falla)
        EN: Base64 string of the PNG image (empty if fails)
    """
    if not data or len(data) < 2:
        return ""

    try:
        df = pd.DataFrame({
            "idx": list(range(len(data))),
            "val": [float(v) for v in data],
        })

        # ES: Crear grafico sparkline minimalista / EN: Create minimal sparkline chart
        line = (
            alt.Chart(df)
            .mark_area(
                line={"color": color, "strokeWidth": 2},
                color=alt.Gradient(
                    gradient="linear",
                    stops=[
                        alt.GradientStop(color=color, offset=0),
                        alt.GradientStop(color="transparent", offset=1),
                    ],
                    x1=0, x2=0, y1=0, y2=1,
                ),
                interpolate="monotone",
                opacity=0.3,
            )
            .encode(
                x=alt.X("idx:Q", axis=None, scale=alt.Scale(nice=False)),
                y=alt.Y("val:Q", axis=None, scale=alt.Scale(zero=False)),
            )
            .properties(
                width=width,
                height=height,
                padding={"top": 2, "bottom": 2, "left": 0, "right": 0},
            )
            .configure_view(strokeWidth=0)
        )

        # ES: Renderizar a PNG en buffer / EN: Render to PNG in buffer
        buf = io.BytesIO()
        line.save(buf, format="png", scale_factor=2)
        buf.seek(0)
        return base64.b64encode(buf.read()).decode("utf-8")

    except Exception:  # noqa: BLE001 — ES: Sparkline es decorativo / EN: Sparkline is decorative
        return ""


def _compute_delta_display(
    current: float | int,
    previous: float | int | None,
) -> tuple[str, str, str]:
    """ES: Calcula el delta porcentual, la flecha y la clase CSS semantica.

    EN: Compute percentage delta, arrow, and semantic CSS class.

    Args:
        current: ES: Valor actual / EN: Current value
        previous: ES: Valor anterior (None si no hay) / EN: Previous value (None if unavailable)

    Returns:
        ES: Tupla (texto_delta, clase_css, flecha)
        EN: Tuple (delta_text, css_class, arrow)
    """
    if previous is None or previous == 0:
        return ("\u2014", "kpi-delta--neutral", "")

    try:
        current_f = float(current)
        previous_f = float(previous)
    except (TypeError, ValueError):
        return ("\u2014", "kpi-delta--neutral", "")

    diff = current_f - previous_f
    pct = (diff / abs(previous_f)) * 100.0

    if abs(pct) < 0.01:
        return ("0.0%", "kpi-delta--neutral", "\u2194")

    if pct > 0:
        arrow = "\u2191"
        cls = "kpi-delta--positive"
    else:
        arrow = "\u2193"
        cls = "kpi-delta--negative"

    return (f"{pct:+.1f}%", cls, arrow)


# =========================================================================
# ES: Funcion principal reutilizable para crear tarjetas KPI
# EN: Main reusable function for creating KPI cards
# =========================================================================
def create_kpi_card(
    title_es: str,
    title_en: str,
    value: str | int | float,
    delta: float | int | None = None,
    delta_previous: float | int | None = None,
    spark_data: list[float | int] | None = None,
    tooltip_text: str = "",
    tooltip_source: str = "",
    accent_color: str = ACCENT_BLUE,
    value_suffix: str = "",
    delta_override: str | None = None,
    delta_class_override: str | None = None,
) -> str:
    """ES: Crea una tarjeta KPI institucional completa para el dashboard.
    Conforme a estandares de informes de observacion electoral de la OEA,
    UE Election Observation Missions y el Carter Center.

    Cada tarjeta incluye:
      - Titulo bilingue (ES/EN) con etiqueta superior
      - Valor principal en tipografia de impacto (2rem, weight 800)
      - Delta porcentual con flecha y color semantico automatico
      - Subtitulo explicativo
      - Tooltip con definicion estadistica y fuente exacta del JSON CNE
      - Sparkline Altair de las ultimas 12 horas

    EN: Create a complete institutional KPI card for the dashboard.
    Compliant with OEA, EU Election Observation Missions, and Carter
    Center electoral observation report standards.

    Each card includes:
      - Bilingual title (ES/EN) with top label
      - Main value in impact typography (2rem, weight 800)
      - Percentage delta with automatic semantic color and arrow
      - Explanatory subtitle
      - Tooltip with statistical definition and exact CNE JSON source
      - Altair sparkline of the last 12 hours

    Args:
        title_es: ES: Titulo en espanol / EN: Title in Spanish
        title_en: ES: Titulo en ingles / EN: Title in English
        value: ES: Valor principal a mostrar / EN: Main value to display
        delta: ES: Valor numerico actual para calcular delta
               EN: Current numeric value for delta calculation
        delta_previous: ES: Valor numerico anterior para calcular delta
                        EN: Previous numeric value for delta calculation
        spark_data: ES: Lista de valores para el sparkline (ultimas 12h)
                    EN: List of values for the sparkline (last 12h)
        tooltip_text: ES: Texto de la definicion estadistica
                      EN: Statistical definition text
        tooltip_source: ES: Fuente del dato (campo JSON y timestamp)
                        EN: Data source (JSON field and timestamp)
        accent_color: ES: Color de acento para barra superior y sparkline
                      EN: Accent color for top bar and sparkline
        value_suffix: ES: Sufijo del valor (ej. '%', 'min')
                      EN: Value suffix (e.g. '%', 'min')
        delta_override: ES: Texto de delta personalizado (omitir calculo)
                        EN: Custom delta text (skip calculation)
        delta_class_override: ES: Clase CSS de delta personalizada
                              EN: Custom delta CSS class

    Returns:
        ES: HTML completo de la tarjeta KPI listo para st.markdown()
        EN: Complete KPI card HTML ready for st.markdown()
    """
    # ES: Formatear valor principal / EN: Format main value
    display_value = str(value)
    if value_suffix:
        display_value = f"{display_value}{value_suffix}"

    # ES: Calcular delta o usar override / EN: Compute delta or use override
    if delta_override is not None:
        delta_text = delta_override
        delta_cls = delta_class_override or "kpi-delta--neutral"
        delta_arrow = ""
    elif delta is not None:
        delta_text, delta_cls, delta_arrow = _compute_delta_display(delta, delta_previous)
    else:
        delta_text = ""
        delta_cls = ""
        delta_arrow = ""

    # ES: Construir tooltip HTML / EN: Build tooltip HTML
    tooltip_html = ""
    if tooltip_text:
        source_html = ""
        if tooltip_source:
            source_html = (
                f'<span class="tooltip-source">'
                f"\U0001f4cb Fuente / Source:<br/><code>{tooltip_source}</code>"
                f"</span>"
            )
        tooltip_html = (
            f'<div class="kpi-info-icon">i'
            f'<div class="kpi-tooltip">'
            f"<strong>{title_es} / {title_en}</strong>"
            f"{tooltip_text}"
            f"{source_html}"
            f"</div></div>"
        )

    # ES: Construir delta HTML / EN: Build delta HTML
    delta_html = ""
    if delta_text:
        delta_html = (
            f'<div class="kpi-delta-row">'
            f'<span class="kpi-delta {delta_cls}">{delta_arrow} {delta_text}</span>'
            f"</div>"
        )

    # ES: Construir sparkline HTML / EN: Build sparkline HTML
    sparkline_html = ""
    if spark_data and len(spark_data) >= 2:
        b64 = _render_sparkline_base64(spark_data, color=accent_color)
        if b64:
            sparkline_html = (
                f'<div class="kpi-sparkline">'
                f'<img src="data:image/png;base64,{b64}" alt="sparkline" />'
                f"</div>"
            )

    return f"""
<div class="kpi-card-lg" style="--kpi-accent: {accent_color};">
  <div>
    <div class="kpi-header">
      <div>
        <div class="kpi-label">{title_es}</div>
        <div class="kpi-label-en">{title_en}</div>
      </div>
      {tooltip_html}
    </div>
    <div class="kpi-main-value">{display_value}</div>
    {delta_html}
  </div>
  {sparkline_html}
</div>
"""


# =========================================================================
# ES: Badge de actualizacion CNE con color dinamico
# EN: CNE update badge with dynamic color
# =========================================================================
def create_cne_update_badge(minutes_ago: float | int | None) -> str:
    """ES: Genera un badge que indica la frescura de los datos del CNE.
    El color cambia dinamicamente segun la antiguedad:
      - Verde: < 15 minutos (datos frescos)
      - Naranja: 15-45 minutos (datos algo antiguos)
      - Rojo: > 45 minutos (datos criticos)

    EN: Generate a badge indicating the freshness of CNE data.
    Color changes dynamically based on age:
      - Green: < 15 minutes (fresh data)
      - Orange: 15-45 minutes (somewhat stale data)
      - Red: > 45 minutes (critical staleness)

    Args:
        minutes_ago: ES: Minutos desde la ultima actualizacion (None si no hay datos)
                     EN: Minutes since last update (None if no data)

    Returns:
        ES: HTML del badge con color dinamico
        EN: Badge HTML with dynamic color
    """
    if minutes_ago is None:
        badge_cls = "cne-badge--critical"
        label_es = "Sin datos del CNE"
        label_en = "No CNE data"
    elif minutes_ago < 15:
        badge_cls = "cne-badge--fresh"
        label_es = f"Datos del CNE \u2013 Actualizado hace {int(minutes_ago)} min"
        label_en = f"CNE Data \u2013 Updated {int(minutes_ago)} min ago"
    elif minutes_ago < 45:
        badge_cls = "cne-badge--stale"
        label_es = f"Datos del CNE \u2013 Actualizado hace {int(minutes_ago)} min"
        label_en = f"CNE Data \u2013 Updated {int(minutes_ago)} min ago"
    else:
        badge_cls = "cne-badge--critical"
        hours = minutes_ago / 60.0
        if hours >= 1:
            label_es = f"Datos del CNE \u2013 Actualizado hace {hours:.1f}h"
            label_en = f"CNE Data \u2013 Updated {hours:.1f}h ago"
        else:
            label_es = f"Datos del CNE \u2013 Actualizado hace {int(minutes_ago)} min"
            label_en = f"CNE Data \u2013 Updated {int(minutes_ago)} min ago"

    return (
        f'<div class="cne-update-badge {badge_cls}">'
        f'<span class="cne-badge-dot"></span>'
        f"{label_es} / {label_en}"
        f"</div>"
    )


# =========================================================================
# ES: Seccion completa de Resumen Ejecutivo
# EN: Complete Executive Summary section
# =========================================================================
def render_executive_summary(
    snapshot_count: int,
    integrity_pct: float,
    critical_count: int,
    actas_inconsistent: int,
    actas_total_checked: int,
    rules_count: int,
    minutes_since_update: float | None,
    anchor_root_hash: str,
    spark_snapshots: list[float | int] | None = None,
    spark_integrity: list[float | int] | None = None,
    spark_deltas: list[float | int] | None = None,
    spark_actas: list[float | int] | None = None,
    spark_latency: list[float | int] | None = None,
    spark_rules: list[float | int] | None = None,
    prev_snapshot_count: int | None = None,
    prev_integrity_pct: float | None = None,
    prev_critical_count: int | None = None,
    prev_actas_inconsistent: int | None = None,
    prev_latency_min: float | None = None,
    prev_rules_count: int | None = None,
    latency_avg_min: float = 4.2,
) -> None:
    """ES: Renderiza la seccion completa de Resumen Ejecutivo con las 6 tarjetas
    KPI obligatorias, badge de actualizacion CNE, y sparklines.

    Metricas obligatorias (conforme estandares de observacion electoral):
      1. Snapshots procesados
      2. Integridad Global (%)
      3. Deltas Negativos
      4. Actas Inconsistentes
      5. Latencia Promedio
      6. Reglas Activas

    EN: Render the complete Executive Summary section with the 6 mandatory
    KPI cards, CNE update badge, and sparklines.

    Mandatory metrics (per electoral observation standards):
      1. Processed snapshots
      2. Global Integrity (%)
      3. Negative Deltas
      4. Inconsistent Actas
      5. Average Latency
      6. Active Rules

    Args:
        snapshot_count: ES: Numero de snapshots procesados / EN: Number of processed snapshots
        integrity_pct: ES: Porcentaje de integridad global / EN: Global integrity percentage
        critical_count: ES: Numero de deltas negativos / EN: Number of negative deltas
        actas_inconsistent: ES: Actas inconsistentes / EN: Inconsistent actas
        actas_total_checked: ES: Total de actas verificadas / EN: Total actas checked
        rules_count: ES: Reglas activas / EN: Active rules
        minutes_since_update: ES: Minutos desde ultima actualizacion / EN: Minutes since last update
        anchor_root_hash: ES: Hash raiz del anclaje blockchain / EN: Blockchain anchor root hash
        spark_*: ES: Datos para sparklines / EN: Sparkline data
        prev_*: ES: Valores anteriores para calculo de delta / EN: Previous values for delta calculation
        latency_avg_min: ES: Latencia promedio en minutos / EN: Average latency in minutes
    """
    # ES: Inyectar CSS de la grilla KPI / EN: Inject KPI grid CSS
    st.markdown(get_kpi_grid_css(), unsafe_allow_html=True)

    # ES: Titulo de seccion bilingue / EN: Bilingual section title
    st.markdown(
        '<div class="section-title">Resumen Ejecutivo / Executive Summary</div>'
        '<div class="section-subtitle">'
        "Indicadores clave de integridad, velocidad y cobertura operacional "
        "\u2014 conforme est\u00e1ndares OEA/UE/Carter Center.<br/>"
        "<em>Key integrity, speed, and operational coverage indicators "
        "\u2014 per OEA/EU/Carter Center standards.</em>"
        "</div>",
        unsafe_allow_html=True,
    )

    # ES: Badge de actualizacion CNE / EN: CNE update badge
    st.markdown(
        create_cne_update_badge(minutes_since_update),
        unsafe_allow_html=True,
    )

    # ES: Construir las 6 tarjetas KPI / EN: Build the 6 KPI cards
    # -- 1) Snapshots procesados --
    card_snapshots = create_kpi_card(
        title_es="Snapshots procesados",
        title_en="Processed Snapshots",
        value=f"{snapshot_count:,}",
        delta=snapshot_count,
        delta_previous=prev_snapshot_count,
        spark_data=spark_snapshots,
        tooltip_text=(
            "N\u00famero total de capturas JSON del endpoint p\u00fablico del CNE "
            "procesadas y verificadas por hash SHA-256. Cada snapshot contiene "
            "el estado completo de votos nacionales y por departamento."
        ),
        tooltip_source="snapshot_*.json \u2192 campo 'timestamp' + hash SHA-256",
        accent_color=ACCENT_BLUE,
    )

    # -- 2) Integridad Global (%) --
    integrity_color = GREEN_INTEGRITY if integrity_pct >= 99.0 else (
        ALERT_ORANGE if integrity_pct >= 95.0 else DANGER_RED
    )
    card_integrity = create_kpi_card(
        title_es="Integridad global",
        title_en="Global Integrity",
        value=f"{integrity_pct:.1f}",
        value_suffix="%",
        delta=integrity_pct,
        delta_previous=prev_integrity_pct,
        spark_data=spark_integrity,
        tooltip_text=(
            "Porcentaje de consistencia entre la suma de votos por departamento "
            "y el total nacional reportado por el CNE. Una discrepancia indica "
            "votos sin origen geogr\u00e1fico trazable."
        ),
        tooltip_source="JSON CNE \u2192 'departamentos[].total' vs 'nacional.total'",
        accent_color=integrity_color,
    )

    # -- 3) Deltas Negativos --
    delta_color = GREEN_INTEGRITY if critical_count == 0 else (
        ALERT_ORANGE if critical_count <= 2 else DANGER_RED
    )
    delta_cls = "kpi-delta--positive" if critical_count == 0 else (
        "kpi-delta--warning" if critical_count <= 2 else "kpi-delta--negative"
    )
    card_deltas = create_kpi_card(
        title_es="Deltas negativos",
        title_en="Negative Deltas",
        value=str(critical_count),
        delta=critical_count,
        delta_previous=prev_critical_count,
        spark_data=spark_deltas,
        tooltip_text=(
            "Conteo de snapshots donde el total de votos de un departamento "
            "disminuy\u00f3 respecto al snapshot anterior (delta < -200). "
            "Cada delta negativo es una alerta de posible eliminaci\u00f3n de datos."
        ),
        tooltip_source="snapshot_N.json \u2192 delta = votos[t] - votos[t-1]",
        accent_color=delta_color,
        delta_class_override=delta_cls,
    )

    # -- 4) Actas Inconsistentes --
    actas_color = GREEN_INTEGRITY if actas_inconsistent == 0 else (
        ALERT_ORANGE if actas_inconsistent <= 3 else DANGER_RED
    )
    actas_integrity_label = f"{(100.0 * (1 - actas_inconsistent / max(1, actas_total_checked))):.0f}%"
    card_actas = create_kpi_card(
        title_es="Actas inconsistentes",
        title_en="Inconsistent Actas",
        value=str(actas_inconsistent),
        delta=actas_inconsistent,
        delta_previous=prev_actas_inconsistent,
        spark_data=spark_actas,
        tooltip_text=(
            f"Mesas electorales cuya suma aritm\u00e9tica (v\u00e1lidos + nulos + blancos) "
            f"no coincide con el total declarado, o donde la suma de candidatos "
            f"no iguala los votos v\u00e1lidos. Integridad actas: {actas_integrity_label}."
        ),
        tooltip_source=(
            "snapshot_*.json \u2192 'mesas[].totals' vs "
            "'mesas[].candidatos' (\u00b1tolerancia 1)"
        ),
        accent_color=actas_color,
    )

    # -- 5) Latencia Promedio --
    latency_display = f"{latency_avg_min:.1f}"
    latency_color = GREEN_INTEGRITY if latency_avg_min < 5.0 else (
        ALERT_ORANGE if latency_avg_min < 15.0 else DANGER_RED
    )
    card_latency = create_kpi_card(
        title_es="Latencia promedio",
        title_en="Average Latency",
        value=latency_display,
        value_suffix=" min",
        delta=latency_avg_min,
        delta_previous=prev_latency_min,
        spark_data=spark_latency,
        tooltip_text=(
            "Tiempo promedio entre la publicaci\u00f3n de datos en el endpoint "
            "del CNE y su captura por el motor de ingesta CENTINEL. "
            "Menor latencia indica mayor vigilancia en tiempo real."
        ),
        tooltip_source="log \u2192 timestamp_captura - timestamp_publicacion (UTC)",
        accent_color=latency_color,
    )

    # -- 6) Reglas Activas --
    card_rules = create_kpi_card(
        title_es="Reglas activas",
        title_en="Active Rules",
        value=str(rules_count),
        delta=rules_count,
        delta_previous=prev_rules_count,
        spark_data=spark_rules,
        tooltip_text=(
            "N\u00famero de reglas de auditor\u00eda activadas en el motor de reglas "
            "CENTINEL. Incluye: delta negativo, Benford 1er d\u00edgito, "
            "outlier z-score, consistencia topol\u00f3gica y verificaci\u00f3n de actas."
        ),
        tooltip_source="command_center/config.yaml \u2192 'rules.*'",
        accent_color=ACCENT_BLUE,
    )

    # ES: Renderizar grilla 2x3 con HTML / EN: Render 2x3 grid with HTML
    grid_html = (
        '<div class="kpi-grid fade-in">'
        f"{card_snapshots}"
        f"{card_integrity}"
        f"{card_deltas}"
        f"{card_actas}"
        f"{card_latency}"
        f"{card_rules}"
        "</div>"
    )
    st.markdown(grid_html, unsafe_allow_html=True)
