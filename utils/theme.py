"""Reusable institutional theme primitives for C.E.N.T.I.N.E.L.

ES: Variables y estilos reutilizables para el diseño institucional premium.
EN: Reusable variables and style builders for premium institutional design.
"""

from __future__ import annotations

# ES: Paleta institucional obligatoria en modo oscuro.
# EN: Mandatory institutional dark-mode palette.
BG_PRIMARY = "#0A1428"
BG_SURFACE = "#101E3A"
BRAND_BLUE = "#00A3E0"
INTEGRITY_GREEN = "#00C853"
ALERT_ORANGE = "#FF9800"
TEXT_PRIMARY = "#EAF2FF"
TEXT_SECONDARY = "#9DB2D1"
BORDER_SOFT = "rgba(255,255,255,0.08)"
CARD_SHADOW = "0 4px 20px rgba(0,0,0,0.3)"
RADIUS_MD = "12px"
SPACING_PANEL = "24px 32px"

# ES: Configuración oficial de página para Streamlit.
# EN: Official page configuration for Streamlit.
PAGE_CONFIG = {
    "page_title": "C.E.N.T.I.N.E.L. – Centro de Vigilancia Electoral",
    "page_icon": "🛰️",
    "layout": "wide",
    "initial_sidebar_state": "expanded",
}


def build_institutional_css() -> str:
    """Return premium CSS for Streamlit components.

    ES: Retorna CSS premium para componentes Streamlit.
    EN: Return premium CSS for Streamlit components.
    """

    # ES: CSS centralizado para header fijo, tarjetas y sidebar mínima.
    # EN: Centralized CSS for fixed header, cards, and minimal sidebar.
    return f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

        .stApp {{
            background: {BG_PRIMARY};
            color: {TEXT_PRIMARY};
            font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
        }}

        .block-container {{
            padding-top: 8.5rem;
            padding-left: 2rem;
            padding-right: 2rem;
        }}

        h1, h2, h3, h4, h5 {{
            font-family: 'SF Pro Display', 'Inter', sans-serif;
            font-weight: 700;
            letter-spacing: -0.01em;
        }}

        .ce-header {{
            position: fixed;
            top: 0.9rem;
            left: 1.6rem;
            right: 1.6rem;
            z-index: 999;
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 1rem;
            background: linear-gradient(145deg, {BG_SURFACE}, rgba(0,163,224,0.08));
            border: 1px solid {BORDER_SOFT};
            border-radius: {RADIUS_MD};
            box-shadow: {CARD_SHADOW};
            padding: {SPACING_PANEL};
        }}

        .ce-header__left {{ display: flex; align-items: center; gap: 1rem; }}
        .ce-header__left h1 {{ margin: 0; font-size: 1.55rem; }}
        .ce-header__left p {{ margin: 0; color: {TEXT_SECONDARY}; }}
        .ce-header__right {{ text-align: right; }}
        .ce-logo {{ color: {BRAND_BLUE}; font-weight: 800; letter-spacing: .18em; }}
        .ce-badge {{
            display: inline-block;
            background: rgba(0,163,224,.16);
            color: {BRAND_BLUE};
            border: 1px solid rgba(0,163,224,.38);
            border-radius: 999px;
            padding: .45rem .9rem;
            font-size: .79rem;
        }}

        .ce-panel {{
            margin-top: 1rem;
            border: 1px solid {BORDER_SOFT};
            border-radius: {RADIUS_MD};
            box-shadow: {CARD_SHADOW};
            background: {BG_SURFACE};
            padding: {SPACING_PANEL};
        }}

        [data-testid="metric-container"] {{
            border: 1px solid {BORDER_SOFT};
            border-radius: {RADIUS_MD};
            box-shadow: {CARD_SHADOW};
            background: {BG_SURFACE};
            padding: 1rem 1.1rem;
        }}

        section[data-testid="stSidebar"] {{
            background: #0b1730;
            border-right: 1px solid {BORDER_SOFT};
        }}

        .ce-footer {{
            margin-top: 1.4rem;
            padding: .9rem;
            border: 1px solid {BORDER_SOFT};
            border-radius: {RADIUS_MD};
            background: rgba(255,255,255,.02);
            font-size: .82rem;
            color: {TEXT_SECONDARY};
        }}

        .ce-footer a {{ color: {BRAND_BLUE}; text-decoration: none; }}
    </style>
    """
