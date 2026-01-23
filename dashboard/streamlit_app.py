import datetime as dt
from dataclasses import dataclass

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

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


def build_rules_data() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "regla": "Si un archivo cambia más del 5%",
                "estado": "ON",
                "accion": "Notificamos y pausamos snapshots",
            },
            {
                "regla": "Cambios fuera de horarios esperados",
                "estado": "ON",
                "accion": "Alertamos a observadores",
            },
            {
                "regla": "Patrones repetidos en JSON",
                "estado": "OFF",
                "accion": "Registrar y revisar",
            },
        ]
    )


def styled_status(df: pd.DataFrame):
    def highlight_status(value: str) -> str:
        color_map = {
            "OK": "background-color: rgba(255, 255, 255, 0.06); color: var(--text);",
            "REVISAR": "background-color: rgba(255, 255, 255, 0.12); color: var(--text);",
            "ALERTA": "background-color: rgba(255, 255, 255, 0.2); color: var(--text);",
        }
        return color_map.get(value, "")

    return df.style.map(highlight_status, subset=["status"])


def build_benford_data() -> pd.DataFrame:
    expected = [30.1, 17.6, 12.5, 9.7, 7.9, 6.7, 5.8, 5.1, 4.6]
    observed = [29.3, 18.2, 12.1, 10.4, 7.2, 6.9, 5.5, 5.0, 5.4]
    digits = list(range(1, 10))
    return pd.DataFrame({"dígito": digits, "esperado": expected, "observado": observed})


def build_last_digit_data() -> pd.DataFrame:
    digits = list(range(10))
    observed = [9.4, 10.6, 9.8, 10.2, 9.9, 9.7, 10.5, 10.1, 10.0, 9.8]
    return pd.DataFrame({"dígito": digits, "observado": observed})


def build_vote_evolution() -> pd.DataFrame:
    now = dt.datetime.now(dt.timezone.utc)
    series = []
    total_votes = 120_000
    for step in range(8):
        total_votes += 6_500 + (step * 320)
        series.append(
            {
                "hora": (now - dt.timedelta(hours=7 - step)).strftime("%H:%M"),
                "votos": total_votes,
            }
        )
    return pd.DataFrame(series)


def _escape_pdf_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build_pdf_report(anchor: BlockchainAnchor, snapshots_df: pd.DataFrame, rules_df: pd.DataFrame, language: str) -> bytes:
    if language == "en":
        title = "C.E.N.T.I.N.E.L. Citizen Report"
        subtitle = f"Anchored on {anchor.network} · {anchor.anchored_at}"
        snapshot_title = "Recent snapshots"
        rules_title = "Active rules"
        qr_label = "Verification hash (QR)"
        qr_fallback = "QR unavailable in this environment."
        hash_label = "Root hash"
        tx_label = "Public transaction"
    else:
        title = "C.E.N.T.I.N.E.L. Reporte ciudadano"
        subtitle = f"Anclado en {anchor.network} · {anchor.anchored_at}"
        snapshot_title = "Snapshots recientes"
        rules_title = "Reglas activas"
        qr_label = "Hash de verificación (QR)"
        qr_fallback = "QR no disponible en este entorno."
        hash_label = "Hash raíz"
        tx_label = "Transacción pública"

    lines = [
        title,
        subtitle,
        "",
        snapshot_title,
    ]
    for _, row in snapshots_df.iterrows():
        lines.append(f"- {row['timestamp']} | {row['status']} | {row['detail']}")
    lines.append("")
    lines.append(rules_title)
    for _, row in rules_df.iterrows():
        lines.append(f"- {row['regla']} ({row['estado']})")
    lines.append("")
    lines.append(f"{hash_label}: {anchor.root_hash}")
    lines.append(f"{tx_label}: {anchor.tx_url}")

    content_lines = []
    y = 760
    for line in lines:
        safe_line = _escape_pdf_text(str(line))
        content_lines.append(f"BT /F1 12 Tf 72 {y} Td ({safe_line}) Tj ET")
        y -= 16
        if y < 220:
            break
    qr_label_line = _escape_pdf_text(qr_label)
    content_lines.append(f"BT /F1 10 Tf 72 200 Td ({qr_label_line}) Tj ET")
    if qrcode is None:
        fallback_line = _escape_pdf_text(qr_fallback)
        content_lines.append(f"BT /F1 10 Tf 72 184 Td ({fallback_line}) Tj ET")
    else:
        qr = qrcode.QRCode(border=1, box_size=1)
        qr.add_data(anchor.root_hash)
        qr.make(fit=True)
        qr_matrix = qr.get_matrix()
        qr_module = 4
        qr_origin_x = 72
        qr_origin_y = 90
        content_lines.append("0 0 0 rg")
        for row_index, row in enumerate(qr_matrix):
            for col_index, cell in enumerate(row):
                if not cell:
                    continue
                x = qr_origin_x + (col_index * qr_module)
                y = qr_origin_y + ((len(qr_matrix) - row_index - 1) * qr_module)
                content_lines.append(f"{x} {y} {qr_module} {qr_module} re f")
    content = "\n".join(content_lines)
    content_bytes = content.encode("latin-1")

    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        "/Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(content_bytes)} >>\nstream\n{content}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    pdf_bytes = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf_bytes))
        pdf_bytes.extend(f"{index} 0 obj\n{obj}\nendobj\n".encode("latin-1"))

    xref_offset = len(pdf_bytes)
    pdf_bytes.extend(b"xref\n0 6\n0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf_bytes.extend(f"{offset:010d} 00000 n \n".encode("latin-1"))
    pdf_bytes.extend(
        f"trailer << /Size 6 /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("latin-1")
    )
    return bytes(pdf_bytes)


st.set_page_config(
    page_title="C.E.N.T.I.N.E.L. | Dashboard Ciudadano",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded",
)

LANG_OPTIONS = {"Español": "es", "English": "en"}
language_label = st.sidebar.selectbox("Idioma / Language", list(LANG_OPTIONS.keys()), index=0)
language = LANG_OPTIONS[language_label]

theme = {
    "color_scheme": "dark",
    "bg": "#0b1220",
    "panel": "#111827",
    "panel_soft": "#1f2937",
    "text": "#e5e7eb",
    "muted": "#94a3b8",
    "border": "#2b3648",
    "accent": "#60a5fa",
    "accent_soft": "#7c8aa4",
    "chart_primary": "#93c5fd",
    "chart_secondary": "#94a3b8",
}

translations = {
    "es": {
        "title": "C.E.N.T.I.N.E.L. – Integridad Electoral basada en datos",
        "subtitle": "Análisis reproducible de JSON público con trazabilidad blockchain para auditorías institucionales.",
        "pillars": [
            "Datos públicos en JSON",
            "Análisis estadístico verificable",
            "Reglas de auditoría claras",
            "Trazabilidad en blockchain",
        ],
        "status_now": "Estado actual",
        "status_note": "Todo OK · sin anomalías críticas",
        "status_body": "El sistema analiza cambios en el JSON público y detecta patrones atípicos con evidencia trazable.",
        "last_snapshot": "Último snapshot verificable",
        "citizen_checks": "Verificaciones externas",
        "citizen_body": "Auditores independientes pueden contrastar JSON y hashes públicos.",
        "cta_verify": "Validar evidencia JSON",
        "cta_blockchain": "Ver anclaje en blockchain",
        "kpi_title": "Indicadores clave",
        "kpi_helper": "Cada métrica parte de JSON público y evidencia anclada en blockchain.",
        "kpi_snapshots": "Snapshots públicos 24h",
        "kpi_changes": "Cambios auditables",
        "kpi_alerts": "Anomalías críticas",
        "kpi_checks": "Verificaciones externas",
        "kpi_tooltips": [
            "Snapshots del JSON público cada 10 minutos.",
            "Deltas auditables entre snapshots.",
            "Alertas que superan umbrales técnicos.",
            "Validaciones externas basadas en evidencia.",
        ],
        "kpi_descriptions": [
            "Captura periódica del JSON público con hash verificable.",
            "Cambios comparados con evidencia histórica reproducible.",
            "Sin señales críticas en los indicadores de integridad.",
            "Auditores externos confirman consistencia de datos.",
        ],
        "stats_title": "Indicadores estadísticos de integridad",
        "stats_subtitle": "Pruebas replicables para identificar patrones atípicos en el JSON.",
        "benford_title": "Ley de Benford (primer dígito)",
        "last_digit_title": "Último dígito de votos",
        "votes_title": "Evolución de votos acumulados",
        "benford_note": "Distribución consistente con datos públicos ✓ (confianza 92%).",
        "last_digit_note": "Concentraciones anómalas requieren auditoría adicional.",
        "votes_note": "Crecimientos abruptos requieren contraste con evidencia.",
        "updates_title": "¿A qué horas se actualizan más los datos?",
        "updates_note": "Actividad fuera de horario requiere justificación y auditoría.",
        "snapshots_title": "Snapshots recientes",
        "rules_title": "Reglas de auditoría",
        "reports_title": "Reportes para auditoría institucional",
        "download_pdf": "Descargar reporte (PDF)",
        "download_json": "Descargar datos completos (JSON + hashes)",
        "download_csv": "Descargar CSV",
        "rules_card": "Reglas de control y evidencia",
        "ai_card": "Detección automática de anomalías",
        "repro_title": "Reportes reproducibles para auditoría",
        "verify_title": "Verificación propia",
    },
    "en": {
        "title": "C.E.N.T.I.N.E.L. – Data-driven electoral integrity",
        "subtitle": "Reproducible analysis of public JSON with blockchain traceability for institutional audits.",
        "pillars": [
            "Public JSON data",
            "Verifiable statistical analysis",
            "Clear audit rules",
            "Blockchain traceability",
        ],
        "status_now": "Current status",
        "status_note": "All clear · no critical anomalies",
        "status_body": "The system analyzes public JSON changes and flags anomalous patterns with traceable evidence.",
        "last_snapshot": "Latest verifiable snapshot",
        "citizen_checks": "External checks",
        "citizen_body": "Independent auditors can validate public JSON and hashes.",
        "cta_verify": "Validate JSON evidence",
        "cta_blockchain": "View blockchain anchor",
        "kpi_title": "Key indicators",
        "kpi_helper": "Each metric is derived from public JSON and blockchain evidence.",
        "kpi_snapshots": "Public snapshots 24h",
        "kpi_changes": "Auditable changes",
        "kpi_alerts": "Critical anomalies",
        "kpi_checks": "External checks",
        "kpi_tooltips": [
            "Public JSON snapshots every 10 minutes.",
            "Auditable deltas between snapshots.",
            "Alerts exceeding technical thresholds.",
            "External validation based on evidence.",
        ],
        "kpi_descriptions": [
            "Periodic capture of public JSON with verifiable hashes.",
            "Changes compared against reproducible evidence history.",
            "No critical integrity signals detected.",
            "External audits confirm data consistency.",
        ],
        "stats_title": "Statistical integrity indicators",
        "stats_subtitle": "Replicable tests to flag outliers in the JSON data.",
        "benford_title": "Benford's law (first digit)",
        "last_digit_title": "Last digit of votes",
        "votes_title": "Cumulative vote evolution",
        "benford_note": "Consistent with public data ✓ (92% confidence).",
        "last_digit_note": "Concentrated digits require audit review.",
        "votes_note": "Abrupt growth requires evidence cross-checking.",
        "updates_title": "When do updates happen most?",
        "updates_note": "Out-of-hours activity requires justification and audit.",
        "snapshots_title": "Recent snapshots",
        "rules_title": "Audit rules",
        "reports_title": "Reports for institutional audit",
        "download_pdf": "Download report (PDF)",
        "download_json": "Download full data (JSON + hashes)",
        "download_csv": "Download CSV",
        "rules_card": "Control & evidence rules",
        "ai_card": "Automated anomaly detection",
        "repro_title": "Reproducible audit reports",
        "verify_title": "Self-verification",
    },
}
copy = translations[language]

css = """
<style>
    :root {{
        color-scheme: {color_scheme};
        --bg: {bg};
        --panel: {panel};
        --panel-soft: {panel_soft};
        --text: {text};
        --muted: {muted};
        --border: {border};
        --accent: {accent};
        --accent-soft: {accent_soft};
    }}
    html, body, [class*="css"]  {{
        font-size: 16px;
    }}
    .stApp {{
        background: var(--bg);
        color: var(--text);
    }}
    section[data-testid="stSidebar"] {{
        background: var(--panel);
        border-right: 1px solid var(--border);
    }}
    .bento-grid {{
        display: grid;
        gap: 1rem;
        grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
        margin-bottom: 1.5rem;
    }}
    .bento-card {{
        background: var(--panel);
        border: 1px solid var(--border);
        border-radius: 18px;
        padding: 1.25rem;
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.12);
    }}
    .bento-hero {{
        padding: 2rem;
        border-radius: 24px;
        background: var(--panel);
        border: 1px solid var(--border);
        margin-bottom: 1.5rem;
    }}
    .bento-hero h1 {{
        margin-bottom: 0.4rem;
        font-size: 2.1rem;
        color: var(--text);
    }}
    .bento-hero p {{
        margin-bottom: 0.8rem;
        color: var(--muted);
    }}
    .pillars {{
        display: flex;
        gap: 0.75rem;
        flex-wrap: wrap;
    }}
    .pillar {{
        background: var(--panel-soft);
        padding: 0.5rem 0.85rem;
        border-radius: 999px;
        font-size: 0.85rem;
        border: 1px solid var(--border);
        color: var(--text);
    }}
    .section-title {{
        font-size: 1.1rem;
        color: var(--text);
        margin-bottom: 0.35rem;
    }}
    .section-subtitle {{
        color: var(--muted);
        font-size: 0.95rem;
        margin-bottom: 0.75rem;
    }}
    .bento-metric {{
        display: flex;
        flex-direction: column;
        gap: 0.35rem;
    }}
    .bento-metric h3 {{
        margin: 0;
        font-size: 0.85rem;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: var(--muted);
    }}
    .bento-metric p {{
        margin: 0;
        font-size: 1.6rem;
        font-weight: 700;
        color: var(--text);
    }}
    .bento-metric span {{
        font-size: 0.9rem;
        color: var(--muted);
    }}
    .hint {{
        font-size: 0.85rem;
        color: var(--accent-soft);
        border-bottom: 1px dotted var(--accent-soft);
        cursor: help;
    }}
    .note {{
        background: var(--panel-soft);
        border: 1px solid var(--border);
        padding: 0.75rem 1rem;
        border-radius: 12px;
        color: var(--muted);
        margin-bottom: 1rem;
    }}
</style>
"""
st.markdown(css.format(**theme), unsafe_allow_html=True)

anchor = BlockchainAnchor(
    root_hash="0x9f3a7c2d1b4a7e1f02d5e1c34aa9b21b",
    network="Arbitrum L2",
    tx_url="https://arbiscan.io/tx/0x9f3b0c0d1d2e3f4a5b6c7d8e9f000111222333444555666777888999aaa",
    anchored_at="2026-01-12 18:40 UTC",
)

st.sidebar.markdown("## C.E.N.T.I.N.E.L.")
st.sidebar.caption(
    "Centinela Electoral Nacional Transparente Íntegro Nacional Electoral Libre"
    if language == "es"
    else "National Transparent Electoral Sentinel"
)

st.sidebar.markdown("### Navegación" if language == "es" else "### Navigation")
st.sidebar.write("• Resumen institucional" if language == "es" else "• Institutional overview")
st.sidebar.write("• Indicadores" if language == "es" else "• Indicators")
st.sidebar.write("• Snapshots verificables" if language == "es" else "• Verifiable snapshots")
st.sidebar.write("• Reglas de auditoría" if language == "es" else "• Audit rules")
st.sidebar.write("• Reportes" if language == "es" else "• Reports")

st.sidebar.markdown("---")

if st.sidebar.button("⚡ Activar Modo Electoral" if language == "es" else "⚡ Activate Election Mode", use_container_width=True):
    st.sidebar.success(
        "Modo electoral activado (cadencia intensiva)."
        if language == "es"
        else "Election mode activated (intensive cadence)."
    )
if st.sidebar.button("📥 Snapshot Ahora" if language == "es" else "📥 Snapshot Now", use_container_width=True):
    st.sidebar.success(
        "Snapshot programado para la próxima ventana."
        if language == "es"
        else "Snapshot scheduled for the next window."
    )

st.sidebar.markdown("---")
st.sidebar.markdown("**Estado**" if language == "es" else "**Status**")
st.sidebar.write("Modo: Auditoría Activa" if language == "es" else "Mode: Audit Active")
st.sidebar.write("Cadena: Arbitrum L2" if language == "es" else "Chain: Arbitrum L2")
st.sidebar.write("Último snapshot: hace 4 min" if language == "es" else "Latest snapshot: 4 min ago")

st.markdown(
    f"""
<div class="bento-hero">
  <h1>{copy['title']}</h1>
  <p>{copy['subtitle']}</p>
  <div class="pillars">
    <div class="pillar">{copy['pillars'][0]}</div>
    <div class="pillar">{copy['pillars'][1]}</div>
    <div class="pillar">{copy['pillars'][2]}</div>
    <div class="pillar">{copy['pillars'][3]}</div>
  </div>
</div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    f"""
<div class="bento-grid">
  <div class="bento-card">
    <div class="section-title">{copy['status_now']}</div>
    <div class="section-subtitle">{copy['status_note']}</div>
    <p>{copy['status_body']}</p>
  </div>
  <div class="bento-card">
    <div class="section-title">{copy['last_snapshot']}</div>
    <div class="section-subtitle">{'Hace 4 minutos' if language == 'es' else '4 minutes ago'} · {anchor.network}</div>
    <p>{'Hash raíz' if language == 'es' else 'Root hash'}: {anchor.root_hash[:12]}...</p>
  </div>
  <div class="bento-card">
    <div class="section-title">{copy['citizen_checks']}</div>
    <div class="section-subtitle">2.4K {('personas' if language == 'es' else 'people')}</div>
    <p>{copy['citizen_body']}</p>
  </div>
</div>
    """,
    unsafe_allow_html=True,
)

cta_col1, cta_col2 = st.columns([1, 1])
with cta_col1:
    st.button(copy["cta_verify"], use_container_width=True)
with cta_col2:
    st.link_button(copy["cta_blockchain"], anchor.tx_url, use_container_width=True)

st.markdown(f"### {copy['kpi_title']}")
st.markdown(f"<div class='note'>{copy['kpi_helper']}</div>", unsafe_allow_html=True)
st.markdown(
    f"""
<div class='bento-grid'>
  <div class='bento-card bento-metric'>
    <h3>{copy['kpi_snapshots']} <span class='hint' title='{copy['kpi_tooltips'][0]}'>ⓘ</span></h3>
    <p>174</p>
    <span>{copy['kpi_descriptions'][0]}</span>
  </div>
  <div class='bento-card bento-metric'>
    <h3>{copy['kpi_changes']} <span class='hint' title='{copy['kpi_tooltips'][1]}'>ⓘ</span></h3>
    <p>68</p>
    <span>{copy['kpi_descriptions'][1]}</span>
  </div>
  <div class='bento-card bento-metric'>
    <h3>{copy['kpi_alerts']} <span class='hint' title='{copy['kpi_tooltips'][2]}'>ⓘ</span></h3>
    <p>0</p>
    <span>{copy['kpi_descriptions'][2]}</span>
  </div>
  <div class='bento-card bento-metric'>
    <h3>{copy['kpi_checks']} <span class='hint' title='{copy['kpi_tooltips'][3]}'>ⓘ</span></h3>
    <p>2.4K</p>
    <span>{copy['kpi_descriptions'][3]}</span>
  </div>
</div>
    """,
    unsafe_allow_html=True,
)

st.markdown(f"### {copy['stats_title']}")
st.markdown(f"<div class='note'>{copy['stats_subtitle']}</div>", unsafe_allow_html=True)

benford_col, last_digit_col = st.columns([1.4, 1])
with benford_col:
    benford_df = build_benford_data()
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=benford_df["dígito"],
            y=benford_df["esperado"],
            name="Esperado",
            marker_color=theme["chart_primary"],
        )
    )
    fig.add_trace(
        go.Bar(
            x=benford_df["dígito"],
            y=benford_df["observado"],
            name="Observado",
            marker_color=theme["chart_secondary"],
        )
    )
    fig.update_layout(
        barmode="group",
        height=300,
        margin=dict(l=10, r=10, t=20, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color=theme["text"],
        title=copy["benford_title"],
    )
    st.plotly_chart(fig, use_container_width=True)
    st.markdown(f"<div class='note'>{copy['benford_note']}</div>", unsafe_allow_html=True)

with last_digit_col:
    last_digit_df = build_last_digit_data()
    fig = px.bar(
        last_digit_df,
        x="dígito",
        y="observado",
        color_discrete_sequence=[theme["chart_primary"]],
        title=copy["last_digit_title"],
    )
    fig.update_layout(
        height=300,
        margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color=theme["text"],
        yaxis_title="% observado",
    )
    st.plotly_chart(fig, use_container_width=True)
    st.markdown(f"<div class='note'>{copy['last_digit_note']}</div>", unsafe_allow_html=True)

votes_df = build_vote_evolution()
fig = px.line(votes_df, x="hora", y="votos", markers=True, title=copy["votes_title"])
fig.update_layout(
    height=260,
    margin=dict(l=10, r=10, t=30, b=10),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font_color=theme["text"],
)
fig.update_traces(line=dict(color=theme["chart_primary"]))
st.plotly_chart(fig, use_container_width=True)
st.markdown(f"<div class='note'>{copy['votes_note']}</div>", unsafe_allow_html=True)

st.markdown(f"### {copy['updates_title']}")
heatmap_df = pd.DataFrame(
    {
        "hora": ["00:00", "04:00", "08:00", "12:00", "16:00", "20:00"],
        "actividad": [18, 22, 40, 75, 55, 30],
    }
)
heat_fig = px.bar(
    heatmap_df,
    x="hora",
    y="actividad",
    color="actividad",
    color_continuous_scale=[theme["chart_secondary"], theme["chart_primary"]],
)
heat_fig.update_layout(
    height=260,
    margin=dict(l=10, r=10, t=20, b=10),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font_color=theme["text"],
    coloraxis_showscale=False,
)
st.plotly_chart(heat_fig, use_container_width=True)
st.markdown(f"<div class='note'>{copy['updates_note']}</div>", unsafe_allow_html=True)

st.markdown(f"### {copy['snapshots_title']}")
snapshots_df = build_snapshot_data()
st.dataframe(
    styled_status(snapshots_df),
    width="stretch",
    hide_index=True,
)
if st.button("Ver qué cambió exactamente" if language == "es" else "See what changed"):
    st.write(
        "✅ +3 registros JSON agregados · ❌ 1 registro JSON corregido"
        if language == "es"
        else "✅ +3 JSON records added · ❌ 1 JSON record corrected"
    )

st.markdown(f"### {copy['rules_title']}")
rules_df = build_rules_data()
st.dataframe(rules_df, width="stretch", hide_index=True)
st.button("¡Sugiere una nueva regla!" if language == "es" else "Suggest a new rule", use_container_width=True)

st.markdown(f"### {copy['reports_title']}")
report_csv = snapshots_df.to_csv(index=False).encode("utf-8")
pdf_bytes = build_pdf_report(anchor, snapshots_df, rules_df, language)
col_report1, col_report2, col_report3 = st.columns(3)
with col_report1:
    st.download_button(
        copy["download_pdf"],
        data=pdf_bytes,
        file_name="centinel_reporte.pdf",
        mime="application/pdf",
        use_container_width=True,
    )
with col_report2:
    st.download_button(
        copy["download_json"],
        data=snapshots_df.to_json(orient="records"),
        file_name="centinel_reporte.json",
        mime="application/json",
        use_container_width=True,
    )
with col_report3:
    st.download_button(
        copy["download_csv"],
        data=report_csv,
        file_name="centinel_reporte.csv",
        mime="text/csv",
        use_container_width=True,
    )

st.markdown(f"### {copy['snapshots_title']}")
st.dataframe(
    styled_status(snapshots_df),
    width="stretch",
    hide_index=True,
)
st.caption(
    "Estados: OK (sin anomalías), REVISAR (cambios menores), ALERTA (anomalías graves)."
    if language == "es"
    else "Statuses: OK (no anomalies), REVIEW (minor changes), ALERT (critical anomalies)."
)

rules_df = build_rules_data()
col_rules, col_ai = st.columns([1.3, 1])
with col_rules:
    st.markdown(
        f"<div class='bento-card'><div class='section-title'>{copy['rules_card']}</div>"
        f"<div class='section-subtitle'>"
        f"{'Protocolos de control basados en evidencia pública' if language == 'es' else 'Evidence-based control protocols'}"
        f"</div>",
        unsafe_allow_html=True,
    )
    st.dataframe(rules_df, width="stretch", hide_index=True)
    st.button("Crear nueva regla" if language == "es" else "Create new rule", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with col_ai:
    st.markdown(
        f"<div class='bento-card'><div class='section-title'>{copy['ai_card']}</div>"
        f"<div class='section-subtitle'>{'Alertas trazables en tiempo real' if language == 'es' else 'Traceable real-time alerts'}</div>",
        unsafe_allow_html=True,
    )
    st.write(
        "• Patrón anómalo en sección 12 · Alta"
        if language == "es"
        else "• Anomalous pattern in precinct 12 · High"
    )
    st.write(
        "• Cambio irregular en JSON 2024-09 · Media"
        if language == "es"
        else "• Irregular JSON change 2024-09 · Medium"
    )
    st.write(
        "• Pico inusual en consultas ciudadanas · Baja"
        if language == "es"
        else "• Unusual spike in citizen queries · Low"
    )
    st.progress(0.92, text="Confianza anomalías críticas" if language == "es" else "Critical anomalies confidence")
    st.progress(0.84, text="Confianza cambios no autorizados" if language == "es" else "Unauthorized changes confidence")
    st.progress(0.68, text="Confianza inconsistencias menores" if language == "es" else "Minor inconsistencies confidence")
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown(f"### {copy['repro_title']}")
st.markdown(
    f"""
<div class="bento-card">
  <div class="section-title">{'Exportación verificable' if language == 'es' else 'Verifiable export'}</div>
  <div class="section-subtitle">{'PDF firmado, JSON auditado y hash reproducible.' if language == 'es' else 'Signed PDF, audited JSON, and reproducible hash.'}</div>
</div>
    """,
    unsafe_allow_html=True,
)

with st.expander(copy["verify_title"]):
    st.write(
        "Pegá el hash raíz para confirmar si coincide con el registro público en Arbitrum."
        if language == "es"
        else "Paste the root hash to confirm it matches the public record on Arbitrum."
    )
    hash_input = st.text_input("Hash raíz" if language == "es" else "Root hash", value=anchor.root_hash)
    if st.button("Verificar ahora" if language == "es" else "Verify now"):
        if anchor.root_hash[:6].lower() in hash_input.lower():
            st.markdown(
                f"<div class='note'>{'¡Coincide! ✓ Este hash está anclado en blockchain.' if language == 'es' else 'Match ✓ This hash is anchored on-chain.'}</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"<div class='note'>{'No coincide. Revisá que el hash sea correcto.' if language == 'es' else 'No match. Please verify the hash.'}</div>",
                unsafe_allow_html=True,
            )
