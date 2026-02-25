"""
======================== INDICE / INDEX ========================
1. Descripcion general / Overview
2. Paleta institucional / Institutional palette
3. CSS profesional / Professional CSS
4. Funciones auxiliares / Helper functions

======================== ESPANOL ========================
Archivo: `dashboard/utils/theme.py`.
Modulo de tema institucional premium para el dashboard C.E.N.T.I.N.E.L.
Inspirado en dashboards de la OEA, UE Election Observation Missions
y el Carter Center.

Paleta de colores, tipografia, sombras, bordes y CSS reutilizable
para un diseno de clase mundial en modo oscuro.

======================== ENGLISH ========================
File: `dashboard/utils/theme.py`.
Premium institutional theme module for the C.E.N.T.I.N.E.L. dashboard.
Inspired by OEA, EU Election Observation Missions, and Carter Center
dashboards.

Color palette, typography, shadows, borders, and reusable CSS
for a world-class dark mode design.
"""

from __future__ import annotations

# =========================================================================
# ES: Paleta institucional de colores
# EN: Institutional color palette
# =========================================================================

# -- Fondos / Backgrounds --
BG_PRIMARY = "#0A1428"          # ES: Fondo principal oscuro / EN: Primary dark background
BG_SECONDARY = "#0E1A32"       # ES: Fondo secundario / EN: Secondary background
BG_PANEL = "rgba(14, 26, 50, 0.92)"  # ES: Panel con transparencia / EN: Panel with transparency
BG_PANEL_SOFT = "rgba(22, 38, 66, 0.85)"  # ES: Panel suave / EN: Soft panel
BG_SIDEBAR = "rgba(8, 16, 32, 0.98)"      # ES: Fondo sidebar / EN: Sidebar background

# -- Acentos institucionales / Institutional accents --
ACCENT_BLUE = "#00A3E0"         # ES: Azul confianza (acento primario) / EN: Trust blue (primary accent)
ACCENT_BLUE_STRONG = "#33B5E5"  # ES: Azul fuerte / EN: Strong blue
ACCENT_BLUE_MUTED = "rgba(0, 163, 224, 0.15)"  # ES: Azul difuminado / EN: Muted blue
ACCENT_BLUE_BORDER = "rgba(0, 163, 224, 0.35)"  # ES: Borde azul / EN: Blue border

# -- Colores semanticos / Semantic colors --
GREEN_INTEGRITY = "#00C853"     # ES: Verde integridad / EN: Integrity green
GREEN_BG = "rgba(0, 200, 83, 0.12)"   # ES: Fondo verde / EN: Green background
GREEN_BORDER = "rgba(0, 200, 83, 0.30)"  # ES: Borde verde / EN: Green border

ALERT_ORANGE = "#FF9800"        # ES: Naranja alertas / EN: Alert orange
ALERT_ORANGE_BG = "rgba(255, 152, 0, 0.12)"  # ES: Fondo naranja / EN: Orange background
ALERT_ORANGE_BORDER = "rgba(255, 152, 0, 0.30)"  # ES: Borde naranja / EN: Orange border

DANGER_RED = "#EF4444"          # ES: Rojo peligro / EN: Danger red
DANGER_RED_BG = "rgba(239, 68, 68, 0.12)"  # ES: Fondo rojo / EN: Red background
DANGER_RED_BORDER = "rgba(239, 68, 68, 0.30)"  # ES: Borde rojo / EN: Red border

# -- Texto / Text --
TEXT_PRIMARY = "#F0F4F8"        # ES: Texto principal / EN: Primary text
TEXT_SECONDARY = "#94A3B8"      # ES: Texto secundario / EN: Secondary text
TEXT_MUTED = "#64748B"          # ES: Texto atenuado / EN: Muted text

# -- Bordes y sombras / Borders and shadows --
BORDER_DEFAULT = "rgba(148, 163, 184, 0.15)"  # ES: Borde por defecto / EN: Default border
SHADOW_DEFAULT = "0 4px 20px rgba(0, 0, 0, 0.3)"  # ES: Sombra estandar / EN: Standard shadow
SHADOW_GLOW = f"0 0 0 1px {ACCENT_BLUE_BORDER}, 0 8px 32px rgba(10, 20, 40, 0.6)"  # ES: Brillo / EN: Glow
BORDER_RADIUS = "12px"          # ES: Radio de borde estandar / EN: Standard border radius
BORDER_RADIUS_LG = "16px"      # ES: Radio de borde grande / EN: Large border radius
BORDER_RADIUS_PILL = "999px"   # ES: Radio pill / EN: Pill radius

# -- Tipografia / Typography --
FONT_FAMILY_BODY = '"Inter", "SF Pro Display", "Segoe UI", system-ui, -apple-system, sans-serif'
FONT_FAMILY_HEADING = '"SF Pro Display", "Inter", "Segoe UI", system-ui, -apple-system, sans-serif'
FONT_FAMILY_MONO = '"SF Mono", "Fira Code", "JetBrains Mono", "Consolas", monospace'

# -- Espaciado / Spacing --
SPACING_SM = "12px"
SPACING_MD = "20px"
SPACING_LG = "28px"
SPACING_XL = "36px"

# -- Graficos Altair / Altair chart colors --
CHART_BLUE = "#00A3E0"
CHART_GREEN = "#00C853"
CHART_ORANGE = "#FF9800"
CHART_RED = "#EF4444"
CHART_GRAY = "#64748B"
CHART_PALETTE = [CHART_BLUE, CHART_GREEN, CHART_ORANGE, CHART_RED, CHART_GRAY]

# =========================================================================
# ES: Version e informacion del tema
# EN: Version and theme information
# =========================================================================
THEME_VERSION = "2.0.0"
THEME_NAME = "C.E.N.T.I.N.E.L. Institutional Dark"


def get_page_config() -> dict:
    """ES: Retorna la configuracion de pagina para st.set_page_config().

    EN: Return page configuration for st.set_page_config().
    """
    return {
        "page_title": "C.E.N.T.I.N.E.L. \u2013 Centro de Vigilancia Electoral",
        "page_icon": "\U0001f6f0\ufe0f",
        "layout": "wide",
        "initial_sidebar_state": "expanded",
    }


def get_institutional_css() -> str:
    """ES: Genera el CSS institucional premium completo.
    Incluye tipografia, colores, sombras, bordes, animaciones
    y estilos de componentes Streamlit.

    EN: Generate the complete premium institutional CSS.
    Includes typography, colors, shadows, borders, animations,
    and Streamlit component styles.
    """
    return f"""
<style>
    /* ============================================================
       ES: Variables CSS raiz / EN: Root CSS variables
       ============================================================ */
    :root {{
        color-scheme: dark;
        --bg: {BG_PRIMARY};
        --bg-secondary: {BG_SECONDARY};
        --panel: {BG_PANEL};
        --panel-soft: {BG_PANEL_SOFT};
        --text: {TEXT_PRIMARY};
        --text-secondary: {TEXT_SECONDARY};
        --text-muted: {TEXT_MUTED};
        --accent: {ACCENT_BLUE};
        --accent-strong: {ACCENT_BLUE_STRONG};
        --accent-muted: {ACCENT_BLUE_MUTED};
        --green: {GREEN_INTEGRITY};
        --orange: {ALERT_ORANGE};
        --red: {DANGER_RED};
        --border: {BORDER_DEFAULT};
        --shadow: {SHADOW_DEFAULT};
        --glow: {SHADOW_GLOW};
        --radius: {BORDER_RADIUS};
        --radius-lg: {BORDER_RADIUS_LG};
    }}

    /* ============================================================
       ES: Tipografia global / EN: Global typography
       ============================================================ */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    html, body, [class*="css"] {{
        font-family: {FONT_FAMILY_BODY};
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
    }}
    h1, h2, h3, h4, h5, h6 {{
        font-family: {FONT_FAMILY_HEADING};
        font-weight: 700;
        letter-spacing: -0.02em;
    }}
    code, pre, .stCode {{
        font-family: {FONT_FAMILY_MONO};
    }}

    /* ============================================================
       ES: Fondo de la aplicacion / EN: App background
       ============================================================ */
    .stApp {{
        background:
            radial-gradient(ellipse at 15% 5%, rgba(0, 163, 224, 0.08), transparent 50%),
            radial-gradient(ellipse at 85% 95%, rgba(0, 200, 83, 0.04), transparent 45%),
            {BG_PRIMARY};
        color: var(--text);
    }}
    .block-container {{
        max-width: 1320px;
        padding-top: 1rem;
        padding-left: 2.5rem;
        padding-right: 2.5rem;
    }}

    /* ============================================================
       ES: Sidebar institucional / EN: Institutional sidebar
       ============================================================ */
    section[data-testid="stSidebar"] {{
        background: {BG_SIDEBAR};
        border-right: 1px solid var(--border);
    }}
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] label {{
        color: var(--text);
        font-size: 0.88rem;
    }}
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stRadio label {{
        font-weight: 500;
        text-transform: uppercase;
        font-size: 0.72rem;
        letter-spacing: 0.08em;
        color: var(--text-secondary);
    }}

    /* ============================================================
       ES: Header fijo institucional / EN: Fixed institutional header
       ============================================================ */
    .centinel-header {{
        background: linear-gradient(135deg, {BG_SECONDARY}, rgba(0, 163, 224, 0.06));
        border: 1px solid var(--border);
        border-radius: var(--radius-lg);
        padding: 24px 32px;
        margin-bottom: 24px;
        box-shadow: var(--shadow);
        position: relative;
        overflow: hidden;
    }}
    .centinel-header::before {{
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, {ACCENT_BLUE}, {GREEN_INTEGRITY}, {ACCENT_BLUE});
    }}
    .centinel-header .header-top {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 20px;
        flex-wrap: wrap;
    }}
    .centinel-header .header-logo {{
        font-size: 1.65rem;
        font-weight: 800;
        letter-spacing: 0.12em;
        color: var(--accent);
        white-space: nowrap;
    }}
    .centinel-header .header-title {{
        font-size: 1.2rem;
        font-weight: 600;
        color: var(--text);
        letter-spacing: -0.01em;
    }}
    .centinel-header .header-title-en {{
        font-size: 0.82rem;
        color: var(--text-secondary);
        font-weight: 400;
        margin-top: 2px;
    }}
    .centinel-header .header-badge {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 6px 16px;
        border-radius: {BORDER_RADIUS_PILL};
        background: {ACCENT_BLUE_MUTED};
        color: var(--accent);
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.04em;
        border: 1px solid {ACCENT_BLUE_BORDER};
        white-space: nowrap;
    }}

    /* ============================================================
       ES: Hero con metricas / EN: Hero with metrics
       ============================================================ */
    .hero-section {{
        background: linear-gradient(135deg, rgba(0, 163, 224, 0.08), rgba(14, 26, 50, 0.95));
        border: 1px solid var(--border);
        border-radius: var(--radius-lg);
        padding: 28px 32px;
        box-shadow: var(--glow);
        margin-bottom: 20px;
    }}
    .hero-section h2 {{
        font-size: 1.5rem;
        margin: 0 0 6px;
        color: var(--text);
    }}
    .hero-section .hero-subtitle {{
        color: var(--text-secondary);
        font-size: 0.9rem;
        margin: 0 0 16px;
        line-height: 1.5;
    }}
    .hero-meta {{
        display: flex;
        gap: 8px 16px;
        flex-wrap: wrap;
        font-size: 0.76rem;
        color: var(--text-muted);
    }}
    .hero-meta span {{
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 4px 10px;
        background: rgba(0, 163, 224, 0.06);
        border-radius: {BORDER_RADIUS_PILL};
        border: 1px solid rgba(0, 163, 224, 0.10);
    }}

    /* ============================================================
       ES: Panel de vidrio / EN: Glass panel
       ============================================================ */
    .glass {{
        background: var(--panel);
        border: 1px solid var(--border);
        border-radius: var(--radius);
        padding: 24px;
        box-shadow: var(--shadow);
        backdrop-filter: blur(12px);
    }}

    /* ============================================================
       ES: Tarjetas KPI / EN: KPI cards
       ============================================================ */
    .kpi-card {{
        background: var(--panel-soft);
        border-radius: var(--radius);
        padding: 20px 24px;
        border: 1px solid var(--border);
        box-shadow: var(--shadow);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }}
    .kpi-card:hover {{
        transform: translateY(-2px);
        box-shadow: 0 8px 28px rgba(0, 0, 0, 0.4);
    }}
    .kpi-card h4 {{
        margin: 0;
        font-size: 0.68rem;
        text-transform: uppercase;
        letter-spacing: 0.14em;
        color: var(--text-muted);
        font-weight: 600;
    }}
    .kpi-card .kpi-value {{
        margin: 8px 0 4px;
        font-size: 1.5rem;
        font-weight: 700;
        color: var(--text);
        word-break: break-all;
    }}
    .kpi-card .kpi-caption {{
        font-size: 0.76rem;
        color: var(--text-secondary);
    }}

    /* ============================================================
       ES: Pildoras de estado / EN: Status pills
       ============================================================ */
    .status-pill {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 5px 14px;
        border-radius: {BORDER_RADIUS_PILL};
        font-size: 0.76rem;
        font-weight: 600;
        letter-spacing: 0.02em;
    }}
    .status-pill--ok {{
        background: {GREEN_BG};
        color: var(--green);
        border: 1px solid {GREEN_BORDER};
    }}
    .status-pill--warning {{
        background: {ALERT_ORANGE_BG};
        color: var(--orange);
        border: 1px solid {ALERT_ORANGE_BORDER};
    }}
    .status-pill--danger {{
        background: {DANGER_RED_BG};
        color: var(--red);
        border: 1px solid {DANGER_RED_BORDER};
    }}
    .status-pill--info {{
        background: {ACCENT_BLUE_MUTED};
        color: var(--accent);
        border: 1px solid {ACCENT_BLUE_BORDER};
    }}

    /* ============================================================
       ES: Panel lateral de estado / EN: Status side panel
       ============================================================ */
    .status-panel {{
        background: var(--panel);
        border: 1px solid var(--border);
        border-radius: var(--radius);
        padding: 24px;
        box-shadow: var(--shadow);
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }}
    .status-panel h3 {{
        margin: 8px 0;
        font-size: 1.1rem;
    }}
    .status-panel .status-detail {{
        font-size: 0.82rem;
        color: var(--text-secondary);
        margin: 4px 0;
    }}

    /* ============================================================
       ES: Grilla de micro-tarjetas / EN: Micro-card grid
       ============================================================ */
    .card-grid {{
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 12px;
    }}
    @media (max-width: 768px) {{
        .card-grid {{ grid-template-columns: repeat(2, 1fr); }}
    }}
    .micro-card {{
        background: rgba(14, 26, 50, 0.75);
        border-radius: var(--radius);
        padding: 16px 20px;
        border: 1px solid var(--border);
        transition: border-color 0.2s ease;
    }}
    .micro-card:hover {{
        border-color: {ACCENT_BLUE_BORDER};
    }}
    .micro-card h5 {{
        margin: 0 0 6px;
        font-size: 0.68rem;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.16em;
        font-weight: 600;
    }}
    .micro-card p {{
        margin: 0;
        font-size: 1rem;
        font-weight: 600;
        color: var(--text);
    }}

    /* ============================================================
       ES: Titulo de seccion / EN: Section title
       ============================================================ */
    .section-title {{
        margin-top: 28px;
        font-size: 1.1rem;
        font-weight: 700;
        color: var(--text);
        letter-spacing: -0.01em;
    }}
    .section-subtitle {{
        color: var(--text-secondary);
        font-size: 0.85rem;
        margin-top: 2px;
    }}

    /* ============================================================
       ES: Badges / EN: Badges
       ============================================================ */
    .badge {{
        display: inline-block;
        padding: 4px 12px;
        border-radius: {BORDER_RADIUS_PILL};
        background: {ACCENT_BLUE_MUTED};
        color: var(--accent);
        font-size: 0.72rem;
        font-weight: 600;
        border: 1px solid {ACCENT_BLUE_BORDER};
        letter-spacing: 0.02em;
    }}

    /* ============================================================
       ES: Componentes Streamlit personalizados
       EN: Custom Streamlit components
       ============================================================ */
    div[data-testid="stMetric"] {{
        background: var(--panel-soft);
        padding: 16px 20px;
        border-radius: var(--radius);
        border: 1px solid var(--border);
    }}
    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
        border-bottom: 1px solid var(--border);
        padding-bottom: 0;
    }}
    .stTabs [data-baseweb="tab"] {{
        background: transparent;
        border-radius: {BORDER_RADIUS_PILL};
        border: 1px solid transparent;
        padding: 8px 18px;
        color: var(--text-secondary);
        font-weight: 500;
        font-size: 0.88rem;
        transition: all 0.2s ease;
    }}
    .stTabs [data-baseweb="tab"]:hover {{
        background: {ACCENT_BLUE_MUTED};
        color: var(--text);
    }}
    .stTabs [aria-selected="true"] {{
        background: {ACCENT_BLUE_MUTED};
        color: var(--accent);
        border-color: {ACCENT_BLUE_BORDER};
        font-weight: 600;
    }}
    .streamlit-expanderHeader {{
        font-weight: 600;
        font-size: 0.92rem;
    }}

    /* ============================================================
       ES: Separador personalizado / EN: Custom divider
       ============================================================ */
    .centinel-divider {{
        height: 1px;
        background: linear-gradient(90deg, transparent, var(--border), transparent);
        margin: 24px 0;
        border: none;
    }}

    /* ============================================================
       ES: Footer institucional / EN: Institutional footer
       ============================================================ */
    .centinel-footer {{
        text-align: center;
        padding: 20px 0 8px;
        font-size: 0.72rem;
        color: var(--text-muted);
        border-top: 1px solid var(--border);
        margin-top: 32px;
    }}
    .centinel-footer a {{
        color: var(--accent);
        text-decoration: none;
    }}
    .centinel-footer a:hover {{
        text-decoration: underline;
    }}

    /* ============================================================
       ES: Animacion de entrada / EN: Fade-in animation
       ============================================================ */
    .fade-in {{
        animation: centinelFadeIn 0.8s ease-out;
    }}
    @keyframes centinelFadeIn {{
        from {{ opacity: 0; transform: translateY(8px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}

    /* ============================================================
       ES: Barra de alerta superior / EN: Top alert bar
       ============================================================ */
    .alert-bar {{
        margin-top: 8px;
    }}

    /* ============================================================
       ES: Sidebar footer / EN: Sidebar footer
       ============================================================ */
    .sidebar-footer {{
        font-size: 0.68rem;
        color: var(--text-muted);
        padding-top: 12px;
        border-top: 1px solid var(--border);
        line-height: 1.6;
    }}
    .sidebar-footer a {{
        color: var(--accent);
        text-decoration: none;
    }}
</style>
"""


def get_header_html(
    latest_label: str = "N/D",
    root_hash_short: str = "N/D",
    snapshot_label: str = "N/D",
    snapshot_hash_short: str = "N/D",
) -> str:
    """ES: Genera el HTML del header institucional fijo superior.
    Incluye logo, titulo bilingue y badge de neutralidad politica.

    EN: Generate the fixed top institutional header HTML.
    Includes logo, bilingual title, and political neutrality badge.
    """
    return f"""
<div class="centinel-header fade-in">
  <div class="header-top">
    <div>
      <div class="header-logo">C.E.N.T.I.N.E.L.</div>
      <div class="header-title">Centro de Vigilancia Electoral</div>
      <div class="header-title-en">Electoral Surveillance Center</div>
    </div>
    <div class="header-badge">
      \U0001f6e1\ufe0f Auditor\u00eda T\u00e9cnica Independiente &ndash; Agn\u00f3stica a Partidos Pol\u00edticos
    </div>
  </div>
  <div style="margin-top: 16px;">
    <div class="hero-meta">
      <span>\U0001f50e Modo auditor\u00eda: Activo</span>
      <span>\U0001f6f0\ufe0f \u00daltima actualizaci\u00f3n: {latest_label}</span>
      <span>\U0001f9fe Snapshot: {snapshot_label}</span>
      <span>\U0001f510 Hash ra\u00edz: {root_hash_short}</span>
      <span>\U0001f9ec Hash snapshot: {snapshot_hash_short}</span>
    </div>
  </div>
</div>
"""


def get_status_panel_html(
    polling_status: dict,
    department: str,
    snapshot_count: int,
    latest_label: str,
) -> str:
    """ES: Genera el HTML del panel lateral de estado.
    Muestra estado de polling, cobertura y metricas clave.

    EN: Generate the status side panel HTML.
    Shows polling status, coverage, and key metrics.
    """
    # ES: Determinar clase de pildora / EN: Determine pill class
    pill_class = "status-pill--ok"
    if "danger" in polling_status.get("class", ""):
        pill_class = "status-pill--danger"
    elif "warning" in polling_status.get("class", ""):
        pill_class = "status-pill--warning"

    return f"""
<div class="status-panel">
  <div>
    <div class="status-pill {pill_class}">{polling_status['label']}</div>
    <h3>{department}</h3>
    <div class="status-detail">Cobertura activa / Active coverage</div>
  </div>
  <div>
    <div class="status-detail">Snapshots observados: <strong>{snapshot_count}</strong></div>
    <div class="status-detail">\u00daltimo lote: <strong>{latest_label}</strong></div>
    <div class="status-detail">Estado: {polling_status['detail']}</div>
  </div>
</div>
"""


def get_kpi_html(label: str, value: str, caption: str) -> str:
    """ES: Genera el HTML de una tarjeta KPI individual.

    EN: Generate HTML for a single KPI card.
    """
    return f"""
<div class="kpi-card">
  <h4>{label}</h4>
  <div class="kpi-value">{value}</div>
  <div class="kpi-caption">{caption}</div>
</div>
"""


def get_micro_cards_html(cards: list[tuple[str, str]]) -> str:
    """ES: Genera la grilla de micro-tarjetas con pares (titulo, valor).

    EN: Generate the micro-card grid with (title, value) pairs.
    """
    items = ""
    for title, value in cards:
        items += f"""
    <div class="micro-card">
      <h5>{title}</h5>
      <p>{value}</p>
    </div>"""
    return f'<div class="card-grid">{items}\n</div>'


def get_sidebar_footer_html(
    version: str = "v9.0",
    last_update: str = "N/D",
    methodology_url: str = "",
) -> str:
    """ES: Genera el HTML del footer del sidebar con version,
    ultima actualizacion y enlace a metodologia.

    EN: Generate sidebar footer HTML with version,
    last update, and methodology link.
    """
    method_link = ""
    if methodology_url:
        method_link = f'<br/><a href="{methodology_url}" target="_blank">Metodolog\u00eda / Methodology</a>'
    return f"""
<div class="sidebar-footer">
  <strong>C.E.N.T.I.N.E.L.</strong> {version}<br/>
  \u00daltima act. JSON: {last_update}{method_link}<br/>
  Sistema agn\u00f3stico a partidos pol\u00edticos
</div>
"""


def get_footer_html() -> str:
    """ES: Genera el HTML del footer principal del dashboard.

    EN: Generate the main dashboard footer HTML.
    """
    return """
<div class="centinel-footer fade-in">
  <strong>C.E.N.T.I.N.E.L.</strong> &mdash; Centro de Vigilancia Electoral<br/>
  Auditor&iacute;a t&eacute;cnica independiente &middot; Sistema agn&oacute;stico a partidos pol&iacute;ticos<br/>
  Electoral Surveillance Center &middot; Independent technical audit &middot; Politically agnostic system
</div>
"""
