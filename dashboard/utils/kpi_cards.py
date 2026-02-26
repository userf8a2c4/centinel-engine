"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Utilidades de sparkline SVG / SVG sparkline utilities
3. Renderizado de delta semántico / Semantic delta rendering
4. Función principal create_kpi_card / Main create_kpi_card function
5. CSS de tarjetas KPI v2 / KPI v2 card CSS
6. Badge dinámico CNE / Dynamic CNE badge

======================== ESPAÑOL ========================
Archivo: `dashboard/utils/kpi_cards.py`.

Módulo de tarjetas KPI para el dashboard C.E.N.T.I.N.E.L.
Proporciona tarjetas KPI grandes con sparklines SVG inline,
deltas semánticos con flecha y color, tooltips estadísticos,
badges de fuente CNE y un grid responsivo 2×3 (desktop) / 1×2 (mobile).

Diseñado para cumplir estándares de informes de observación electoral
internacional (OEA, UE Election Observation Missions, Carter Center).

Cada tarjeta muestra:
  - Valor principal en tipografía grande (≥ 2.4rem)
  - Delta porcentual con flecha ▲/▼ y color semántico verde/rojo
  - Subtítulo explicativo bilingüe
  - Tooltip con definición estadística y fuente exacta del JSON del CNE
  - Micro-gráfico sparkline SVG de las últimas 12 horas

======================== ENGLISH ========================
File: `dashboard/utils/kpi_cards.py`.

KPI card module for the C.E.N.T.I.N.E.L. dashboard.
Provides large KPI cards with inline SVG sparklines, semantic deltas
with arrow and color, statistical tooltips, CNE source badges, and
a responsive 2×3 grid (desktop) / 1×2 (mobile).

Designed to meet international electoral observation report standards
(OAS, EU Election Observation Missions, Carter Center).

Each card shows:
  - Main value in large typography (≥ 2.4rem)
  - Percentage delta with ▲/▼ arrow and semantic green/red color
  - Bilingual explanatory subtitle
  - Tooltip with statistical definition and exact CNE JSON field/timestamp
  - SVG sparkline micro-chart for the last 12 hours
"""

from __future__ import annotations

import math
from typing import Optional


# =========================================================================
# ES: Colores semánticos para deltas / EN: Semantic delta colors
# =========================================================================
_COLOR_POSITIVE = "#00C853"   # ES: Verde positivo / EN: Positive green
_COLOR_DANGER   = "#EF4444"   # ES: Rojo peligro   / EN: Danger red
_COLOR_NEUTRAL  = "#94A3B8"   # ES: Gris neutro    / EN: Neutral gray
_COLOR_WARNING  = "#FF9800"   # ES: Naranja aviso  / EN: Warning orange


# =========================================================================
# ES: Utilidades de sparkline SVG puro / EN: Pure SVG sparkline utilities
# =========================================================================

def _clean_series(data: list) -> list[float]:
    """ES: Filtra valores None, NaN e infinitos de una serie numérica.

    EN: Filter None, NaN, and infinite values from a numeric series.

    Args:
        data: ES: Lista de valores raw. / EN: Raw value list.

    Returns:
        list[float]: ES: Serie limpia de floats. / EN: Clean float series.
    """
    result = []
    for v in data:
        try:
            f = float(v)
            if math.isfinite(f):
                result.append(f)
        except (TypeError, ValueError):
            pass  # ES: Ignorar no numéricos / EN: Skip non-numerics
    return result


def _generate_sparkline_svg(
    data: list,
    color: str = "#00A3E0",
    width: int = 220,
    height: int = 44,
    stroke_width: float = 2.0,
    fill_opacity: float = 0.14,
) -> str:
    """ES: Genera un micro-gráfico sparkline SVG puro a partir de una lista de valores.

    No requiere dependencias externas (matplotlib, plotly, altair).
    Produce un SVG inline embebible en HTML con:
      - Área de relleno translúcida bajo la curva
      - Línea de tendencia suavizada (polyline)
      - Punto de resalte en el último valor

    EN: Generate a pure SVG sparkline micro-chart from a list of values.

    Requires no external dependencies (matplotlib, plotly, altair).
    Produces an inline SVG embeddable in HTML with:
      - Translucent fill area under the curve
      - Smoothed trend line (polyline)
      - Highlight dot at the last value

    Args:
        data: ES: Lista de valores numéricos (hasta 12 puntos). / EN: List of numeric values (up to 12 points).
        color: ES: Color de línea en formato hex. / EN: Line color in hex format.
        width: ES: Ancho del SVG en píxeles lógicos. / EN: SVG width in logical pixels.
        height: ES: Alto del SVG en píxeles lógicos. / EN: SVG height in logical pixels.
        stroke_width: ES: Grosor del trazo. / EN: Stroke width.
        fill_opacity: ES: Opacidad del relleno bajo la línea. / EN: Fill opacity under line.

    Returns:
        str: ES: Cadena SVG completa lista para embeber. / EN: Complete SVG string ready to embed.
    """
    # ES: Limpiar y validar datos / EN: Clean and validate data
    clean = _clean_series(data)
    if len(clean) < 2:
        # ES: Sin suficientes datos → SVG vacío / EN: Insufficient data → empty SVG
        return (
            f'<svg viewBox="0 0 {width} {height}" width="100%" height="{height}" '
            f'xmlns="http://www.w3.org/2000/svg">'
            f'<line x1="{4}" y1="{height/2:.1f}" x2="{width-4}" y2="{height/2:.1f}" '
            f'stroke="{color}" stroke-width="1" stroke-dasharray="4 4" opacity="0.3"/>'
            f'</svg>'
        )

    # ES: Calcular rango con padding interior / EN: Calculate range with inner padding
    min_val = min(clean)
    max_val = max(clean)
    range_val = max_val - min_val or 1.0

    # ES: Márgenes internos / EN: Inner margins
    pad_x, pad_y = 4, 5
    usable_w = width - 2 * pad_x
    usable_h = height - 2 * pad_y

    # ES: Mapear valores a coordenadas SVG (y=0 en arriba → invertir)
    # EN: Map values to SVG coordinates (y=0 at top → invert)
    n = len(clean)
    step = usable_w / max(n - 1, 1)
    pts: list[tuple[float, float]] = []
    for i, v in enumerate(clean):
        x = pad_x + i * step
        y = pad_y + usable_h * (1.0 - (v - min_val) / range_val)
        pts.append((x, y))

    # ES: Construir polyline de puntos / EN: Build points polyline
    pts_str = " ".join(f"{x:.2f},{y:.2f}" for x, y in pts)

    # ES: Área de relleno (polygon cerrado al fondo) / EN: Fill area (polygon closed at bottom)
    base_y = pad_y + usable_h
    fill_pts = (
        f"{pts[0][0]:.2f},{base_y:.2f} "
        + pts_str
        + f" {pts[-1][0]:.2f},{base_y:.2f}"
    )

    # ES: Punto resaltado en el último valor / EN: Highlight dot at last value
    lx, ly = pts[-1]
    highlight_dot = (
        f'<circle cx="{lx:.2f}" cy="{ly:.2f}" r="3.2" fill="{color}" opacity="0.95"/>'
        f'<circle cx="{lx:.2f}" cy="{ly:.2f}" r="6" fill="{color}" opacity="0.15"/>'
    )

    return (
        f'<svg viewBox="0 0 {width} {height}" width="100%" height="{height}" '
        f'xmlns="http://www.w3.org/2000/svg" style="display:block;overflow:visible;">'
        f'<polygon points="{fill_pts}" fill="{color}" opacity="{fill_opacity}"/>'
        f'<polyline points="{pts_str}" fill="none" stroke="{color}" '
        f'stroke-width="{stroke_width}" stroke-linecap="round" stroke-linejoin="round"/>'
        f'{highlight_dot}'
        f'</svg>'
    )


# =========================================================================
# ES: Renderizado de delta semántico / EN: Semantic delta rendering
# =========================================================================

def _delta_badge_html(
    delta: Optional[float],
    invert_semantics: bool = False,
) -> str:
    """ES: Genera el HTML del badge delta con flecha ▲/▼ y color semántico.

    La semántica normal es:
      - Delta positivo → verde (bueno): ej. más snapshots procesados.
      - Delta negativo → rojo (malo): ej. caída de integridad.
    Con invert_semantics=True la lógica se invierte, útil para métricas
    de error donde crecer es negativo (ej. deltas negativos, inconsistencias).

    EN: Generate delta badge HTML with ▲/▼ arrow and semantic color.

    Normal semantics:
      - Positive delta → green (good): e.g. more snapshots processed.
      - Negative delta → red (bad): e.g. integrity drop.
    With invert_semantics=True the logic is reversed, useful for error
    metrics where growth is bad (e.g. negative deltas, inconsistencies).

    Args:
        delta: ES: Cambio porcentual vs período anterior (None si no aplica).
               EN: Percentage change vs. prior period (None if not applicable).
        invert_semantics: ES: Invertir semántica de color.
                          EN: Invert color semantics.

    Returns:
        str: ES: Fragmento HTML del badge delta. / EN: Delta badge HTML fragment.
    """
    if delta is None:
        # ES: Sin datos comparativos / EN: No comparison data available
        return '<span class="kpi-v2-delta kpi-delta-neutral">&#8212; Sin datos previos / No prior data</span>'

    is_zero = abs(delta) < 0.05  # ES: Umbral de cero / EN: Zero threshold

    if is_zero:
        arrow, sign, css_cls = "&#8594;", "", "kpi-delta-neutral"  # →
    elif delta > 0:
        arrow, sign = "&#9650;", "+"  # ▲
        # ES: Positivo es bueno (verde) salvo inversión / EN: Positive is good (green) unless inverted
        css_cls = "kpi-delta-danger" if invert_semantics else "kpi-delta-positive"
    else:
        arrow, sign = "&#9660;", ""  # ▼
        # ES: Negativo es malo (rojo) salvo inversión / EN: Negative is bad (red) unless inverted
        css_cls = "kpi-delta-positive" if invert_semantics else "kpi-delta-danger"

    # ES: Formatear el valor del delta / EN: Format delta value
    formatted = f"{sign}{delta:+.1f}%"

    return f'<span class="kpi-v2-delta {css_cls}">{arrow}&nbsp;{formatted}</span>'


# =========================================================================
# ES: Función principal create_kpi_card / EN: Main create_kpi_card function
# =========================================================================

def create_kpi_card(
    title_es: str,
    title_en: str,
    value: str,
    delta: Optional[float],
    spark_data: list,
    tooltip_text: str,
    subtitle: str = "",
    source_field: str = "",
    source_ts: str = "",
    invert_delta_semantics: bool = False,
    accent_color: str = "#00A3E0",
) -> str:
    """ES: Crea una tarjeta KPI grande conforme a estándares de observación electoral internacional.

    Cada tarjeta incluye:
      - Título bilingüe (ES/EN) en cabecera
      - Ícono de información con tooltip estadístico (definición + fuente CNE)
      - Valor principal en tipografía grande (≥ 2.4rem)
      - Badge de delta porcentual con flecha ▲/▼ y color semántico verde/rojo
      - Subtítulo explicativo opcional
      - Micro-gráfico sparkline SVG de las últimas 12 horas
      - Línea de fuente exacta del JSON del CNE (campo + timestamp)

    EN: Create a large KPI card meeting international electoral observation standards.

    Each card includes:
      - Bilingual title (ES/EN) in header
      - Information icon with statistical tooltip (definition + CNE source)
      - Main value in large typography (≥ 2.4rem)
      - Percentage delta badge with ▲/▼ arrow and semantic green/red color
      - Optional explanatory subtitle
      - SVG sparkline micro-chart for the last 12 hours
      - Exact CNE JSON source line (field + timestamp)

    Args:
        title_es:
            ES: Título de la métrica en español.
            EN: Metric title in Spanish.
        title_en:
            ES: Título de la métrica en inglés.
            EN: Metric title in English.
        value:
            ES: Valor principal formateado como string (ej. "1,234" o "98.7%").
            EN: Main value formatted as string (e.g. "1,234" or "98.7%").
        delta:
            ES: Cambio porcentual vs período anterior. None si no hay datos comparativos.
            EN: Percentage change vs. prior period. None if no comparison data.
        spark_data:
            ES: Lista de hasta 12 puntos numéricos para el sparkline.
                Representa la evolución de la métrica en las últimas 12 horas.
            EN: List of up to 12 numeric points for the sparkline.
                Represents metric evolution over the last 12 hours.
        tooltip_text:
            ES: Texto completo para el tooltip: definición estadística + fuente CNE.
            EN: Full tooltip text: statistical definition + CNE source.
        subtitle:
            ES: Subtítulo explicativo opcional (ej. "Integridad verificada").
            EN: Optional explanatory subtitle (e.g. "Verified integrity").
        source_field:
            ES: Campo exacto del JSON del CNE (ej. "meta.timestamp_utc").
            EN: Exact CNE JSON field (e.g. "meta.timestamp_utc").
        source_ts:
            ES: Timestamp de la fuente CNE en formato ISO o legible.
            EN: CNE source timestamp in ISO or human-readable format.
        invert_delta_semantics:
            ES: Invertir semántica de color del delta. Usar True para métricas
                de error donde incremento es negativo (deltas negativos, inconsistencias).
            EN: Invert delta color semantics. Use True for error metrics where
                growth is negative (negative deltas, inconsistencies).
        accent_color:
            ES: Color de acento en hex para borde superior y sparkline.
            EN: Hex accent color for top border and sparkline.

    Returns:
        str: ES: HTML completo de la tarjeta KPI, listo para st.markdown(unsafe_allow_html=True).
             EN: Complete KPI card HTML, ready for st.markdown(unsafe_allow_html=True).
    """
    # ES: Escapar strings para atributos HTML seguros / EN: Escape strings for safe HTML attributes
    def _esc(s: str) -> str:
        return s.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")

    # ES: Generar sparkline SVG inline / EN: Generate inline SVG sparkline
    spark_svg = _generate_sparkline_svg(spark_data, color=accent_color) if spark_data else ""

    # ES: Badge de delta semántico / EN: Semantic delta badge
    delta_html = _delta_badge_html(delta, invert_semantics=invert_delta_semantics)

    # ES: Bloque de subtítulo / EN: Subtitle block
    subtitle_html = (
        f'<div class="kpi-v2-subtitle">{subtitle}</div>'
        if subtitle else ""
    )

    # ES: Bloque de sparkline / EN: Sparkline block
    spark_html = (
        f'<div class="kpi-v2-sparkline" aria-hidden="true">{spark_svg}</div>'
        if spark_svg else ""
    )

    # ES: Línea de fuente CNE / EN: CNE source line
    source_parts = []
    if source_field:
        # ES: Campo del JSON del CNE / EN: CNE JSON field
        source_parts.append(f"Campo&nbsp;<code>{_esc(source_field)}</code>")
    if source_ts:
        # ES: Timestamp del snapshot / EN: Snapshot timestamp
        source_parts.append(f"TS&nbsp;{_esc(source_ts)}")
    source_html = (
        f'<div class="kpi-v2-source">CNE &middot; {" &middot; ".join(source_parts)}</div>'
        if source_parts else ""
    )

    # ES: Tooltip escapado para atributo title / EN: Tooltip escaped for title attribute
    tooltip_attr = _esc(tooltip_text)

    return f"""<div class="kpi-card-v2 fade-in" style="--kpi-accent:{accent_color};" title="{tooltip_attr}">
  <div class="kpi-v2-header">
    <div>
      <div class="kpi-v2-label-es">{title_es}</div>
      <div class="kpi-v2-label-en">{title_en}</div>
    </div>
    <div class="kpi-v2-info-icon" title="{tooltip_attr}" aria-label="Información estadística / Statistical info">&#x24D8;</div>
  </div>
  <div class="kpi-v2-value">{value}</div>
  {delta_html}
  {subtitle_html}
  {spark_html}
  {source_html}
</div>"""


# =========================================================================
# ES: CSS de tarjetas KPI v2 / EN: KPI v2 card CSS
# =========================================================================

def get_kpi_v2_css() -> str:
    """ES: Retorna el bloque <style> CSS completo para tarjetas KPI v2.

    Incluye:
      - Grid responsivo 2×3 (desktop), 2×2 (tablet), 1×N (mobile)
      - Tarjeta con borde superior de acento, glassmorphism y sombra institucional
      - Estilos de valor principal grande (≥ 2.4rem)
      - Badges de delta con colores semánticos (verde/rojo/gris)
      - Subtítulo, sparkline y línea de fuente CNE
      - Badge "Datos del CNE" con variantes fresh/recent/stale
      - Animación de entrada fadeIn
      - Compatibilidad con modo oscuro del tema institucional

    EN: Return the complete CSS <style> block for KPI v2 cards.

    Includes:
      - Responsive grid 2×3 (desktop), 2×2 (tablet), 1×N (mobile)
      - Card with accent top border, glassmorphism, and institutional shadow
      - Large main value styles (≥ 2.4rem)
      - Delta badges with semantic colors (green/red/gray)
      - Subtitle, sparkline, and CNE source line
      - "CNE Data" badge with fresh/recent/stale variants
      - Fade-in entry animation
      - Dark mode compatibility with the institutional theme

    Returns:
        str: ES: Bloque <style> CSS listo para inyectar con st.markdown().
             EN: CSS <style> block ready to inject via st.markdown().
    """
    return """<style>
/* ==========================================================================
   ES: KPI Cards v2 — Estándar Observación Electoral Internacional
   EN: KPI Cards v2 — International Electoral Observation Standard
   Versión / Version: 2.0.0
   ========================================================================== */

/* --------------------------------------------------------------------------
   ES: Grid principal 2×3 (desktop) → responsivo
   EN: Main 2×3 grid (desktop) → responsive
   -------------------------------------------------------------------------- */
.kpi-v2-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 18px;
    margin: 8px 0 24px;
}
@media (max-width: 960px) {
    /* ES: Tablet: 2 columnas / EN: Tablet: 2 columns */
    .kpi-v2-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 560px) {
    /* ES: Mobile: 1 columna / EN: Mobile: 1 column */
    .kpi-v2-grid { grid-template-columns: 1fr; }
}

/* --------------------------------------------------------------------------
   ES: Tarjeta individual
   EN: Individual card
   -------------------------------------------------------------------------- */
.kpi-card-v2 {
    --kpi-accent: #00A3E0;            /* ES: Acento por defecto / EN: Default accent */
    position: relative;
    background: linear-gradient(
        148deg,
        rgba(14, 26, 50, 0.98) 0%,
        rgba(10, 18, 36, 0.94) 100%
    );
    border: 1px solid rgba(148, 163, 184, 0.11);
    border-top: 3px solid var(--kpi-accent);   /* ES: Borde top de acento / EN: Top accent border */
    border-radius: 14px;
    padding: 20px 22px 15px;
    box-shadow:
        0 4px 24px rgba(0, 0, 0, 0.30),
        0 1px 4px  rgba(0, 0, 0, 0.18),
        inset 0 1px 0 rgba(255, 255, 255, 0.03);
    transition: transform 0.20s ease, box-shadow 0.20s ease, border-color 0.20s ease;
    cursor: default;
    overflow: hidden;
}
.kpi-card-v2:hover {
    transform: translateY(-3px);
    box-shadow:
        0 14px 40px rgba(0, 0, 0, 0.42),
        0 0 0 1px var(--kpi-accent),
        inset 0 1px 0 rgba(255, 255, 255, 0.04);
}
/* ES: Reflejo decorativo en esquina superior derecha / EN: Decorative reflection in top-right corner */
.kpi-card-v2::after {
    content: '';
    position: absolute;
    top: -1px; right: -1px;
    width: 60px; height: 60px;
    background: radial-gradient(circle at top right, var(--kpi-accent), transparent 70%);
    opacity: 0.06;
    pointer-events: none;
}

/* --------------------------------------------------------------------------
   ES: Cabecera de la tarjeta / EN: Card header
   -------------------------------------------------------------------------- */
.kpi-v2-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 6px;
    margin-bottom: 10px;
}
.kpi-v2-label-es {
    font-size: 0.70rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.13em;
    color: rgba(148, 163, 184, 0.88);
    line-height: 1.3;
}
.kpi-v2-label-en {
    font-size: 0.60rem;
    font-weight: 400;
    color: rgba(100, 116, 139, 0.80);
    letter-spacing: 0.05em;
    margin-top: 1px;
}

/* ES: Ícono de información / EN: Information icon */
.kpi-v2-info-icon {
    font-size: 1.05rem;
    color: rgba(0, 163, 224, 0.45);
    cursor: help;
    flex-shrink: 0;
    line-height: 1;
    padding: 1px 4px;
    border-radius: 50%;
    transition: color 0.18s ease, background 0.18s ease;
    user-select: none;
}
.kpi-v2-info-icon:hover {
    color: rgba(0, 163, 224, 0.95);
    background: rgba(0, 163, 224, 0.12);
}

/* --------------------------------------------------------------------------
   ES: Valor principal grande / EN: Large main value
   -------------------------------------------------------------------------- */
.kpi-v2-value {
    font-size: 2.4rem;
    font-weight: 800;
    color: #F0F4F8;
    letter-spacing: -0.03em;
    line-height: 1.05;
    margin-bottom: 7px;
    word-break: break-all;
    /* ES: Variantes numéricas / EN: Numeric variants */
    font-variant-numeric: tabular-nums;
}

/* --------------------------------------------------------------------------
   ES: Badge de delta con flecha y color semántico
   EN: Delta badge with arrow and semantic color
   -------------------------------------------------------------------------- */
.kpi-v2-delta {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 0.78rem;
    font-weight: 600;
    padding: 3px 9px;
    border-radius: 999px;
    margin-bottom: 7px;
    letter-spacing: 0.01em;
    transition: opacity 0.2s;
}
/* ES: Delta positivo (verde — bueno por defecto) / EN: Positive delta (green — good by default) */
.kpi-delta-positive {
    background: rgba(0, 200, 83, 0.12);
    color: #00C853;
    border: 1px solid rgba(0, 200, 83, 0.28);
}
/* ES: Delta negativo / peligro (rojo) / EN: Negative / danger delta (red) */
.kpi-delta-danger {
    background: rgba(239, 68, 68, 0.12);
    color: #EF4444;
    border: 1px solid rgba(239, 68, 68, 0.28);
}
/* ES: Delta neutro (gris) / EN: Neutral delta (gray) */
.kpi-delta-neutral {
    background: rgba(148, 163, 184, 0.09);
    color: #94A3B8;
    border: 1px solid rgba(148, 163, 184, 0.18);
}
/* ES: Delta advertencia (naranja) / EN: Warning delta (orange) */
.kpi-delta-warning {
    background: rgba(255, 152, 0, 0.12);
    color: #FF9800;
    border: 1px solid rgba(255, 152, 0, 0.28);
}

/* --------------------------------------------------------------------------
   ES: Subtítulo explicativo / EN: Explanatory subtitle
   -------------------------------------------------------------------------- */
.kpi-v2-subtitle {
    font-size: 0.73rem;
    color: rgba(148, 163, 184, 0.72);
    line-height: 1.4;
    margin-top: 1px;
    margin-bottom: 8px;
}

/* --------------------------------------------------------------------------
   ES: Contenedor del sparkline SVG / EN: SVG sparkline container
   -------------------------------------------------------------------------- */
.kpi-v2-sparkline {
    margin: 10px 0 6px;
    line-height: 0;
    border-top: 1px solid rgba(148, 163, 184, 0.07);
    padding-top: 10px;
    opacity: 0.88;
}
.kpi-v2-sparkline svg {
    width: 100%;      /* ES: Ancho completo de la tarjeta / EN: Full card width */
    height: 44px;
    display: block;
}

/* --------------------------------------------------------------------------
   ES: Línea de fuente CNE / EN: CNE source line
   -------------------------------------------------------------------------- */
.kpi-v2-source {
    font-size: 0.60rem;
    color: rgba(100, 116, 139, 0.65);
    margin-top: 5px;
    letter-spacing: 0.02em;
    line-height: 1.5;
}
.kpi-v2-source code {
    /* ES: Referencia de campo JSON del CNE / EN: CNE JSON field reference */
    background: rgba(0, 163, 224, 0.09);
    color: rgba(0, 163, 224, 0.78);
    padding: 0 4px;
    border-radius: 3px;
    font-size: 0.58rem;
    font-family: "SF Mono", "Fira Code", "JetBrains Mono", "Consolas", monospace;
}

/* ==========================================================================
   ES: Badge dinámico "Datos del CNE – Actualizado hace X min"
   EN: Dynamic "CNE Data – Updated X min ago" badge
   ========================================================================== */
.cne-data-badge {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    padding: 5px 15px;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    border: 1px solid transparent;
    margin-bottom: 14px;
    transition: opacity 0.3s;
}
/* ES: Fresco < 15 min (verde) / EN: Fresh < 15 min (green) */
.cne-badge-fresh {
    background: rgba(0, 200, 83, 0.12);
    color: #00C853;
    border-color: rgba(0, 200, 83, 0.30);
}
/* ES: Reciente 15–60 min (naranja) / EN: Recent 15–60 min (orange) */
.cne-badge-recent {
    background: rgba(255, 152, 0, 0.12);
    color: #FF9800;
    border-color: rgba(255, 152, 0, 0.30);
}
/* ES: Desactualizado > 60 min (rojo) / EN: Stale > 60 min (red) */
.cne-badge-stale {
    background: rgba(239, 68, 68, 0.12);
    color: #EF4444;
    border-color: rgba(239, 68, 68, 0.30);
}

/* ES: Sección del resumen ejecutivo / EN: Executive summary section */
.exec-summary-section {
    margin-top: 8px;
    margin-bottom: 0;
}
.exec-summary-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 10px;
    margin-bottom: 6px;
}
.exec-summary-titles {}
.exec-summary-title {
    font-size: 1.15rem;
    font-weight: 700;
    color: #F0F4F8;
    letter-spacing: -0.01em;
    margin: 0;
    padding: 0;
    line-height: 1.3;
}
.exec-summary-subtitle {
    font-size: 0.82rem;
    color: rgba(148, 163, 184, 0.80);
    margin-top: 2px;
    line-height: 1.4;
}
</style>"""


# =========================================================================
# ES: Badge dinámico CNE / EN: Dynamic CNE badge
# =========================================================================

def get_cne_badge_html(minutes_ago: Optional[float]) -> str:
    """ES: Genera el HTML del badge 'Datos del CNE – Actualizado hace X minutos'.

    El color del badge es dinámico según la antigüedad del dato:
      - Verde (cne-badge-fresh): dato fresco, hace < 15 minutos.
      - Naranja (cne-badge-recent): hace 15 a 60 minutos.
      - Rojo (cne-badge-stale): hace > 60 minutos o sin datos.

    EN: Generate HTML for the 'CNE Data – Updated X minutes ago' badge.

    Badge color is dynamic based on data age:
      - Green (cne-badge-fresh): fresh data, < 15 minutes ago.
      - Orange (cne-badge-recent): 15 to 60 minutes ago.
      - Red (cne-badge-stale): > 60 minutes ago or no data.

    Args:
        minutes_ago:
            ES: Minutos transcurridos desde la última actualización del CNE.
                None si el timestamp es desconocido.
            EN: Minutes elapsed since the last CNE update.
                None if the timestamp is unknown.

    Returns:
        str: ES: HTML del badge listo para st.markdown(unsafe_allow_html=True).
             EN: Badge HTML ready for st.markdown(unsafe_allow_html=True).
    """
    if minutes_ago is None:
        # ES: Sin datos de tiempo / EN: No timing data
        return (
            '<span class="cne-data-badge cne-badge-stale">'
            '&#x25CF;&nbsp;Datos del CNE &ndash; Sin actualizaci&oacute;n reciente / No recent update'
            '</span>'
        )

    m = float(minutes_ago)

    # ES: Seleccionar clase CSS según antigüedad / EN: Select CSS class based on age
    if m < 15:
        css_cls = "cne-badge-fresh"
    elif m < 60:
        css_cls = "cne-badge-recent"
    else:
        css_cls = "cne-badge-stale"

    # ES: Formatear tiempo transcurrido bilingüe / EN: Format bilingual elapsed time
    if m < 1:
        elapsed_es = "hace menos de 1&nbsp;min"
        elapsed_en = "less than 1&nbsp;min ago"
    elif m < 60:
        mins = int(m)
        elapsed_es = f"hace {mins}&nbsp;min"
        elapsed_en = f"{mins}&nbsp;min ago"
    else:
        hours = int(m // 60)
        rem_m = int(m % 60)
        elapsed_es = f"hace {hours}h&nbsp;{rem_m}m"
        elapsed_en = f"{hours}h&nbsp;{rem_m}m ago"

    return (
        f'<span class="cne-data-badge {css_cls}">'
        f'&#x25CF;&nbsp;Datos del CNE &ndash; Actualizado {elapsed_es} / Updated {elapsed_en}'
        f'</span>'
    )
