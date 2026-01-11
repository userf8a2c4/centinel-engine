import streamlit as st
import pandas as pd
import os
from pathlib import Path
from sklearn.ensemble import IsolationForest
from datetime import datetime

# --- Configuración de Rutas ---
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

def load_latest_data():
    """Carga datos de forma segura sin importar el nombre de las columnas"""
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

def detect_anomalies(df):
    """Análisis de IA agnóstico: solo busca saltos numéricos sospechosos"""
    # Buscamos columnas numéricas automáticamente para no depender de nombres fijos
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    if len(numeric_cols) < 2:
        return pd.DataFrame(), 100
    
    model = IsolationForest(contamination=0.05, random_state=42)
    # Usamos las primeras dos columnas numéricas que encuentre (usualmente votos y progreso)
    df['anomaly_score'] = model.fit_predict(df[numeric_cols[:2]].fillna(0))
    
    anomalias = (df['anomaly_score'] == -1).sum()
    score = max(0, 100 - (anomalias / len(df) * 100))
    return df[df['anomaly_score'] == -1], score

# --- Interfaz ---
st.set_page_config(page_title="C.E.N.T.I.N.E.L. Audit", layout="wide")

st.markdown("<h1 style='text-align: center;'>Proyecto C.E.N.T.I.N.E.L.</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center;'>Vigilancia Estadística en Tiempo Real</p>", unsafe_allow_html=True)

data = load_latest_data()

if data is not None:
    # Ejecutar IA de forma imparcial
    alertas, integridad = detect_anomalies(data)
    
    # Métricas de Integridad
    c1, c2 = st.columns(2)
    with c1:
        st.metric("Índice de Integridad Estadística", f"{int(integridad)}%")
    with c2:
        status = "ESTABLE" if integridad > 90 else "BAJO REVISIÓN"
        st.metric("Estado del Sistema", status)

    # Visualización Automática de Candidatos
    # Identifica columnas de votos (votos_...) para graficar sin nombres grabados
    candidatos = [c for c in data.columns if 'votos' in c.lower() and c.lower() != 'votos_totales']
    
    if candidatos:
        st.subheader("Análisis de Tendencias (Datos Públicos)")
        votos_totales = data[candidatos].sum().sort_values(ascending=False)
        st.bar_chart(votos_totales)

    if not alertas.empty:
        st.header("🔍 Registro de Anomalías Detectadas")
        st.warning("La IA detectó patrones fuera de la norma estadística en los siguientes registros:")
        st.dataframe(alertas.drop(columns=['anomaly_score'], errors='ignore'))
    else:
        st.success("✅ No se detectan anomalías estadísticas en los datos públicos actuales.")
else:
    st.info("📡 Sincronizando... Esperando que el motor de GitHub genere el primer snapshot de datos.")

st.markdown("---")
st.caption(f"C.E.N.T.I.N.E.L. | Protocolo de Neutralidad Técnica | {datetime.now().year}")
