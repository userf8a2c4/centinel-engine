"""
Proyecto C.E.N.T.I.N.E.L. - Dashboard de Auditoría Electoral
Versión: 3.0.3 (2026)
"""

import json
import logging
import os
from datetime import datetime
from hashlib import sha256
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sklearn.ensemble import IsolationForest

# --- Configuración de Rutas ---
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
HASH_DIR = BASE_DIR / "hashes"

# Asegurar que existan los directorios
DATA_DIR.mkdir(parents=True, exist_ok=True)
HASH_DIR.mkdir(parents=True, exist_ok=True)

def load_latest_data():
    """Busca y carga el último archivo JSON en /data"""
    if not DATA_DIR.exists():
        return None
    files = list(DATA_DIR.glob("snapshot_*.json"))
    if not files:
        return None
    # Ordenar por fecha de creación para tener el más reciente
    latest_file = max(files, key=os.path.getctime)
    try:
        with open(latest_file, "r", encoding="utf-8") as f:
            payload = json.load(f)
        if isinstance(payload, list):
            return pd.DataFrame(payload)
        if isinstance(payload, dict):
            if "data" in payload and isinstance(payload["data"], list):
                return pd.DataFrame(payload["data"])
            return pd.DataFrame([payload])
        st.error(f"Error cargando el archivo {latest_file.name}: formato no soportado.")
        return None
    except Exception as e:
        st.error(f"Error cargando el archivo {latest_file.name}: {e}")
        return None

def detect_anomalies(df):
    """Detecta anomalías estadísticas en los votos"""
    if df is None or df.empty:
        return pd.DataFrame()
    
    # Columnas esperadas según la plantilla de Sentinel
    cols_interes = ['porcentaje_escrutado', 'votos_totales']
    existentes = [c for c in cols_interes if c in df.columns]
    
    if len(existentes) < 2:
        return pd.DataFrame()

    features = df[existentes].fillna(0)
    model = IsolationForest(contamination=0.05, random_state=42)
    df['anomaly_score'] = model.fit_predict(features)
    
    return df[df['anomaly_score'] == -1]

# --- Interfaz de Usuario ---
st.set_page_config(page_title="C.E.N.T.I.N.E.L. Dashboard", layout="wide")

st.markdown("""
    <h1 style='text-align: center;'>Proyecto C.E.N.T.I.N.E.L.</h1>
    <p style='text-align: center;'>Auditoría Ciudadana Independiente - Honduras 2028/2029</p>
    <hr>
""", unsafe_allow_html=True)

data = load_latest_data()

if data is not None:
    st.sidebar.header("⚙️ Info Técnica")
    st.sidebar.write(f"**Snapshot:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    st.header("🚨 Sistema de Alertas de Integridad")
    alertas = detect_anomalies(data)
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        if not alertas.empty:
            st.error(f"Se detectaron {len(alertas)} anomalías.")
            st.metric("Nivel de Riesgo", "ELEVADO", delta="Anomalía Detectada", delta_color="inverse")
        else:
            st.success("No se detectan anomalías estadísticas.")
            st.metric("Nivel de Riesgo", "NORMAL", delta="Estadísticamente Seguro")

    with col2:
        if not alertas.empty:
            st.dataframe(alertas.drop(columns=['anomaly_score'], errors='ignore'))
            
    st.header("📊 Visualización de Datos")
    if 'departamento' in data.columns:
        fig = px.bar(data, x='departamento', y='votos_totales', title="Votos por Departamento")
        st.plotly_chart(fig, use_container_width=True)

    with st.expander("🔍 Ver datos crudos"):
        st.dataframe(data)
else:
    st.warning("⏳ Esperando datos... GitHub Actions debe generar el primer snapshot.")

st.markdown("---")
st.caption("PROYECTO C.E.N.T.I.N.E.L. | Preparado para Elecciones 2029")
