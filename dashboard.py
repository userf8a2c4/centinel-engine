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
    cols_interes = ["porcentaje_escrutado", "votos_totales"]
    existentes = [c for c in cols_interes if c in df.columns]

    if len(existentes) < 2:
        return pd.DataFrame()

    features = df[existentes].fillna(0)
    model = IsolationForest(contamination=0.05, random_state=42)
    df["anomaly_score"] = model.fit_predict(features)

    return df[df["anomaly_score"] == -1]


# --- Interfaz ---
st.set_page_config(page_title="C.E.N.T.I.N.E.L. Audit", layout="wide")

st.markdown(
    """
    <h1 style='text-align: center;'>Proyecto C.E.N.T.I.N.E.L.</h1>
    <p style='text-align: center;'>Auditoría Ciudadana Independiente - Honduras 2028/2029</p>
    <hr>
""",
    unsafe_allow_html=True,
)

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
            st.metric(
                "Nivel de Riesgo",
                "ELEVADO",
                delta="Anomalía Detectada",
                delta_color="inverse",
            )
        else:
            st.success("No se detectan anomalías estadísticas.")
            st.metric("Nivel de Riesgo", "NORMAL", delta="Estadísticamente Seguro")

    with col2:
        if not alertas.empty:
            st.dataframe(alertas.drop(columns=["anomaly_score"], errors="ignore"))

    st.header("📊 Visualización de Datos")
    if "departamento" in data.columns:
        fig = px.bar(
            data, x="departamento", y="votos_totales", title="Votos por Departamento"
        )
        st.plotly_chart(fig, use_container_width=True)

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
