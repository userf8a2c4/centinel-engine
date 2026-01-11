# dashboard.py
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

from sentinel.dashboard.data_loader import (
    build_candidates_frame,
    build_totals_frame,
    latest_record,
    load_snapshot_records,
)

# ──────────────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN BÁSICA
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Centinel - Dashboard",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("📡 Centinel Dashboard")
st.markdown("Visualización automática de snapshots generados desde GitHub")


@st.cache_data(ttl=600, show_spinner="Buscando snapshots...")
def get_records() -> list:
    return load_snapshot_records(max_files=100)


records = get_records()
latest = latest_record(records)

if not records or not latest:
    st.error("**No se pudo cargar ningún snapshot con datos útiles**")
    st.info(
        "No se encontraron snapshots con métricas numéricas. "
        "Verifica que existan archivos JSON reales en `data/` o en "
        "`tests/fixtures/snapshots_2025`."
    )
    st.caption("Última comprobación: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    st.stop()

st.success(f"✓ Snapshot cargado: {latest.source_path}")
st.caption("Última comprobación: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

# ──────────────────────────────────────────────────────────────────────────────
# VISIÓN GENERAL
# ──────────────────────────────────────────────────────────────────────────────

st.subheader("Panorama general")

totals_df = build_totals_frame(records)
totals_df["timestamp"] = pd.to_datetime(totals_df["timestamp"])

candidates_df = build_candidates_frame(records)

if totals_df.empty:
    st.warning("No hay datos agregados disponibles para mostrar.")
    st.stop()

latest_totals = totals_df.sort_values("timestamp").iloc[-1]

metrics_cols = st.columns(5)
metrics_cols[0].metric("Registrados", f"{latest_totals['registered_voters']:,}")
metrics_cols[1].metric("Votos emitidos", f"{latest_totals['total_votes']:,}")
metrics_cols[2].metric("Votos válidos", f"{latest_totals['valid_votes']:,}")
metrics_cols[3].metric("Votos nulos", f"{latest_totals['null_votes']:,}")
metrics_cols[4].metric("Votos blancos", f"{latest_totals['blank_votes']:,}")

st.markdown("### Evolución temporal")
trend_df = totals_df.sort_values("timestamp")
fig = px.line(
    trend_df,
    x="timestamp",
    y=["total_votes", "valid_votes", "null_votes", "blank_votes"],
    markers=True,
    labels={"value": "Votos", "timestamp": "Timestamp"},
)
fig.update_layout(legend_title_text="Métrica")
st.plotly_chart(fig, use_container_width=True)

# ──────────────────────────────────────────────────────────────────────────────
# TABLAS PRINCIPALES
# ──────────────────────────────────────────────────────────────────────────────

col1, col2 = st.columns([3, 2])

with col1:
    st.markdown("### Totales por snapshot")
    display_df = totals_df.sort_values("timestamp", ascending=False).head(25)
    st.dataframe(display_df, use_container_width=True)

with col2:
    st.markdown("### Último snapshot (candidatos)")
    latest_candidates = candidates_df[
        candidates_df["source_path"] == latest.source_path
    ]
    if not latest_candidates.empty:
        st.dataframe(
            latest_candidates[["candidate", "party", "votes"]].sort_values(
                "votes", ascending=False
            ),
            use_container_width=True,
        )
    else:
        st.info("No se encontraron candidatos en el último snapshot.")

with st.expander("Ver JSON del último snapshot"):
    st.json(latest.raw_payload)

st.markdown("---")
st.caption("Powered by Streamlit • Datos desde GitHub • Actualización automática")
