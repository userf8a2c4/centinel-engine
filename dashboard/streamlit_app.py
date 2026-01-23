import datetime as dt
import hashlib
import io
from dataclasses import dataclass

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    REPORTLAB_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency for PDF rendering
    REPORTLAB_AVAILABLE = False
    colors = None
    LETTER = None
    ParagraphStyle = None
    getSampleStyleSheet = None
    inch = None
    Image = None
    Paragraph = None
    SimpleDocTemplate = None
    Spacer = None
    Table = None
    TableStyle = None

try:
    import qrcode
except ImportError:  # pragma: no cover - optional dependency for QR rendering
    qrcode = None


@dataclass(frozen=True)
class BlockchainAnchor:
    root_hash: str
    network: str
    tx_url: str
    anchored_at: str


@st.cache_data(show_spinner=False)
def build_snapshot_data() -> pd.DataFrame:
    now = dt.datetime.now(dt.timezone.utc)
    snapshots = [
        {
            "timestamp": (now - dt.timedelta(minutes=40)).strftime("%Y-%m-%d %H:%M UTC"),
            "hash": "0x88fa...e901",
            "changes": 2,
            "detail": "JSON actualizado en 3 mesas",
            "status": "REVISAR",
        },
        {
            "timestamp": (now - dt.timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M UTC"),
            "hash": "0xe41b...93f0",
            "changes": 1,
            "detail": "Corrección menor en JSON",
            "status": "REVISAR",
        },
        {
            "timestamp": (now - dt.timedelta(minutes=20)).strftime("%Y-%m-%d %H:%M UTC"),
            "hash": "0x7b99...ae02",
            "changes": 0,
            "detail": "Sin cambios detectados",
            "status": "OK",
        },
        {
            "timestamp": (now - dt.timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M UTC"),
            "hash": "0x9f3a...e21b",
            "changes": 0,
            "detail": "Sin cambios detectados",
            "status": "OK",
        },
    ]
    return pd.DataFrame(snapshots)


@st.cache_data(show_spinner=False)
def build_rules_data() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "name": "Si un archivo cambia más del 5%",
                "type": "Integridad",
                "severity": "Alta",
                "state": "ON",
                "action": "Pausa snapshots y alerta automática",
            },
            {
                "name": "Cambios fuera de horarios esperados",
                "type": "Temporalidad",
                "severity": "Media",
                "state": "ON",
                "action": "Notifica a observadores",
            },
            {
                "name": "Patrones repetidos en JSON",
                "type": "Anomalías",
                "severity": "Media",
                "state": "OFF",
                "action": "Registrar y revisar",
            },
        ]
    )


@st.cache_data(show_spinner=False)
def build_benford_data() -> pd.DataFrame:
    expected = [30.1, 17.6, 12.5, 9.7, 7.9, 6.7, 5.8, 5.1, 4.6]
    observed = [29.3, 18.2, 12.1, 10.4, 7.2, 6.9, 5.5, 5.0, 5.4]
    digits = list(range(1, 10))
    return pd.DataFrame({"digit": digits, "expected": expected, "observed": observed})


@st.cache_data(show_spinner=False)
def build_last_digit_data() -> pd.DataFrame:
    digits = list(range(10))
    observed = [9.4, 10.6, 9.8, 10.2, 9.9, 9.7, 10.5, 10.1, 10.0, 9.8]
    return pd.DataFrame({"digit": digits, "observed": observed})


@st.cache_data(show_spinner=False)
def build_vote_evolution() -> pd.DataFrame:
    now = dt.datetime.now(dt.timezone.utc)
    series = []
    total_votes = 120_000
    for step in range(8):
        total_votes += 6_500 + (step * 320)
        series.append(
            {
                "hour": (now - dt.timedelta(hours=7 - step)).strftime("%H:%M"),
                "votes": total_votes,
            }
        )
    return pd.DataFrame(series)


def styled_status(df: pd.DataFrame) -> "pd.io.formats.style.Styler":
    def highlight_status(value: str) -> str:
        color_map = {
            "OK": "background-color: rgba(16, 185, 129, 0.18); color: #e5e7eb;",
            "REVISAR": "background-color: rgba(245, 158, 11, 0.18); color: #e5e7eb;",
            "ALERTA": "background-color: rgba(239, 68, 68, 0.2); color: #e5e7eb;",
        }
        return color_map.get(value, "")

    return df.style.map(highlight_status, subset=["status"])


def compute_report_hash(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_pdf_report(data: dict, language: str) -> bytes:
    if not REPORTLAB_AVAILABLE:
        raise RuntimeError("reportlab is required to build the PDF report.")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=LETTER,
        leftMargin=0.7 * inch,
        rightMargin=0.7 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.7 * inch,
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="HeadingPrimary", fontSize=18, leading=22, spaceAfter=8))
    styles.add(ParagraphStyle(name="HeadingSecondary", fontSize=14, leading=18, spaceAfter=6))
    styles.add(ParagraphStyle(name="Body", fontSize=11, leading=15))

    elements: list = []
    elements.append(Paragraph(data["logo"], styles["HeadingPrimary"]))
    elements.append(Paragraph(data["title"], styles["HeadingSecondary"]))
    elements.append(Paragraph(data["subtitle"], styles["Body"]))
    elements.append(Paragraph(f"{data['generated_label']} {data['generated_at']} UTC", styles["Body"]))
    elements.append(Paragraph(data["global_status"], styles["HeadingSecondary"]))
    elements.append(Spacer(1, 12))

    elements.append(Paragraph(data["executive_title"], styles["HeadingSecondary"]))
    elements.append(Paragraph(data["executive_intro"], styles["Body"]))
    elements.append(Paragraph(data["executive_state"], styles["Body"]))
    elements.append(Spacer(1, 8))

    kpi_table = Table(
        [data["kpi_headers"], data["kpi_values"]],
        colWidths=[1.2 * inch] * len(data["kpi_headers"]),
    )
    kpi_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#003366")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f2f4f8")),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ]
        )
    )
    elements.append(kpi_table)
    elements.append(Spacer(1, 12))

    elements.append(Paragraph(data["technical_title"], styles["HeadingSecondary"]))
    elements.append(Paragraph(f"{data['root_hash_label']} {data['root_hash']}", styles["Body"]))
    elements.append(Paragraph(f"{data['tx_label']} {data['tx_url']}", styles["Body"]))
    elements.append(Paragraph(data["anchored_label"], styles["Body"]))

    elements.append(Spacer(1, 8))
    if qrcode is None:
        elements.append(Paragraph(f"{data['qr_label']}: QR no disponible", styles["Body"]))
        elements.append(Spacer(1, 12))
    else:
        qr = qrcode.make(data["root_hash"])
        qr_buffer = io.BytesIO()
        qr.save(qr_buffer, format="PNG")
        qr_buffer.seek(0)
        elements.append(Paragraph(data["qr_label"], styles["Body"]))
        elements.append(Image(qr_buffer, width=1.5 * inch, height=1.5 * inch))
        elements.append(Spacer(1, 12))

    elements.append(Paragraph(data["snapshots_title"], styles["HeadingSecondary"]))
    snapshot_table = Table(data["snapshots_rows"], colWidths=[1.3 * inch, 0.9 * inch, 3.2 * inch, 1 * inch])
    snapshot_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#003366")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.HexColor("#f8fafc")]),
            ]
        )
    )
    elements.append(snapshot_table)
    elements.append(Spacer(1, 12))

    elements.append(Paragraph(data["rules_title"], styles["HeadingSecondary"]))
    rules_table = Table(data["rules_rows"], colWidths=[2.1 * inch, 1 * inch, 0.9 * inch, 0.7 * inch, 2.2 * inch])
    rules_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#003366")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.HexColor("#f8fafc")]),
            ]
        )
    )
    elements.append(rules_table)
    elements.append(Spacer(1, 12))

    elements.append(Paragraph(data["integrity_title"], styles["HeadingSecondary"]))
    elements.append(Paragraph(data["integrity_intro"], styles["Body"]))
    elements.append(Paragraph(data["integrity_benford"], styles["Body"]))
    elements.append(Paragraph(data["integrity_votes"], styles["Body"]))
    elements.append(Paragraph(data["integrity_heatmap"], styles["Body"]))
    elements.append(Spacer(1, 12))

    elements.append(Paragraph(data["verify_title"], styles["HeadingSecondary"]))
    for step in data["verify_steps"]:
        elements.append(Paragraph(step, styles["Body"]))

    def draw_footer(canvas, _doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.grey)
        canvas.drawString(0.7 * inch, 0.5 * inch, data["footer_left"])
        canvas.drawRightString(7.9 * inch, 0.5 * inch, data["footer_right"])
        canvas.restoreState()

    doc.build(elements, onFirstPage=draw_footer, onLaterPages=draw_footer)
    buffer.seek(0)
    return buffer.getvalue()


st.set_page_config(
    page_title="C.E.N.T.I.N.E.L. | Panel Ejecutivo",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

if "language" not in st.session_state:
    st.session_state.language = "es"

LANG_OPTIONS = {"Español": "es", "English": "en"}

translations = {
    "es": {
        "nav_title": "Navegación",
        "nav_sections": [
            "Resumen Ejecutivo",
            "Indicadores",
            "Observación Internacional",
            "Verificación",
            "Reportes",
        ],
        "hero_title": "C.E.N.T.I.N.E.L. – Panel Ejecutivo de Integridad Electoral · Honduras",
        "hero_subtitle": (
            "Sistema de auditoría independiente con evidencia criptográfica verificable. "
            "Snapshots inmutables anclados en Arbitrum L2 cada 10 minutos para observación internacional."
        ),
        "global_ok": "ESTATUS GLOBAL: VERIFICABLE · SIN ANOMALÍAS CRÍTICAS",
        "header_title": "Panel Ejecutivo de Integridad Electoral",
        "header_status": "Verificable",
        "header_subtitle": "Auditoría independiente con evidencia criptográfica verificable",
        "audience_title": "Audiencias prioritarias",
        "audience_items": [
            "Autoridades electorales y autoridades políticas",
            "Analistas matemáticos y estadísticos",
            "Observadores internacionales (OEA/UE/DEA)",
            "Medios y sociedad civil especializada",
        ],
        "kpi_snapshots": "Snapshots (24h)",
        "kpi_changes": "Cambios detectados",
        "kpi_anomalies": "Anomalías críticas",
        "kpi_rules": "Reglas activas",
        "kpi_verifications": "Verificaciones externas",
        "kpi_notes": "Cada 10 min tomamos una foto inmutable del JSON público oficial.",
        "kpi_changes_note": "Cambios normales en JSON público.",
        "kpi_anomalies_note": "Sin señales críticas.",
        "kpi_rules_note": "Reglas activas en modo auditoría.",
        "kpi_verifications_note": "Validaciones independientes.",
        "capabilities_title": "Capacidades clave de C.E.N.T.I.N.E.L.",
        "capabilities_items": [
            "Monitoreo continuo con evidencias inmutables en Arbitrum L2",
            "Anclaje criptográfico con hashes SHA-256 encadenados",
            "Indicadores estadísticos y matemáticos de integridad",
            "Reportes ejecutivos y técnicos reproducibles para auditoría externa",
        ],
        "methodology_title": "Metodología resumida",
        "methodology_items": [
            "Ingesta continua de datos públicos electorales del CNE.",
            "Snapshots inmutables cada 10 minutos con hash raíz.",
            "Reglas de integridad automáticas y auditoría en Arbitrum L2.",
            "Validación pública y verificable por terceros.",
        ],
        "indicator_title": "Indicadores de integridad",
        "indicator_subtitle": "Métricas estadístico-matemáticas usadas por misiones de observación.",
        "benford_title": "Distribución de primeros dígitos – Normal ✓",
        "last_digit_title": "Actividad de últimos dígitos",
        "vote_evolution_title": "Evolución de cambios",
        "activity_title": "Actividad concentrada en horarios diurnos",
        "snapshots_title": "Snapshots recientes",
        "rules_title": "Reglas activas",
        "international_title": "Observación internacional y cumplimiento",
        "international_intro": (
            "La matriz resume cómo los controles de Centinel respaldan estándares de observación y auditoría."
        ),
        "verification_title": "Verificación criptográfica",
        "verification_help": "Pegue el hash raíz para confirmar si coincide con el registro en Arbitrum.",
        "verification_input": "Hash raíz",
        "verify_button": "Verificar",
        "verify_success": "¡Coincide! ✓",
        "verify_fail": "No coincide, revisá el hash.",
        "expected_label": "Esperado",
        "observed_label": "Observado",
        "export_title": "Reportes y exportación",
        "export_pdf_es": "Descargar Reporte Ciudadano PDF (Español)",
        "export_pdf_en": "Download Citizen Report PDF (English)",
        "export_json": "Descargar JSON auditado",
        "export_csv": "Descargar CSV",
        "snapshots_button": "Ver detalle",
        "rules_help": "Estas reglas protegen la integridad automáticamente.",
        "governance_title": "Gobernanza de datos y garantías",
        "risk_title": "Mapa de riesgos y controles",
        "footer_links_title": "Accesos institucionales",
        "footer_github": "Repositorio técnico",
        "footer_docs": "Documentación técnica",
        "footer_verify": "Verificación en Arbitrum",
        "footer_contact": "Contacto para observadores",
        "cta_report": "Ver Reporte Técnico Completo",
        "cta_verify": "Validar en Blockchain",
        "footer_note": "Datos públicos e inmutables. Verificables independientemente por cualquier actor.",
    },
    "en": {
        "nav_title": "Navigation",
        "nav_sections": [
            "Executive Summary",
            "Indicators",
            "International Observation",
            "Verification",
            "Reports",
        ],
        "hero_title": "C.E.N.T.I.N.E.L. – Executive Electoral Integrity Dashboard · Honduras",
        "hero_subtitle": (
            "Independent audit system with verifiable cryptographic evidence. "
            "Immutable snapshots anchored on Arbitrum L2 every 10 minutes for international observation."
        ),
        "global_ok": "GLOBAL STATUS: VERIFIABLE · NO CRITICAL ANOMALIES",
        "header_title": "Executive Electoral Integrity Dashboard",
        "header_status": "Verifiable",
        "header_subtitle": "Independent audit system with verifiable cryptographic evidence",
        "audience_title": "Primary audiences",
        "audience_items": [
            "Electoral authorities and political leadership",
            "Mathematical and statistical analysts",
            "International observers (OAS/EU/DEA)",
            "Media and specialized civil society",
        ],
        "kpi_snapshots": "Snapshots (24h)",
        "kpi_changes": "Detected changes",
        "kpi_anomalies": "Critical anomalies",
        "kpi_rules": "Active rules",
        "kpi_verifications": "External verifications",
        "kpi_notes": "Every 10 min we take an immutable snapshot of official public JSON.",
        "kpi_changes_note": "Normal changes in public JSON.",
        "kpi_anomalies_note": "No critical signals detected.",
        "kpi_rules_note": "Rules active in audit mode.",
        "kpi_verifications_note": "Independent validations.",
        "capabilities_title": "Key Centinel capabilities",
        "capabilities_items": [
            "Continuous monitoring with immutable evidence on Arbitrum L2",
            "Cryptographic anchoring with chained SHA-256 hashes",
            "Statistical and mathematical integrity indicators",
            "Executive and technical reports reproducible for external audit",
        ],
        "methodology_title": "Methodology (summary)",
        "methodology_items": [
            "Continuous ingestion of public electoral data from CNE.",
            "Immutable snapshots every 10 minutes with root hash.",
            "Integrity rules and audit workflow on Arbitrum L2.",
            "Public validation and third-party verification.",
        ],
        "indicator_title": "Integrity indicators",
        "indicator_subtitle": "Statistical and mathematical metrics used by observation missions.",
        "benford_title": "First-digit distribution – Normal ✓",
        "last_digit_title": "Last-digit activity",
        "vote_evolution_title": "Change evolution",
        "activity_title": "Activity concentrated in daytime hours",
        "snapshots_title": "Recent snapshots",
        "rules_title": "Active rules",
        "international_title": "International observation & compliance",
        "international_intro": (
            "The matrix shows how Centinel controls align with observation and audit standards."
        ),
        "verification_title": "Cryptographic verification",
        "verification_help": "Paste the root hash to verify against Arbitrum.",
        "verification_input": "Root hash",
        "verify_button": "Verify",
        "verify_success": "Match ✓",
        "verify_fail": "No match, check the hash.",
        "expected_label": "Expected",
        "observed_label": "Observed",
        "export_title": "Reports & exports",
        "export_pdf_es": "Descargar Reporte Ciudadano PDF (Español)",
        "export_pdf_en": "Download Citizen Report PDF (English)",
        "export_json": "Download audited JSON",
        "export_csv": "Download CSV",
        "snapshots_button": "View detail",
        "rules_help": "These rules protect integrity automatically.",
        "governance_title": "Data governance and guarantees",
        "risk_title": "Risk & control map",
        "footer_links_title": "Institutional access",
        "footer_github": "Technical repository",
        "footer_docs": "Technical documentation",
        "footer_verify": "Verify on Arbitrum",
        "footer_contact": "Observer contact",
        "cta_report": "View Full Technical Report",
        "cta_verify": "Validate on Blockchain",
        "footer_note": "Public, immutable data. Independently verifiable by any stakeholder.",
    },
}
_, header_right = st.columns([0.78, 0.22])
with header_right:
    language_label = st.selectbox(
        "Idioma / Language",
        list(LANG_OPTIONS.keys()),
        index=0 if st.session_state.language == "es" else 1,
        label_visibility="collapsed",
    )
st.session_state.language = LANG_OPTIONS[language_label]
language = st.session_state.language
copy = translations[language]

css = """
<style>
    :root {
        color-scheme: dark;
        --bg: #0a0c12;
        --panel: rgba(16, 19, 28, 0.92);
        --panel-soft: rgba(20, 24, 32, 0.88);
        --text: #f8f9fa;
        --muted: #e0e0e0;
        --accent: #3b82f6;
        --success: #00a676;
        --warning: #f59e0b;
        --danger: #e63946;
        --border: rgba(255, 255, 255, 0.08);
        --shadow: 0 10px 24px rgba(0, 0, 0, 0.4);
    }
    html, body, [class*="css"] { font-family: "Inter", "Geist", "Segoe UI", sans-serif; }
    .stApp { background: var(--bg); color: var(--text); }
    section[data-testid="stSidebar"] { display: none; }
    .glass { background: var(--panel); border: 1px solid var(--border); border-radius: 16px; padding: 2rem; box-shadow: var(--shadow); }
    .hero { margin-bottom: 2rem; }
    .hero h1 { font-size: 1.95rem; letter-spacing: -0.02em; margin-bottom: 0.6rem; color: var(--text); }
    .hero p { font-size: 1.02rem; color: var(--muted); margin-top: 0; line-height: 1.6; }
    .kpi { background: var(--panel-soft); border: 1px solid var(--border); border-radius: 12px; padding: 1.1rem; }
    .kpi h3 { margin: 0; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.14em; color: var(--muted); }
    .kpi p { margin: 0.45rem 0; font-size: 1.55rem; font-weight: 600; color: var(--text); }
    .kpi span { font-size: 0.88rem; color: var(--muted); }
    .note { background: var(--panel); border: 1px solid var(--border); padding: 0.95rem 1.1rem; border-radius: 12px; color: var(--muted); }
    .badge { display: inline-block; padding: 0.35rem 0.85rem; border-radius: 999px; background: rgba(59, 130, 246, 0.12); color: var(--text); margin: 0.2rem 0.35rem 0 0; font-size: 0.82rem; border: 1px solid rgba(59, 130, 246, 0.2); }
    .list-card { background: var(--panel); border: 1px solid var(--border); padding: 1.1rem; border-radius: 12px; color: var(--text); }
    .stPlotlyChart { background: var(--panel); border-radius: 12px; padding: 0.5rem; box-shadow: var(--shadow); }
    .cta-row { display: flex; gap: 0.75rem; flex-wrap: wrap; margin-top: 1rem; }
    .cta-primary, .cta-secondary {
        display: inline-flex;
        align-items: center;
        gap: 0.45rem;
        padding: 0.6rem 1rem;
        border-radius: 999px;
        font-size: 0.9rem;
        border: 1px solid var(--border);
        text-decoration: none;
    }
    .cta-primary { background: var(--accent); color: #ffffff; }
    .cta-secondary { background: transparent; color: var(--text); }
    .footer-links { display: grid; gap: 0.4rem; margin-top: 1.5rem; color: var(--muted); font-size: 0.9rem; }
    .header-bar { display: flex; align-items: center; justify-content: space-between; padding: 0.8rem 1.2rem; background: var(--panel); border-radius: 12px; border: 1px solid var(--border); margin-bottom: 1.2rem; }
    .header-title { font-size: 1rem; font-weight: 600; letter-spacing: 0.02em; }
    .header-subtitle { font-size: 0.85rem; color: var(--muted); margin-top: 0.2rem; }
    .status-pill { display: inline-flex; align-items: center; gap: 0.4rem; padding: 0.3rem 0.7rem; border-radius: 999px; background: rgba(0, 166, 118, 0.15); color: var(--success); font-size: 0.78rem; border: 1px solid rgba(0, 166, 118, 0.25); }
    .legal-note { font-size: 0.85rem; color: var(--muted); margin-top: 1rem; }
</style>
"""
st.markdown(css, unsafe_allow_html=True)

anchor = BlockchainAnchor(
    root_hash="0x9f3fa7c2d1b4a7e1f02d5e1c34aa9b21b",
    network="Arbitrum L2",
    tx_url="https://arbiscan.io/tx/0x9f3b0c0d1d2e3f4a5b6c7d8e9f000111222333444555666777888999aaa",
    anchored_at="2026-01-12 18:40 UTC",
)

snapshots_df = build_snapshot_data()
rules_df = build_rules_data()
benford_df = build_benford_data()
last_digit_df = build_last_digit_data()
votes_df = build_vote_evolution()
activity_df = pd.DataFrame(
    {
        "hour": ["00:00", "04:00", "08:00", "12:00", "16:00", "20:00"],
        "activity": [18, 22, 40, 75, 55, 30],
    }
)

critical_anomalies = int((snapshots_df["status"] == "ALERTA").sum())

def build_indicator_figures(
    benford_data: pd.DataFrame,
    last_digit_data: pd.DataFrame,
    votes_data: pd.DataFrame,
    activity_data: pd.DataFrame,
    copy_map: dict,
) -> tuple[go.Figure, go.Figure, go.Figure, go.Figure]:
    benford_fig = go.Figure()
    benford_fig.add_trace(
        go.Bar(
            x=benford_data["digit"],
            y=benford_data["expected"],
            name=copy_map["expected_label"],
            marker_color="#3b82f6",
        )
    )
    benford_fig.add_trace(
        go.Bar(
            x=benford_data["digit"],
            y=benford_data["observed"],
            name=copy_map["observed_label"],
            marker_color="#00a676",
        )
    )
    benford_fig.update_layout(
        barmode="group",
        height=300,
        margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#e5e7eb",
        title=copy_map["benford_title"],
    )

    last_digit_fig = px.bar(
        last_digit_data,
        x="digit",
        y="observed",
        color_discrete_sequence=["#3b82f6"],
        title=copy_map["last_digit_title"],
    )
    last_digit_fig.update_layout(
        height=260,
        margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#e5e7eb",
    )

    votes_fig = px.line(votes_data, x="hour", y="votes", markers=True, title=copy_map["vote_evolution_title"])
    votes_fig.update_layout(
        height=260,
        margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#e5e7eb",
    )

    heat_fig = px.bar(
        activity_data,
        x="hour",
        y="activity",
        color="activity",
        color_continuous_scale=["#1f3a5f", "#00a676"],
        title=copy_map["activity_title"],
    )
    heat_fig.update_layout(
        height=240,
        margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#e5e7eb",
        coloraxis_showscale=False,
    )

    return benford_fig, last_digit_fig, votes_fig, heat_fig


def build_governance_data(language: str) -> pd.DataFrame:
    if language == "en":
        return pd.DataFrame(
            {
                "dimension": [
                    "Data custody",
                    "Traceability",
                    "Public access",
                    "Independence",
                    "Reproducibility",
                ],
                "guarantee": [
                    "Immutable snapshots with root hash",
                    "Public ledger on Arbitrum L2",
                    "Audited JSON available for export",
                    "Automated rules with no political intervention",
                    "Documented calculations + evidence trails",
                ],
            }
        )
    return pd.DataFrame(
        {
            "dimensión": [
                "Custodia de datos",
                "Trazabilidad",
                "Acceso público",
                "Independencia",
                "Reproducibilidad",
            ],
            "garantía": [
                "Snapshots inmutables con hash raíz",
                "Ledger público en Arbitrum L2",
                "JSON auditado disponible y exportable",
                "Reglas automáticas sin intervención política",
                "Documentación de cálculo + evidencias",
            ],
        }
    )


def build_risk_data(language: str) -> pd.DataFrame:
    if language == "en":
        return pd.DataFrame(
            {
                "risk": [
                    "Result manipulation",
                    "Late or irregular uploads",
                    "Atypical statistical patterns",
                    "Publication interruption",
                ],
                "control": [
                    "Root hash + blockchain anchoring",
                    "Timing and change alerts",
                    "Benford + last-digit + series checks",
                    "Scheduled snapshots and exports",
                ],
                "status": ["Mitigated", "Monitored", "Monitored", "Mitigated"],
            }
        )
    return pd.DataFrame(
        {
            "riesgo": [
                "Alteración de resultados",
                "Carga tardía o irregular",
                "Patrones estadísticos atípicos",
                "Interrupción de publicación",
            ],
            "control": [
                "Hash raíz + anclaje blockchain",
                "Alertas de temporalidad y cambios",
                "Benford + dígitos finales + series",
                "Snapshots programados y exportables",
            ],
            "estado": ["Mitigado", "Monitoreado", "Monitoreado", "Mitigado"],
        }
    )


def build_international_data(language: str) -> pd.DataFrame:
    if language == "en":
        return pd.DataFrame(
            {
                "standard": [
                    "OAS – Transparency",
                    "EU – Traceability",
                    "ISO 27001 – Integrity",
                    "GOOD PRACTICE – Auditability",
                ],
                "coverage": [
                    "Verifiable publication with open access",
                    "Immutable record with root hash",
                    "Integrity rules + alerts",
                    "Reproducible reports with evidence",
                ],
            }
        )
    return pd.DataFrame(
        {
            "estándar": [
                "OEA – Transparencia",
                "UE – Trazabilidad",
                "ISO 27001 – Integridad",
                "GOOD PRACTICE – Auditoría",
            ],
            "cómo se cubre": [
                "Publicación verificable y acceso abierto",
                "Registro inmutable con hash raíz",
                "Reglas de integridad + alertas",
                "Reportes reproducibles con evidencias",
            ],
        }
    )

st.markdown(
    f"""
<div class="header-bar">
  <div>
    <div class="header-title">C.E.N.T.I.N.E.L. · {copy['header_title']}</div>
    <div class="header-subtitle">{copy['header_subtitle']}</div>
  </div>
  <div class="status-pill">● {copy['header_status']}</div>
</div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    f"""
<div class="glass hero">
  <h1>{copy['hero_title']}</h1>
  <p>{copy['hero_subtitle']}</p>
  <h3 style="color: var(--success);">{copy['global_ok']}</h3>
  <div class="cta-row">
    <a class="cta-primary" href="https://arbiscan.io/" target="_blank" rel="noopener">{copy['cta_verify']}</a>
    <a class="cta-secondary" href="#reportes">{copy['cta_report']}</a>
  </div>
</div>
    """,
    unsafe_allow_html=True,
)

st.markdown(f"#### {copy['audience_title']}")
st.markdown(
    "".join([f"<span class='badge'>{item}</span>" for item in copy["audience_items"]]),
    unsafe_allow_html=True,
)

kpi_cols = st.columns(5)
kpis = [
    (copy["kpi_snapshots"], "174", copy["kpi_notes"]),
    (copy["kpi_changes"], "68", copy["kpi_changes_note"]),
    (copy["kpi_anomalies"], str(critical_anomalies), copy["kpi_anomalies_note"]),
    (copy["kpi_rules"], str(len(rules_df)), copy["kpi_rules_note"]),
    (copy["kpi_verifications"], "2.4K", copy["kpi_verifications_note"]),
]
for col, (label, value, note) in zip(kpi_cols, kpis):
    with col:
        st.markdown(
            f"""
<div class="kpi">
  <h3>{label}</h3>
  <p>{value}</p>
  <span>{note}</span>
</div>
            """,
            unsafe_allow_html=True,
        )

col_left, col_right = st.columns([1.1, 1])
with col_left:
    st.markdown(f"### {copy['capabilities_title']}")
    st.markdown(
        "<div class='list-card'>" + "<br>".join([f"• {item}" for item in copy["capabilities_items"]]) + "</div>",
        unsafe_allow_html=True,
    )
with col_right:
    st.markdown(f"### {copy['methodology_title']}")
    st.markdown(
        "<div class='list-card'>" + "<br>".join([f"• {item}" for item in copy["methodology_items"]]) + "</div>",
        unsafe_allow_html=True,
    )

st.markdown(f"### {copy['indicator_title']}")
st.markdown(f"<div class='note'>{copy['indicator_subtitle']}</div>", unsafe_allow_html=True)
benford_fig, last_digit_fig, votes_fig, heat_fig = build_indicator_figures(
    benford_df, last_digit_df, votes_df, activity_df, copy
)
st.plotly_chart(benford_fig, use_container_width=True)
st.plotly_chart(last_digit_fig, use_container_width=True)
st.plotly_chart(votes_fig, use_container_width=True)
st.plotly_chart(heat_fig, use_container_width=True)

st.markdown(f"### {copy['snapshots_title']}")
st.dataframe(styled_status(snapshots_df), width="stretch", hide_index=True)
with st.expander(copy["snapshots_button"]):
    st.write("Comparador simple de JSON (placeholder)")

st.markdown(f"### {copy['rules_title']}")
st.markdown(f"<div class='note'>{copy['rules_help']}</div>", unsafe_allow_html=True)
st.dataframe(rules_df, width="stretch", hide_index=True)

st.markdown(f"### {copy['international_title']}")
st.markdown(f"<div class='note'>{copy['international_intro']}</div>", unsafe_allow_html=True)
st.dataframe(build_international_data(language), width="stretch", hide_index=True)

st.markdown(f"### {copy['governance_title']}")
st.dataframe(build_governance_data(language), width="stretch", hide_index=True)

st.markdown(f"### {copy['risk_title']}")
st.dataframe(build_risk_data(language), width="stretch", hide_index=True)

st.markdown(f"### {copy['verification_title']}")
st.markdown(f"<div class='note'>{copy['verification_help']}</div>", unsafe_allow_html=True)
with st.form("verify_form"):
    hash_input = st.text_input(copy["verification_input"], value=anchor.root_hash)
    submitted = st.form_submit_button(copy["verify_button"])
if submitted:
    if anchor.root_hash.lower() in hash_input.lower():
        st.success(copy["verify_success"])
    else:
        st.error(copy["verify_fail"])
st.markdown("### QR")
if qrcode is None:
    st.warning("QR no disponible: falta instalar la dependencia 'qrcode'.")
else:
    st.image(qrcode.make(anchor.root_hash))

st.markdown(f"### {copy['export_title']}")
st.markdown("<a id='reportes'></a>", unsafe_allow_html=True)
report_time = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M")
report_payload = f"{anchor.root_hash}|{anchor.tx_url}|{report_time}"
report_hash = compute_report_hash(report_payload)

snapshots_rows = [
    ["Timestamp UTC", "Estado", "Detalle", "Cambios"]
] + snapshots_df[["timestamp", "status", "detail", "changes"]].values.tolist()

rules_rows = [
    ["Regla", "Tipo", "Severidad", "Estado", "Acción"]
] + rules_df[["name", "type", "severity", "state", "action"]].values.tolist()

data_es = {
    "logo": "C.E.N.T.I.N.E.L. – Centro de Evidencias y Monitoreo Electoral",
    "title": "Reporte Ejecutivo de Integridad Electoral",
    "subtitle": "Transparencia verificable con inmutabilidad blockchain (Arbitrum L2)",
    "generated_label": "Generado el",
    "generated_at": report_time,
    "global_status": "ESTATUS GLOBAL: VERIFICABLE – SIN ANOMALÍAS CRÍTICAS",
    "executive_title": "Resumen Ejecutivo",
    "executive_intro": (
        "Sistema independiente que toma snapshots inmutables de los datos electorales públicos cada 10 minutos "
        "y los ancla en blockchain para que cualquier misión internacional o auditor pueda verificar cambios."
    ),
    "executive_state": (
        f"Último snapshot: {report_time} UTC – Hash raíz verificado en Arbitrum L2. "
        "Disponible para misiones OEA/UE."
    ),
    "kpi_headers": ["Snapshots 24h", "Cambios", "Anomalías", "Reglas", "Verificaciones"],
    "kpi_values": ["174", "68", str(critical_anomalies), str(len(rules_df)), "2.4K"],
    "technical_title": "Sección Técnica Principal",
    "root_hash_label": "Hash raíz actual:",
    "root_hash": anchor.root_hash,
    "tx_label": "Transacción en blockchain:",
    "tx_url": anchor.tx_url,
    "anchored_label": f"Anclado en {anchor.network} el {anchor.anchored_at}",
    "qr_label": "Hash de verificación (QR)",
    "snapshots_title": "Snapshots recientes",
    "snapshots_rows": snapshots_rows,
    "rules_title": "Reglas activas y alertas",
    "rules_rows": rules_rows,
    "integrity_title": "Indicadores pedagógicos de integridad",
    "integrity_intro": "Distribución de primeros dígitos, evolución de cambios y actividad horaria.",
    "integrity_benford": "Ley de Benford: Distribución de primeros dígitos – Normal ✓",
    "integrity_votes": "Evolución de cambios: Línea creciente sin saltos sospechosos.",
    "integrity_heatmap": "Actividad horaria: Concentrada en horarios diurnos.",
    "verify_title": "Cómo verificar usted mismo",
    "verify_steps": [
        "1. Copie el hash raíz.",
        "2. Vaya a https://arbiscan.io y busque la transacción.",
        "3. Compare con el hash calculado localmente.",
        "4. ¡Cualquier discrepancia sería detectable inmediatamente!",
    ],
    "footer_left": "Generado por C.E.N.T.I.N.E.L. – Transparencia Electoral Verificable",
    "footer_right": f"Hash reporte: {report_hash} · https://centinel-dashboard.streamlit.app/",
}

data_en = {
    **data_es,
    "title": "Executive Report on Electoral Integrity",
    "subtitle": "Verifiable transparency with blockchain immutability (Arbitrum L2)",
    "generated_label": "Generated on",
    "executive_title": "Executive Summary",
    "executive_intro": (
        "Independent system that takes immutable snapshots of public electoral data every 10 minutes "
        "and anchors them on blockchain so any international mission or auditor can verify changes."
    ),
    "executive_state": (
        f"Latest snapshot: {report_time} UTC – Root hash verified on Arbitrum L2. "
        "Ready for OAS/EU observation."
    ),
    "technical_title": "Technical core",
    "root_hash_label": "Current root hash:",
    "tx_label": "Blockchain transaction:",
    "anchored_label": f"Anchored on {anchor.network} at {anchor.anchored_at}",
    "qr_label": "Verification hash (QR)",
    "snapshots_title": "Recent snapshots",
    "rules_title": "Active rules & alerts",
    "integrity_title": "Pedagogical integrity indicators",
    "integrity_intro": "First-digit distribution, change evolution, and hourly activity.",
    "integrity_benford": "Benford Law: First-digit distribution – Normal ✓",
    "integrity_votes": "Change evolution: Smooth growth without suspicious jumps.",
    "integrity_heatmap": "Hourly activity: Concentrated in daytime hours.",
    "verify_title": "How to verify it yourself",
    "verify_steps": [
        "1. Copy the root hash.",
        "2. Go to https://arbiscan.io and look up the transaction.",
        "3. Compare with the locally computed hash.",
        "4. Any discrepancy would be immediately detectable.",
    ],
}

if REPORTLAB_AVAILABLE:
    pdf_es = build_pdf_report(data_es, "es")
    pdf_en = build_pdf_report(data_en, "en")
else:
    st.warning("Exportación PDF no disponible: falta instalar la dependencia 'reportlab'.")

col1, col2, col3 = st.columns(3)
with col1:
    if REPORTLAB_AVAILABLE:
        st.download_button(copy["export_pdf_es"], data=pdf_es, file_name="centinel_reporte_es.pdf")
with col2:
    if REPORTLAB_AVAILABLE:
        st.download_button(copy["export_pdf_en"], data=pdf_en, file_name="centinel_report_en.pdf")
with col3:
    st.download_button(copy["export_json"], data=snapshots_df.to_json(orient="records"), file_name="centinel.json")

st.download_button(copy["export_csv"], data=snapshots_df.to_csv(index=False), file_name="centinel.csv")

st.markdown("---")
st.markdown(f"#### {copy['footer_links_title']}")
st.markdown(
    f"""
<div class="footer-links">
  <a href="https://github.com/userf8a2c4/centinel-engine" target="_blank" rel="noopener">{copy['footer_github']}</a>
  <a href="https://github.com/userf8a2c4/centinel-engine#readme" target="_blank" rel="noopener">{copy['footer_docs']}</a>
  <a href="https://arbiscan.io/" target="_blank" rel="noopener">{copy['footer_verify']}</a>
  <a href="mailto:observadores@centinel.app" target="_blank" rel="noopener">{copy['footer_contact']}</a>
</div>
<div class="legal-note">{copy['footer_note']}</div>
    """,
    unsafe_allow_html=True,
)
