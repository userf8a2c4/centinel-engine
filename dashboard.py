import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
from datetime import datetime
import os
import glob

# Configuración de página
st.set_page_config(
    page_title="Centinel - Auditoría Electoral Honduras 2025",
    page_icon="📡",
    layout="wide"
)

# Tema oscuro básico
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #fafafa; }
    .metric-delta { font-size: 1.2rem !important; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# CARGAR TODOS LOS SNAPSHOTS REALES (desde carpeta local o fixtures)
# ──────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)  # Cache 5 min
def load_snapshots():
    # Busca en las carpetas típicas del repo
    patterns = [
        "data/snapshots_2025/*.json",
        "tests/fixtures/snapshots_2025/*.json",
        "*.json"  # fallback si está suelto
    ]
    
    snapshot_files = []
    for pattern in patterns:
        snapshot_files.extend(glob.glob(pattern))
    
    if not snapshot_files:
        st.error("No se encontraron archivos JSON. Verifica las carpetas data/ o tests/fixtures/")
        return pd.DataFrame(), {}, pd.DataFrame()
    
    snapshots = []
    for file_path in sorted(snapshot_files, reverse=True):  # Más reciente primero
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                data['source_path'] = os.path.basename(file_path)
                # Intentamos extraer timestamp del nombre del archivo si no está en el JSON
                if 'timestamp' not in data:
                    # Ejemplo: HN.PRESIDENTE.00-TODOS.000-TODOS 2025-12-03 21_00_11.json
                    parts = os.path.basename(file_path).split()
                    for part in parts:
                        if '2025' in part and '_' in part:
                            ts_str = part.replace('_', ':').replace('.json', '')
                            try:
                                data['timestamp'] = datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S').isoformat()
                                break
                            except:
                                pass
                snapshots.append(data)
        except Exception as e:
            st.warning(f"Error cargando {file_path}: {e}")
    
    if not snapshots:
        return pd.DataFrame(), {}, pd.DataFrame()
    
    # DataFrame resumen general
    df_summary = pd.DataFrame([{
        "timestamp": s.get("timestamp", "Desconocido"),
        "actas_divulgadas": s.get("estadisticas", {}).get("totalizacion_actas", {}).get("actas_divulgadas", "N/A"),
        "validos": int(s.get("estadisticas", {}).get("distribucion_votos", {}).get("validos", "0").replace(",", "")),
        "nulos": int(s.get("estadisticas", {}).get("distribucion_votos", {}).get("nulos", "0").replace(",", "")),
        "blancos": int(s.get("estadisticas", {}).get("distribucion_votos", {}).get("blancos", "0").replace(",", "")),
        "source_path": s.get("source_path", "")
    } for s in snapshots if "estadisticas" in s])
    
    df_summary["timestamp"] = pd.to_datetime(df_summary["timestamp"], errors='coerce')
    df_summary = df_summary.sort_values("timestamp")
    
    # Último snapshot
    last_snapshot = snapshots[0]
    
    # DataFrame candidatos dinámico
    resultados = last_snapshot.get("resultados", [])
    df_candidates = pd.DataFrame(resultados)
    # Limpiar y convertir votos a numérico
    if not df_candidates.empty:
        df_candidates['votos_num'] = df_candidates['votos'].str.replace(",", "").astype(int)
        df_candidates = df_candidates.sort_values('votos_num', ascending=False)
    
    return df_summary, last_snapshot, df_candidates

df_snapshots, last_snapshot, df_candidates = load_snapshots()

# ──────────────────────────────────────────────────────────────────────────────
# HEADER
# ──────────────────────────────────────────────────────────────────────────────
st.title("📡 Centinel - Auditoría Electoral 2025")
st.markdown("Monitoreo automático y neutral de datos públicos del CNE • Honduras 30N 2025")

if last_snapshot:
    ts_display = last_snapshot.get("timestamp", "Último snapshot")
    st.success(f"✓ Datos cargados • Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.caption(f"Snapshot fuente: {last_snapshot.get('source_path', 'Desconocido')}")
else:
    st.error("No hay snapshots válidos cargados.")

# ──────────────────────────────────────────────────────────────────────────────
# KPIs dinámicos
# ──────────────────────────────────────────────────────────────────────────────
st.subheader("Panorama General")

if not df_snapshots.empty:
    current = last_snapshot.get("estadisticas", {})
    distrib = current.get("distribucion_votos", {})
    totalizacion = current.get("totalizacion_actas", {})
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    col1.metric("Actas Divulgadas", totalizacion.get("actas_divulgadas", "N/A"))
    col2.metric("Votos Válidos", f"{distrib.get('validos', '0'):,}")
    col3.metric("Votos Nulos", f"{distrib.get('nulos', '0'):,}")
    col4.metric("Votos Blancos", f"{distrib.get('blancos', '0'):,}")
    
    # Porcentaje avance aproximado (actas divulgadas / totales)
    actas_totales = int(totalizacion.get("actas_totales", 1))
    actas_div = int(totalizacion.get("actas_divulgadas", 0))
    porc_avance = (actas_div / actas_totales) * 100 if actas_totales > 0 else 0
    
    st.progress(porc_avance / 100)
    st.caption(f"**Progreso de totalización: {porc_avance:.1f}%** ({actas_div:,} de {actas_totales:,} actas)")

# ──────────────────────────────────────────────────────────────────────────────
# PIE CHART DINÁMICO
# ──────────────────────────────────────────────────────────────────────────────
st.subheader("Distribución de Votos Válidos - Último Snapshot")

if not df_candidates.empty:
    fig_pie = px.pie(
        df_candidates,
        values="votos_num",
        names="candidato",
        hover_data=["partido", "porcentaje", "votos"],
        title="Participación por Candidato",
        hole=0.35,
        color_discrete_sequence=px.colors.qualitative.Set1
    )
    
    fig_pie.update_traces(textposition='inside', textinfo='percent+label')
    fig_pie.update_layout(
        legend_title_text="Candidatos",
        template="plotly_dark",
        height=600
    )
    
    st.plotly_chart(fig_pie, use_container_width=True)
else:
    st.info("No hay resultados de candidatos en el snapshot actual.")

# ──────────────────────────────────────────────────────────────────────────────
# EVOLUCIÓN (si hay más de 1 snapshot)
# ──────────────────────────────────────────────────────────────────────────────
st.subheader("Evolución del Conteo (si hay múltiples snapshots)")

if len(df_snapshots) > 1:
    fig_line = go.Figure()
    
    fig_line.add_trace(go.Scatter(
        x=df_snapshots["timestamp"],
        y=df_snapshots["validos"],
        mode='lines+markers',
        name='Votos Válidos'
    ))
    
    fig_line.add_trace(go.Scatter(
        x=df_snapshots["timestamp"],
        y=df_snapshots["nulos"],
        mode='lines+markers',
        name='Votos Nulos'
    ))
    
    fig_line.update_layout(
        xaxis_title="Fecha / Hora",
        yaxis_title="Cantidad de Votos",
        template="plotly_dark",
        hovermode="x unified",
        legend=dict(orientation="h", y=1.02)
    )
    
    st.plotly_chart(fig_line, use_container_width=True)
else:
    st.info("Se necesitan al menos 2 snapshots para mostrar evolución temporal.")

# ──────────────────────────────────────────────────────────────────────────────
# TABLAS
# ──────────────────────────────────────────────────────────────────────────────
st.subheader("Detalles del Último Snapshot")

if not df_candidates.empty:
    st.dataframe(
        df_candidates[["candidato", "partido", "votos", "porcentaje"]].style.format({"votos": "{:,}"}),
        use_container_width=True
    )

with st.expander("Estadísticas adicionales"):
    st.json(last_snapshot.get("estadisticas", {}))

st.markdown("---")
st.caption("Powered by Streamlit • Proyecto Sentinel 🇭🇳 • Datos públicos del CNE")
