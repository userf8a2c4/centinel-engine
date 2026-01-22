import datetime as dt
from dataclasses import dataclass

import pandas as pd
import plotly.express as px
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
            "timestamp": (now - dt.timedelta(hours=18)).strftime("%Y-%m-%d %H:%M UTC"),
            "hash": "9a7d1f...e2b8",
            "changes": 0,
            "detail": "Sin cambios detectados",
            "status": "OK",
        },
        {
            "timestamp": (now - dt.timedelta(hours=12)).strftime("%Y-%m-%d %H:%M UTC"),
            "hash": "c31f22...9a11",
            "changes": 4,
            "detail": "Archivo actas.csv cambió de 150KB a 152KB",
            "status": "ALERTA",
        },
        {
            "timestamp": (now - dt.timedelta(hours=6)).strftime("%Y-%m-%d %H:%M UTC"),
            "hash": "f55a10...77c2",
            "changes": 1,
            "detail": "Registro 10298 actualizado",
            "status": "REVISAR",
        },
        {
            "timestamp": now.strftime("%Y-%m-%d %H:%M UTC"),
            "hash": "b12d0c...aa91",
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
                "regla": "Cambios > 5% en archivos clave",
                "severidad": "Crítica",
                "estado": "Activa",
            },
            {
                "regla": "Timestamps fuera de ventana esperada",
                "severidad": "Alta",
                "estado": "Activa",
            },
            {
                "regla": "Duplicados en registros maestros",
                "severidad": "Media",
                "estado": "Activa",
            },
        ]
    )


def styled_status(df: pd.DataFrame):
    def highlight_status(value: str) -> str:
        color_map = {
            "OK": "background-color: #e7f6e8; color: #1e4620;",
            "REVISAR": "background-color: #fff4e5; color: #663c00;",
            "ALERTA": "background-color: #fdecea; color: #611a15;",
        }
        return color_map.get(value, "")

    return df.style.map(highlight_status, subset=["status"])


st.set_page_config(
    page_title="Centinel | Dashboard",
    page_icon="🔒",
    layout="wide",
)

st.markdown(
    """
<style>
    .hero {
        padding: 1.5rem;
        border-radius: 16px;
        background: linear-gradient(135deg, #0f172a, #1e293b);
        color: white;
        margin-bottom: 1.5rem;
    }
    .hero h1 {
        margin-bottom: 0.25rem;
        font-size: 2rem;
    }
    .pillars {
        display: flex;
        gap: 1.5rem;
        flex-wrap: wrap;
        margin-top: 1rem;
    }
    .pillar {
        background: rgba(255, 255, 255, 0.08);
        padding: 0.85rem 1rem;
        border-radius: 12px;
        font-size: 0.95rem;
    }
    .card {
        border-radius: 16px;
        padding: 1rem 1.25rem;
        border: 1px solid #e2e8f0;
        background-color: #ffffff;
        box-shadow: 0 4px 14px rgba(15, 23, 42, 0.06);
    }
    .card.green {
        border-color: #bbf7d0;
        background: #f0fdf4;
    }
    .card h3 {
        margin: 0 0 0.25rem 0;
        font-size: 1rem;
        color: #0f172a;
    }
    .card p {
        margin: 0;
        color: #475569;
        font-size: 0.95rem;
    }
</style>
    """,
    unsafe_allow_html=True,
)

anchor = BlockchainAnchor(
    root_hash="3f1b9c8e2c9d5b8f1a7e0d5c4b2a91ff",
    network="Arbitrum L2",
    tx_url="https://arbiscan.io/tx/0x9f3b0c0d1d2e3f4a5b6c7d8e9f000111222333444555666777888999aaa",
    anchored_at="2026-01-12 18:40 UTC",
)

st.sidebar.title("Centinel")
st.sidebar.caption("Transparencia electoral verificable")

if st.sidebar.button("📥 Snapshot ahora"):
    st.sidebar.success("Snapshot programado para la próxima ventana.")
if st.sidebar.button("⚡ Activar modo electoral"):
    st.sidebar.success("Modo electoral activado (cadencia intensiva).")
if st.sidebar.button("⚙️ Configuración de reglas"):
    st.sidebar.info("Abrí el tab de análisis para editar reglas.")

st.sidebar.markdown("---")
st.sidebar.write("**Modo actual:** Electoral")
st.sidebar.write("**Cadencia:** cada 10 minutos")
st.sidebar.write("**Último snapshot:** hace 6 minutos")

st.markdown(
    """
<div class="hero">
  <h1>Auditoría Electoral Independiente con Inmutabilidad Blockchain</h1>
  <p>Centinel convierte datos públicos en evidencia inmutable, reproducible y verificable por cualquier ciudadano.</p>
  <div class="pillars">
    <div class="pillar">🔒 Inmutabilidad L2</div>
    <div class="pillar">📊 Detección Automática</div>
    <div class="pillar">⚙️ Reglas Personalizables</div>
    <div class="pillar">📄 Reportes Reproducibles</div>
  </div>
</div>
    """,
    unsafe_allow_html=True,
)

tab_overview, tab_snapshots, tab_analysis, tab_reports = st.tabs(
    ["Overview", "Snapshots", "Análisis", "Reportes"]
)

with tab_overview:
    st.subheader("Pilar principal: Inmutabilidad criptográfica + Blockchain L2")
    col_hash, col_mode, col_snapshot = st.columns([2, 1, 1])

    with col_hash:
        st.markdown(
            f"""
<div class="card green">
  <h3>Hash raíz actual</h3>
  <p><strong>{anchor.root_hash}</strong></p>
  <p>🔗 Anclado en {anchor.network}</p>
  <p>🕒 {anchor.anchored_at}</p>
</div>
            """,
            unsafe_allow_html=True,
        )
        st.link_button("Verificar en Blockchain", anchor.tx_url)

    with col_mode:
        st.markdown(
            """
<div class="card">
  <h3>Modo de operación</h3>
  <p><strong>Electoral</strong></p>
  <p>Cadencia: cada 10 minutos</p>
</div>
            """,
            unsafe_allow_html=True,
        )

    with col_snapshot:
        st.markdown(
            """
<div class="card">
  <h3>Último snapshot</h3>
  <p><strong>Hace 6 minutos</strong></p>
  <p>Cadena de hashes verificada</p>
</div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("### Indicadores de auditoría")
    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    metric_col1.metric("Snapshots (24h)", "144", "+12")
    metric_col2.metric("Cambios detectados", "5", "-2")
    metric_col3.metric("Anomalías críticas", "0", "-1")
    metric_col4.metric("Reglas activas", "12", "+1")

    st.markdown("### Operación inteligente")
    op_col1, op_col2, op_col3 = st.columns(3)
    op_col1.metric("Modo actual", "Electoral")
    op_col2.metric("Cadencia", "10 min")
    op_col3.metric("Último snapshot", "6 min")

with tab_snapshots:
    st.subheader("Detección automática y reproducible de cambios")
    snapshot_df = build_snapshot_data()
    st.dataframe(
        styled_status(snapshot_df),
        width="stretch",
        hide_index=True,
    )
    st.caption("Estados: OK (sin anomalías), REVISAR (cambios menores), ALERTA (anomalías graves).")

with tab_analysis:
    st.subheader("Análisis basado en reglas configurables")
    rules_df = build_rules_data()
    st.dataframe(rules_df, width="stretch", hide_index=True)

    if st.button("Ejecutar análisis con reglas"):
        st.success("0 anomalías críticas detectadas. 1 cambio menor en revisión.")

    chart_df = snapshot_df.copy()
    chart_df["timestamp"] = pd.to_datetime(chart_df["timestamp"].str.replace(" UTC", ""))
    fig = px.line(
        chart_df,
        x="timestamp",
        y="changes",
        markers=True,
        title="Cambios detectados por snapshot",
    )
    fig.update_layout(yaxis_title="Cambios", xaxis_title="Hora")
    st.plotly_chart(fig, use_container_width=True)

with tab_reports:
    st.subheader("Reportes reproducibles y descargables")
    st.write("Generá reportes técnicos auditables con cadena de hashes, anclaje L2 y anomalías detectadas.")

    report_csv = snapshot_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Descargar reporte CSV",
        data=report_csv,
        file_name="centinel_reporte.csv",
        mime="text/csv",
    )
    st.download_button(
        "Descargar reporte PDF (demo)",
        data=b"%PDF-1.4\n%Centinel demo report\n",
        file_name="centinel_reporte.pdf",
        mime="application/pdf",
    )

    st.markdown("### Preview del reporte")
    st.dataframe(snapshot_df.head(3), width="stretch", hide_index=True)
