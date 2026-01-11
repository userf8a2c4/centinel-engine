"""
PROYECTO C.E.N.T.I.N.E.L. - Sistema de Auditoría Electoral Independiente
Versión: 3.2.0 (Neutralidad Técnica & IA)
"""

import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from sklearn.ensemble import IsolationForest

# --- Configuración de Entorno ---
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

def load_latest_data():
    """Carga el snapshot más reciente del repositorio"""
    if not DATA_DIR.exists():
        return None
    files = list(DATA_DIR.glob("snapshot_*.json"))
    if not files:
        return None
    latest_file = max(files, key=os.path.getctime)
    try:
        return pd.read_json(latest_file)
    except Exception:
        return None

def perform_ai_audit(df):
    """
    Detección de anomalías mediante Machine Learning (Isolation Forest).
    Analiza si la relación entre participación y votos totales es natural.
    """
    if df is None or len(df) < 5:
        return df, 100
    
    # Columnas base para análisis de integridad
    metrics = ['porcentaje_escrutado', 'votos_totales']
    existing = [m for m in metrics if m in df.columns]
    
    if len(existing) < 2:
        return df, 100

    # Entrenamiento del modelo de IA (Detección de Outliers)
    model = IsolationForest(contamination=0.03, random_state=42)
    df['anomaly_flag'] = model.fit_predict(df[existing].fillna(0))
    
    # Cálculo del Índice de Integridad (0-100)
    outliers = (df['anomaly_flag'] == -1).sum()
    integrity_score = max(0, 100 - (outliers / len(df) * 100))
    return df, integrity_score

# --- Interfaz de Usuario Neutral ---
st.set_page_config(page_title="SENTINEL - Auditoría Electoral", layout="wide")

st.markdown("""
    <h1 style='text-align: center;'>🛡️ C.E.N.T.I.N.E.L.</h1>
    <p style='text-align: center;'>Vigilancia Estadística de Datos Públicos en Tiempo Real</p>
    <hr>
""", unsafe_allow_html=True)

data = load_latest_data()

if data is not None:
    # 1. Proceso de Auditoría IA
    data, integrity_index = perform_ai_audit(data)
    
    # 2. Identificación Dinámica de Candidatos (Sin nombres fijos)
    # Buscamos columnas que contengan 'votos_' para identificar candidatos
    candidate_cols = [c for c in data.columns if c.startswith('votos_') and c != 'votos_totales']
    
    # 3. Métricas Principales
    m1, m2, m3 = st.columns(3)
    
    with m1:
        st.metric("Índice de Integridad Estadística", f"{int(integrity_index)}%", 
                  help="Basado en la detección de anomalías por Machine Learning")
    
    with m2:
        progreso_medio = data['porcentaje_escrutado'].mean() if 'porcentaje_escrutado' in data.columns else 0
        st.metric("Progreso del Escrutinio", f"{progreso_medio:.2f}%")

    if candidate_cols:
        # Sumar votos totales por candidato en este snapshot
        votos_por_candidato = data[candidate_cols].sum().sort_values(ascending=False)
        top_1 = votos_por_candidato.index[0]
        top_2 = votos_por_candidato.index[1] if len(votos_por_candidato) > 1 else None
        
        ventaja_absoluta = votos_por_candidato[0] - (votos_por_candidato[1] if top_2 else 0)
        
        with m3:
            # Determinación de irreversibilidad basada en margen y actas pendientes
            es_irreversible = progreso_medio > 80 and (ventaja_absoluta > (data['votos_totales'].sum() * 0.05))
            st.metric("Estado de la Tendencia", "IRREVERSIBLE" if es_irreversible else "EN EVOLUCIÓN")

        # 4. Análisis Visual
        st.header(" Comparativa de Liderazgo (Top Candidatos)")
        fig_bars = px.bar(
            x=[c.replace('votos_', '').upper() for c in votos_por_candidato.index],
            y=votos_por_candidato.values,
            labels={'x': 'Candidato', 'y': 'Votos'},
            color_discrete_sequence=['#00CC96']
        )
        st.plotly_chart(fig_bars, use_container_width=True)

    # 5. Sección de Alertas (Audit Log)
    st.header("🔍 Hallazgos de Auditoría (IA)")
    anomalias = data[data['anomaly_flag'] == -1]
    
    if not anomalias.empty:
        st.warning(f" Atención: Se han detectado {len(anomalias)} registros con comportamiento estadísticamente atípico.")
        st.dataframe(anomalias.drop(columns=['anomaly_flag']))
    else:
        st.success(" No se detectan patrones de manipulación en los datos públicos procesados.")

else:
    st.info("📡 Sincronizando datos... El motor C.E.N.T.I.N.E.L. está procesando los snapshots de GitHub Actions.")

st.markdown("---")
st.caption(f"Protocolo de Auditoría C.E.N.T.I.N.E.L. | Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
