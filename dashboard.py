import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
from datetime import datetime
import os
import glob

from scripts.download_and_hash import load_config, normalize_master_switch

# Configuración de página
st.set_page_config(
    page_title="Centinel Dashboard",
    page_icon="📡",
    layout="wide"
)

# Tema oscuro
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #fafafa; }
    .metric-delta { font-size: 1.1rem !important; }
    .master-switch-pill {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 999px;
        font-weight: 700;
        font-size: 0.95rem;
        letter-spacing: 0.08em;
    }
    </style>
""", unsafe_allow_html=True)


def load_master_switch():
    try:
        config = load_config()
    except Exception as exc:
        st.warning(f"No se pudo leer config.yaml: {exc}")
        return "UNKNOWN"
    if "master_switch" not in config:
        return "UNCONFIGURED"
    return normalize_master_switch(config.get("master_switch"))

@st.cache_data(ttl=300)
def load_data():
    snapshot_files = glob.glob("tests/fixtures/snapshots_2025/*.json") or \
                     glob.glob("data/snapshots_2025/*.json") or \
                     glob.glob("*.json")
    
    if not snapshot_files:
        st.error("No se encontraron snapshots JSON en las carpetas esperadas.")
        return pd.DataFrame(), {}, pd.DataFrame()
    
    snapshot_files = sorted(snapshot_files)  # ascendente por fecha
    
    snapshots = []
    for file_path in snapshot_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                data['source_path'] = os.path.basename(file_path)
                # Timestamp fallback desde nombre
                if 'timestamp' not in data:
                    name = os.path.basename(file_path)
                    ts_part = name.split('snapshot_')[-1].split('.')[0].replace('_', ':')
                    try:
                        data['timestamp'] = datetime.strptime(ts_part, '%Y-%m-%dT%H:%M:%S').isoformat()
                    except ValueError:
                        data['timestamp'] = datetime.now().isoformat()
                snapshots.append(data)
        except Exception as e:
            st.warning(f"Error cargando {os.path.basename(file_path)}: {e}")
    
    if not snapshots:
        return pd.DataFrame(), {}, pd.DataFrame()
    
    df_snapshots = pd.DataFrame([{
        "timestamp": pd.to_datetime(s["timestamp"]),
        "registered_voters": s.get("registered_voters", 0),
        "total_votes": s.get("total_votes", 0),
        "valid_votes": s.get("valid_votes", 0),
        "null_votes": s.get("null_votes", 0),
        "blank_votes": s.get("blank_votes", 0),
        "source_path": s["source_path"]
    } for s in snapshots])
    
    df_snapshots = df_snapshots.sort_values("timestamp")
    
    last_snapshot = snapshots[-1]
    
    # Extracción segura de candidatos (soporta ambas estructuras)
    candidates = []
    if isinstance(last_snapshot, dict):
        # Estructura de fixtures (tu captura original)
        candidates = last_snapshot.get("candidates", [])
        if not candidates:
            # Fallback para la estructura anidada en tus fixtures
            votos_blancos = last_snapshot.get("votos_blancos", {})
            if isinstance(votos_blancos, dict):
                candidates = votos_blancos.get("candidatos", [])
        
        # Estructura CNE real (si algún snapshot es así)
        if not candidates:
            candidatos_cne = last_snapshot.get("resultados", [])
            if candidatos_cne:
                candidates = [
                    {
                        "candidato": r.get("candidato", ""),
                        "partido": r.get("partido", ""),
                        "votes": int(r.get("votos", "0").replace(",", "")),
                        "porcentaje": r.get("porcentaje", "")
                    }
                    for r in candidatos_cne
                ]
    
    df_candidates = pd.DataFrame(candidates)
    
    return df_snapshots, last_snapshot, df_candidates

df_snapshots, last_snapshot, df_candidates = load_data()

# HEADER
st.title("📡 Centinel Dashboard")
st.markdown("Visualización automática de snapshots • Datos desde GitHub")

master_switch = load_master_switch()
if master_switch == "ON":
    status_color = "#16a34a"
    status_label = "ON"
    status_detail = "Procesos automáticos activos"
elif master_switch == "OFF":
    status_color = "#dc2626"
    status_label = "OFF"
    status_detail = "Procesos automáticos detenidos"
elif master_switch == "UNCONFIGURED":
    status_color = "#facc15"
    status_label = "SIN CONFIG"
    status_detail = "Configura master_switch en config.yaml"
else:
    status_color = "#f97316"
    status_label = "UNKNOWN"
    status_detail = "Estado no disponible"

st.markdown(
    f"""
    <div style="margin-top: 0.25rem; margin-bottom: 1rem;">
        <span class="master-switch-pill" style="background-color: {status_color}; color: #0e1117;">
            MASTER SWITCH: {status_label}
        </span>
        <span style="margin-left: 0.75rem; font-weight: 600;">{status_detail}</span>
    </div>
    """,
    unsafe_allow_html=True,
)

if last_snapshot:
    st.success(f"✓ Snapshot cargado: {last_snapshot.get('source_path', 'desconocido')}")
    st.caption(f"Última comprobación: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
else:
    st.error("No hay snapshots válidos.")

# KPIs con delta y %
st.subheader("Panorama General")

if not df_snapshots.empty:
    current = last_snapshot
    prev = df_snapshots.iloc[-2] if len(df_snapshots) > 1 else current
    
    delta_emitidos = current.get("total_votes", 0) - prev.get("total_votes", 0)
    
    cols = st.columns(5)
    cols[0].metric("Registrados", f"{current.get('registered_voters', 0):,}")
    cols[1].metric("Votos Emitidos", f"{current.get('total_votes', 0):,}", 
                   delta=f"+{delta_emitidos:,}" if delta_emitidos else None)
    cols[2].metric("Votos Válidos", f"{current.get('valid_votes', 0):,}")
    cols[3].metric("Votos Nulos", f"{current.get('null_votes', 0):,}")
    cols[4].metric("Votos Blancos", f"{current.get('blank_votes', 0):,}")
    
    porc_avance = (current.get("total_votes", 0) / current.get("registered_voters", 1)) * 100
    st.progress(porc_avance / 100)
    st.caption(f"**Escrutinio aproximado: {porc_avance:.1f}%**")

# Pie Chart
st.subheader("Distribución de Votos Válidos (Último Snapshot)")

if not df_candidates.empty:
    # Asegurar columna 'votes' numérica
    if 'votes' in df_candidates.columns:
        df_candidates['votes'] = pd.to_numeric(df_candidates['votes'], errors='coerce').fillna(0)
    
    fig = px.pie(
        df_candidates,
        values="votes",
        names="candidato",
        hover_data=["partido"] if "partido" in df_candidates else None,
        hole=0.4
    )
    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No hay datos de candidatos disponibles en el último snapshot.")

# Evolución
st.subheader("Evolución Temporal")

if len(df_snapshots) > 1:
    fig_line = go.Figure()
    fig_line.add_trace(go.Scatter(x=df_snapshots["timestamp"], y=df_snapshots["total_votes"],
                                  mode='lines+markers', name='Total Votos'))
    fig_line.add_trace(go.Scatter(x=df_snapshots["timestamp"], y=df_snapshots["valid_votes"],
                                  mode='lines+markers', name='Votos Válidos'))
    fig_line.update_layout(template="plotly_dark", hovermode="x unified")
    st.plotly_chart(fig_line, use_container_width=True)

# Tablas
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Totales por Snapshot")
    if not df_snapshots.empty:
        st.dataframe(df_snapshots.style.format(precision=0, thousands=","), use_container_width=True)

with col_right:
    st.subheader("Último Snapshot - Candidatos")
    if not df_candidates.empty:
        st.dataframe(df_candidates, use_container_width=True)

# Explicación simple
with st.expander("¿Qué significan estos números?"):
    st.markdown("""
    - Registrados: Personas habilitadas para votar.
    - Votos Emitidos: Total de votos contados.
    - Votos Válidos: Votos que cuentan para candidatos.
    - Δ: Cambio respecto al snapshot anterior.
    """)

with st.expander("JSON del último snapshot"):
    st.json(last_snapshot)

st.caption("Powered by Streamlit • Sentinel Project")
