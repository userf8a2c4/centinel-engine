import datetime as dt
from dataclasses import dataclass

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


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
            "timestamp": (now - dt.timedelta(minutes=50)).strftime("%Y-%m-%d %H:%M UTC"),
            "hash": "0x91c2...ab10",
            "changes": 0,
            "detail": "Sin cambios detectados",
            "status": "OK",
        },
        {
            "timestamp": (now - dt.timedelta(minutes=40)).strftime("%Y-%m-%d %H:%M UTC"),
            "hash": "0x88fa...e901",
            "changes": 2,
            "detail": "Archivo actas.csv cambió de 150KB a 152KB",
            "status": "REVISAR",
        },
        {
            "timestamp": (now - dt.timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M UTC"),
            "hash": "0xe41b...93f0",
            "changes": 1,
            "detail": "Registro 10298 actualizado",
            "status": "REVISAR",
        },
        {
            "timestamp": (now - dt.timedelta(minutes=20)).strftime("%Y-%m-%d %H:%M UTC"),
            "hash": "0x7b99...ae02",
            "changes": 7,
            "detail": "Alteración crítica en acta 2024-09",
            "status": "ALERTA",
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
                "regla": "Variaciones > 5% en archivos clave",
                "tipo": "Umbral",
                "severidad": "Crítica",
                "estado": "ON",
                "acciones": "Notificar + Pausar",
            },
            {
                "regla": "Regex de inconsistencias",
                "tipo": "Regex",
                "severidad": "Media",
                "estado": "ON",
                "acciones": "Alertar",
            },
            {
                "regla": "Modelo IA de anomalías",
                "tipo": "IA",
                "severidad": "Alta",
                "estado": "OFF",
                "acciones": "Notificar + Exportar",
            },
        ]
    )


def styled_status(df: pd.DataFrame):
    def highlight_status(value: str) -> str:
        color_map = {
            "OK": "background-color: rgba(16, 185, 129, 0.2); color: #10b981;",
            "REVISAR": "background-color: rgba(248, 158, 11, 0.2); color: #f59e0b;",
            "ALERTA": "background-color: rgba(248, 113, 113, 0.2); color: #f87171;",
        }
        return color_map.get(value, "")

    return df.style.map(highlight_status, subset=["status"])


st.set_page_config(
    page_title="Centinel | Auditoría Electoral",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    :root {
        color-scheme: dark;
    }
    .stApp {
        background: radial-gradient(circle at top, rgba(0, 212, 255, 0.12), transparent 55%), #0b0f1a;
        color: #e2e8f0;
    }
    section[data-testid="stSidebar"] {
        background: rgba(12, 18, 34, 0.95);
        border-right: 1px solid rgba(148, 163, 184, 0.2);
    }
    .glass {
        background: linear-gradient(135deg, rgba(15, 23, 42, 0.78), rgba(30, 41, 59, 0.55));
        border: 1px solid rgba(148, 163, 184, 0.18);
        backdrop-filter: blur(14px);
        border-radius: 18px;
        padding: 1.25rem;
    }
    .hero {
        padding: 1.75rem;
        border-radius: 24px;
        background: linear-gradient(135deg, rgba(15, 23, 42, 0.88), rgba(30, 41, 59, 0.65));
        border: 1px solid rgba(0, 212, 255, 0.25);
        box-shadow: 0 0 40px rgba(0, 212, 255, 0.08);
        color: #ffffff;
        margin-bottom: 1.5rem;
    }
    .hero h1 {
        margin-bottom: 0.5rem;
        font-size: 2.1rem;
    }
    .pillars {
        display: flex;
        gap: 1rem;
        flex-wrap: wrap;
        margin-top: 1rem;
    }
    .pillar {
        background: rgba(255, 255, 255, 0.08);
        padding: 0.75rem 1rem;
        border-radius: 999px;
        font-size: 0.9rem;
        border: 1px solid rgba(148, 163, 184, 0.2);
    }
    .section-title {
        font-size: 1.05rem;
        color: #e2e8f0;
        margin-bottom: 0.35rem;
    }
    .section-subtitle {
        color: #94a3b8;
        font-size: 0.85rem;
        margin-bottom: 0.75rem;
    }
    .kpi-grid {
        display: grid;
        gap: 1rem;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        margin-bottom: 1.5rem;
    }
    .kpi-card {
        background: rgba(15, 23, 42, 0.8);
        border: 1px solid rgba(148, 163, 184, 0.2);
        border-radius: 18px;
        padding: 1rem 1.1rem;
    }
    .kpi-card h3 {
        margin: 0;
        font-size: 0.8rem;
        letter-spacing: 0.2em;
        text-transform: uppercase;
        color: #94a3b8;
    }
    .kpi-card p {
        margin: 0.35rem 0 0 0;
        font-size: 1.35rem;
        font-weight: 600;
        color: #ffffff;
    }
    .kpi-card span {
        font-size: 0.75rem;
        color: #38bdf8;
    }
    .badge {
        display: inline-block;
        padding: 0.25rem 0.6rem;
        border-radius: 999px;
        font-size: 0.75rem;
        border: 1px solid rgba(148, 163, 184, 0.2);
        color: #e2e8f0;
    }
    .badge.green {
        color: #10b981;
        border-color: rgba(16, 185, 129, 0.45);
    }
    .badge.blue {
        color: #00d4ff;
        border-color: rgba(0, 212, 255, 0.45);
    }
    .badge.purple {
        color: #8b5cf6;
        border-color: rgba(139, 92, 246, 0.45);
    }
    .table-note {
        color: #94a3b8;
        font-size: 0.8rem;
        margin-top: 0.5rem;
    }
</style>
    """,
    unsafe_allow_html=True,
)

anchor = BlockchainAnchor(
    root_hash="0x9f3a7c2d1b4a7e1f02d5e1c34aa9b21b",
    network="Arbitrum L2",
    tx_url="https://arbiscan.io/tx/0x9f3b0c0d1d2e3f4a5b6c7d8e9f000111222333444555666777888999aaa",
    anchored_at="2026-01-12 18:40 UTC",
)

st.sidebar.markdown("## Centinel")
st.sidebar.caption("Transparencia electoral verificable")

st.sidebar.markdown("### Navegación")
st.sidebar.write("• Overview")
st.sidebar.write("• Snapshots")
st.sidebar.write("• Análisis avanzado")
st.sidebar.write("• Reglas & alertas")
st.sidebar.write("• Reportes")
st.sidebar.write("• Verificación on-chain")
st.sidebar.write("• Configuración")

st.sidebar.markdown("---")

if st.sidebar.button("⚡ Activar Modo Electoral", use_container_width=True):
    st.sidebar.success("Modo electoral activado (cadencia intensiva).")
if st.sidebar.button("📥 Snapshot Ahora", use_container_width=True):
    st.sidebar.success("Snapshot programado para la próxima ventana.")

st.sidebar.markdown("---")
st.sidebar.markdown("**Estado**")
st.sidebar.write("Modo: Electoral Activo")
st.sidebar.write("Cadena: Arbitrum L2")
st.sidebar.write("Último snapshot: hace 4 min")

st.markdown(
    """
<div class="hero">
  <h1>Auditoría Electoral Independiente con Inmutabilidad Blockchain</h1>
  <p>Centinel convierte datos públicos en evidencia inmutable, reproducible y verificable por cualquier ciudadano.</p>
  <div class="pillars">
    <div class="pillar">🔒 Inmutabilidad L2</div>
    <div class="pillar">📊 Detección automática con IA</div>
    <div class="pillar">⚙️ Reglas personalizables</div>
    <div class="pillar">🧾 Reportes reproducibles</div>
    <div class="pillar">🛰️ Verificación on-chain</div>
  </div>
</div>
    """,
    unsafe_allow_html=True,
)

header_col1, header_col2, header_col3, header_col4 = st.columns([2.2, 1.2, 1.2, 1.1])
with header_col1:
    st.markdown(
        f"""
<div class="glass">
  <div class="section-title">Hash raíz actual</div>
  <div class="section-subtitle">{anchor.root_hash}</div>
  <span class="badge blue">Inmutable y verificado en {anchor.network}</span>
</div>
        """,
        unsafe_allow_html=True,
    )
with header_col2:
    st.markdown(
        """
<div class="glass">
  <div class="section-title">Último snapshot</div>
  <div class="section-subtitle">Hace 4 min</div>
  <span class="badge green">Snapshots cada 10 min</span>
</div>
        """,
        unsafe_allow_html=True,
    )
with header_col3:
    st.markdown(
        """
<div class="glass">
  <div class="section-title">Verificación ciudadana</div>
  <div class="section-subtitle">2.4K consultas</div>
  <span class="badge purple">Proof pública</span>
</div>
        """,
        unsafe_allow_html=True,
    )
with header_col4:
    st.link_button("Verificar en Blockchain", anchor.tx_url, use_container_width=True)

st.markdown("### Overview")
st.markdown("<div class='kpi-grid'>" 
    "<div class='kpi-card'><h3>Snapshots 24h</h3><p>174</p><span>+12 vs ayer</span></div>"
    "<div class='kpi-card'><h3>Cambios detectados</h3><p>68</p><span>▼ 14%</span></div>"
    "<div class='kpi-card'><h3>Anomalías críticas</h3><p>0</p><span>Sin incidentes</span></div>"
    "<div class='kpi-card'><h3>Reglas activas</h3><p>12</p><span>2 nuevas</span></div>"
    "<div class='kpi-card'><h3>Verificaciones</h3><p>2.4K</p><span>+8%</span></div>"
    "</div>", unsafe_allow_html=True)

snapshots_df = build_snapshot_data()

chart_col1, chart_col2 = st.columns([2, 1])
with chart_col1:
    st.markdown("<div class='glass'><div class='section-title'>Evolución de snapshots y cambios</div>"
                "<div class='section-subtitle'>Últimos 7 días</div>", unsafe_allow_html=True)
    timeline_df = pd.DataFrame(
        {
            "día": ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"],
            "snapshots": [128, 132, 140, 152, 168, 174, 160],
            "cambios": [12, 18, 9, 14, 22, 11, 7],
        }
    )
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=timeline_df["día"], y=timeline_df["snapshots"], mode="lines+markers", name="Snapshots", line=dict(color="#00d4ff")))
    fig.add_trace(go.Scatter(x=timeline_df["día"], y=timeline_df["cambios"], mode="lines+markers", name="Cambios", line=dict(color="#8b5cf6")))
    fig.update_layout(height=280, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#e2e8f0")
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with chart_col2:
    st.markdown("<div class='glass'><div class='section-title'>Distribución de anomalías</div>"
                "<div class='section-subtitle'>Últimas 24h</div>", unsafe_allow_html=True)
    anomaly_df = pd.DataFrame(
        {
            "tipo": ["Cambios no esperados", "Patrones repetidos", "Alteraciones críticas", "Meta-datos"],
            "valor": [38, 21, 12, 29],
        }
    )
    pie_fig = px.pie(anomaly_df, names="tipo", values="valor", hole=0.55)
    pie_fig.update_traces(textinfo="percent", marker=dict(colors=["#00d4ff", "#8b5cf6", "#f87171", "#10b981"]))
    pie_fig.update_layout(height=280, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="rgba(0,0,0,0)", font_color="#e2e8f0", showlegend=False)
    st.plotly_chart(pie_fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<div class='glass'><div class='section-title'>Heatmap de actividad por hora</div>"
            "<div class='section-subtitle'>Detección de patrones sospechosos</div>", unsafe_allow_html=True)
heatmap_df = pd.DataFrame(
    {
        "hora": ["00:00", "04:00", "08:00", "12:00", "16:00", "20:00"],
        "actividad": [20, 32, 48, 71, 58, 36],
    }
)
heat_fig = px.bar(heatmap_df, x="hora", y="actividad", color="actividad", color_continuous_scale=["#0b0f1a", "#00d4ff", "#f87171"])
heat_fig.update_layout(height=260, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#e2e8f0", coloraxis_showscale=False)
st.plotly_chart(heat_fig, use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

st.markdown("### Snapshots recientes")
st.dataframe(
    styled_status(snapshots_df),
    width="stretch",
    hide_index=True,
)
st.caption("Estados: OK (sin anomalías), REVISAR (cambios menores), ALERTA (anomalías graves).")

rules_df = build_rules_data()
col_rules, col_ai = st.columns([1.3, 1])
with col_rules:
    st.markdown("<div class='glass'><div class='section-title'>Reglas personalizadas</div>"
                "<div class='section-subtitle'>Configura respuestas automáticas y auditorías instantáneas</div>", unsafe_allow_html=True)
    st.dataframe(rules_df, width="stretch", hide_index=True)
    st.button("Crear nueva regla", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with col_ai:
    st.markdown("<div class='glass'><div class='section-title'>Detección automática con IA</div>"
                "<div class='section-subtitle'>Alertas en tiempo real</div>", unsafe_allow_html=True)
    st.write("• Patrón anómalo en sección 12 · Alta")
    st.write("• Cambio irregular en acta 2024-09 · Media")
    st.write("• Pico inusual en consultas ciudadanas · Baja")
    st.progress(0.92, text="Confianza anomalías críticas")
    st.progress(0.84, text="Confianza cambios no autorizados")
    st.progress(0.68, text="Confianza inconsistencias menores")
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("### Reportes reproducibles")
st.markdown(
    """
<div class="glass">
  <div class="section-title">Exportación verificable</div>
  <div class="section-subtitle">PDF firmado, JSON auditado y hash reproducible.</div>
</div>
    """,
    unsafe_allow_html=True,
)

report_csv = snapshots_df.to_csv(index=False).encode("utf-8")
col_report1, col_report2, col_report3 = st.columns(3)
with col_report1:
    st.download_button("Descargar reporte CSV", data=report_csv, file_name="centinel_reporte.csv", mime="text/csv", use_container_width=True)
with col_report2:
    st.download_button("Descargar reporte PDF (demo)", data=b"%PDF-1.4\n%Centinel demo report\n", file_name="centinel_reporte.pdf", mime="application/pdf", use_container_width=True)
with col_report3:
    st.download_button("Descargar JSON auditado", data=snapshots_df.to_json(orient="records"), file_name="centinel_reporte.json", mime="application/json", use_container_width=True)

with st.expander("Verificación ciudadana"):
    st.write("Pegá un hash raíz para validar su registro en Arbitrum L2.")
    hash_input = st.text_input("Hash raíz", value="0x9f3a7c2d1b4a7e1f02d5e1c34aa9b21b")
    if st.button("Verificar ahora"):
        if "9f3a" in hash_input.lower():
            st.success("Verificado ✓ Hash confirmado en Arbitrum L2.")
        else:
            st.error("No coincide ✗ El hash no está registrado.")
