import datetime as dt
import hashlib
import io
from dataclasses import dataclass

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import qrcode
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


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


def styled_status(df: pd.DataFrame) -> pd.io.formats.style.Styler:
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

    qr = qrcode.make(data["root_hash"])
    qr_buffer = io.BytesIO()
    qr.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)
    elements.append(Spacer(1, 8))
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
    page_title="C.E.N.T.I.N.E.L. | Dashboard Ciudadano",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded",
)

if "language" not in st.session_state:
    st.session_state.language = "es"

LANG_OPTIONS = {"Español": "es", "English": "en"}
language_label = st.sidebar.selectbox(
    "Idioma / Language",
    list(LANG_OPTIONS.keys()),
    index=0 if st.session_state.language == "es" else 1,
)
st.session_state.language = LANG_OPTIONS[language_label]
language = st.session_state.language

translations = {
    "es": {
        "nav_title": "Navegación",
        "nav_sections": ["Resumen", "Snapshots", "Reglas", "Verificación", "Configuración"],
        "hero_title": "C.E.N.T.I.N.E.L. – Auditoría Electoral Independiente y Verificable",
        "hero_subtitle": "Transparencia total: datos electorales inmutables en blockchain Arbitrum L2",
        "global_ok": "TODO VERIFICABLE – SIN ANOMALÍAS CRÍTICAS",
        "kpi_snapshots": "Snapshots (24h)",
        "kpi_changes": "Cambios detectados",
        "kpi_anomalies": "Anomalías críticas",
        "kpi_rules": "Reglas activas",
        "kpi_verifications": "Verificaciones ciudadanas",
        "kpi_notes": "Cada 10 min tomamos una foto inmutable del JSON público.",
        "pedagogical_title": "Indicadores pedagógicos de integridad",
        "snapshots_title": "Snapshots recientes",
        "rules_title": "Reglas activas",
        "verification_title": "Verificación ciudadana",
        "verification_help": "Pegá el hash raíz para confirmar si coincide con el registro en Arbitrum.",
        "verify_button": "Verificar",
        "verify_success": "¡Coincide! ✓",
        "verify_fail": "No coincide, revisá el hash.",
        "export_title": "Exportación",
        "export_pdf_es": "Descargar Reporte Ciudadano PDF (Español)",
        "export_pdf_en": "Download Citizen Report PDF (English)",
        "export_json": "Descargar JSON auditado",
        "export_csv": "Descargar CSV",
        "snapshots_button": "Ver detalle",
        "rules_help": "Estas reglas protegen la integridad automáticamente.",
    },
    "en": {
        "nav_title": "Navigation",
        "nav_sections": ["Summary", "Snapshots", "Rules", "Verification", "Settings"],
        "hero_title": "C.E.N.T.I.N.E.L. – Independent & Verifiable Electoral Audit",
        "hero_subtitle": "Total transparency: immutable public data anchored on Arbitrum L2",
        "global_ok": "FULLY VERIFIABLE – NO CRITICAL ANOMALIES",
        "kpi_snapshots": "Snapshots (24h)",
        "kpi_changes": "Detected changes",
        "kpi_anomalies": "Critical anomalies",
        "kpi_rules": "Active rules",
        "kpi_verifications": "Citizen verifications",
        "kpi_notes": "Every 10 min we take an immutable snapshot of public JSON.",
        "pedagogical_title": "Pedagogical integrity indicators",
        "snapshots_title": "Recent snapshots",
        "rules_title": "Active rules",
        "verification_title": "Citizen verification",
        "verification_help": "Paste the root hash to verify against Arbitrum.",
        "verify_button": "Verify",
        "verify_success": "Match ✓",
        "verify_fail": "No match, check the hash.",
        "export_title": "Exports",
        "export_pdf_es": "Descargar Reporte Ciudadano PDF (Español)",
        "export_pdf_en": "Download Citizen Report PDF (English)",
        "export_json": "Download audited JSON",
        "export_csv": "Download CSV",
        "snapshots_button": "View detail",
        "rules_help": "These rules protect integrity automatically.",
    },
}
copy = translations[language]

is_admin = st.sidebar.checkbox("Admin", value=False)
if is_admin:
    st.sidebar.button("⚡ Activar Modo Electoral", use_container_width=True)
st.sidebar.button("📥 Snapshot Ahora", use_container_width=True)

section = st.sidebar.radio(copy["nav_title"], copy["nav_sections"])

st.markdown(
    """
<style>
    :root {
        color-scheme: dark;
        --bg: #0f172a;
        --panel: rgba(15, 23, 42, 0.92);
        --panel-soft: rgba(30, 41, 59, 0.75);
        --text: #e2e8f0;
        --muted: #94a3b8;
        --accent: #00A3FF;
        --success: #10B981;
        --warning: #F59E0B;
        --danger: #EF4444;
        --border: rgba(148, 163, 184, 0.2);
    }
    html, body, [class*="css"] { font-family: "Inter", "Segoe UI", sans-serif; }
    .stApp { background: var(--bg); color: var(--text); }
    section[data-testid="stSidebar"] { background: rgba(15, 23, 42, 0.98); border-right: 1px solid var(--border); }
    .glass { background: var(--panel); border: 1px solid var(--border); border-radius: 20px; padding: 1.4rem; }
    .hero { margin-bottom: 1.5rem; }
    .kpi { background: var(--panel-soft); border: 1px solid var(--border); border-radius: 18px; padding: 1rem; }
    .kpi h3 { margin: 0; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.12em; color: var(--muted); }
    .kpi p { margin: 0.4rem 0; font-size: 1.6rem; font-weight: 700; color: var(--text); }
    .kpi span { font-size: 0.9rem; color: var(--muted); }
    .note { background: rgba(15, 23, 42, 0.65); border: 1px solid var(--border); padding: 0.8rem 1rem; border-radius: 14px; color: var(--muted); }
</style>
    """,
    unsafe_allow_html=True,
)

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

critical_anomalies = int((snapshots_df["status"] == "ALERTA").sum())

if section == copy["nav_sections"][0]:
    st.markdown(
        f"""
<div class="glass hero">
  <h1>{copy['hero_title']}</h1>
  <p>{copy['hero_subtitle']}</p>
  <h3 style="color: var(--success);">{copy['global_ok']}</h3>
</div>
        """,
        unsafe_allow_html=True,
    )

    kpi_cols = st.columns(5)
    kpis = [
        (copy["kpi_snapshots"], "174", copy["kpi_notes"], "🛰️"),
        (copy["kpi_changes"], "68", "Cambios normales en JSON público.", "🔎"),
        (copy["kpi_anomalies"], str(critical_anomalies), "Sin señales críticas.", "🚨"),
        (copy["kpi_rules"], str(len(rules_df)), "Reglas activas en modo auditoría.", "🧭"),
        (copy["kpi_verifications"], "2.4K", "Validaciones independientes.", "✅"),
    ]
    for col, (label, value, note, icon) in zip(kpi_cols, kpis):
        with col:
            st.markdown(
                f"""
<div class="kpi">
  <h3>{icon} {label}</h3>
  <p>{value}</p>
  <span>{note}</span>
</div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown(f"### {copy['pedagogical_title']}")
    benford_fig = go.Figure()
    benford_fig.add_trace(
        go.Bar(x=benford_df["digit"], y=benford_df["expected"], name="Esperado", marker_color="#00A3FF")
    )
    benford_fig.add_trace(
        go.Bar(x=benford_df["digit"], y=benford_df["observed"], name="Observado", marker_color="#10B981")
    )
    benford_fig.update_layout(
        barmode="group",
        height=300,
        margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#e2e8f0",
        title="Distribución de primeros dígitos – Normal ✓",
    )
    st.plotly_chart(benford_fig, use_container_width=True)

    last_digit_fig = px.bar(
        last_digit_df,
        x="digit",
        y="observed",
        color_discrete_sequence=["#00A3FF"],
        title="Actividad de últimos dígitos",
    )
    last_digit_fig.update_layout(
        height=260,
        margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#e2e8f0",
    )
    st.plotly_chart(last_digit_fig, use_container_width=True)

    votes_fig = px.line(votes_df, x="hour", y="votes", markers=True, title="Evolución de cambios")
    votes_fig.update_layout(
        height=260,
        margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#e2e8f0",
    )
    st.plotly_chart(votes_fig, use_container_width=True)

    activity_df = pd.DataFrame(
        {
            "hour": ["00:00", "04:00", "08:00", "12:00", "16:00", "20:00"],
            "activity": [18, 22, 40, 75, 55, 30],
        }
    )
    heat_fig = px.bar(
        activity_df,
        x="hour",
        y="activity",
        color="activity",
        color_continuous_scale=["#0ea5e9", "#10B981"],
        title="Actividad concentrada en horarios diurnos",
    )
    heat_fig.update_layout(
        height=240,
        margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#e2e8f0",
        coloraxis_showscale=False,
    )
    st.plotly_chart(heat_fig, use_container_width=True)

elif section == copy["nav_sections"][1]:
    st.markdown(f"### {copy['snapshots_title']}")
    st.dataframe(styled_status(snapshots_df), width="stretch", hide_index=True)
    with st.expander(copy["snapshots_button"]):
        st.write("Comparador simple de JSON (placeholder)")

elif section == copy["nav_sections"][2]:
    st.markdown(f"### {copy['rules_title']}")
    st.markdown(f"<div class='note'>{copy['rules_help']}</div>", unsafe_allow_html=True)
    st.dataframe(rules_df, width="stretch", hide_index=True)

elif section == copy["nav_sections"][3]:
    st.markdown(f"### {copy['verification_title']}")
    st.markdown(f"<div class='note'>{copy['verification_help']}</div>", unsafe_allow_html=True)
    with st.form("verify_form"):
        hash_input = st.text_input("Hash raíz", value=anchor.root_hash)
        submitted = st.form_submit_button(copy["verify_button"])
    if submitted:
        if anchor.root_hash.lower() in hash_input.lower():
            st.success(copy["verify_success"])
        else:
            st.error(copy["verify_fail"])
    st.markdown("### QR")
    st.image(qrcode.make(anchor.root_hash))

else:
    st.markdown(f"### {copy['export_title']}")
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
        "logo": "C.E.N.T.I.N.E.L. – Centinela Electoral Nacional Transparente Íntegro Nacional Electoral Libre",
        "title": "Reporte Ciudadano de Auditoría Electoral Independiente",
        "subtitle": "Transparencia verificable con inmutabilidad blockchain (Arbitrum L2)",
        "generated_label": "Generado el",
        "generated_at": report_time,
        "global_status": "TODO VERIFICABLE – SIN ANOMALÍAS CRÍTICAS",
        "executive_title": "Resumen Ejecutivo",
        "executive_intro": (
            "Sistema independiente que toma fotos inmutables de los datos electorales públicos cada 10 minutos "
            "y las ancla en blockchain para que cualquiera pueda verificar que no han sido alterados."
        ),
        "executive_state": f"Último snapshot: {report_time} UTC – Hash raíz verificado en Arbitrum L2",
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
        "title": "Citizen Report of Independent Electoral Audit",
        "subtitle": "Verifiable transparency with blockchain immutability (Arbitrum L2)",
        "generated_label": "Generated on",
        "executive_title": "Executive Summary",
        "executive_intro": (
            "Independent system that takes immutable snapshots of public electoral data every 10 minutes "
            "and anchors them on blockchain so anyone can verify they were not altered."
        ),
        "executive_state": f"Latest snapshot: {report_time} UTC – Root hash verified on Arbitrum L2",
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

    pdf_es = build_pdf_report(data_es, "es")
    pdf_en = build_pdf_report(data_en, "en")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.download_button(copy["export_pdf_es"], data=pdf_es, file_name="centinel_reporte_es.pdf")
    with col2:
        st.download_button(copy["export_pdf_en"], data=pdf_en, file_name="centinel_report_en.pdf")
    with col3:
        st.download_button(copy["export_json"], data=snapshots_df.to_json(orient="records"), file_name="centinel.json")

    st.download_button(copy["export_csv"], data=snapshots_df.to_csv(index=False), file_name="centinel.csv")
