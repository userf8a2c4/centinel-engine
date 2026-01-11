# dashboard.py
import streamlit as st
import json
import os
from datetime import datetime
import requests
from pathlib import Path
import pandas as pd

# ──────────────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN BÁSICA
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Centinel - Dashboard",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📡 Centinel Dashboard")
st.markdown("Visualización automática de snapshots generados desde GitHub")

# Configuración del repositorio (ajústalas si cambian)
REPO_OWNER = "userf8a2c4"
REPO_NAME = "sentinel"
BRANCH = "dev-v3"
SNAPSHOTS_DIR = "data/snapshots"  # ← muy importante: debe coincidir con tu workflow

GITHUB_RAW_BASE = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/{BRANCH}/{SNAPSHOTS_DIR}"

# ──────────────────────────────────────────────────────────────────────────────
# FUNCIONES AUXILIARES
# ──────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl="10min", show_spinner="Buscando snapshot más reciente...")
def get_latest_snapshot():
    try:
        # Opción 1: Intentamos obtener la lista de archivos vía GitHub API (más confiable)
        api_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/git/trees/{BRANCH}?recursive=1"
        headers = {"Accept": "application/vnd.github.v3+json"}
        
        # Si tienes token → puedes descomentar y usar
        # headers["Authorization"] = f"token {st.secrets.get('GITHUB_TOKEN', '')}"

        response = requests.get(api_url, headers=headers, timeout=15)
        response.raise_for_status()

        data = response.json()
        files = [item["path"] for item in data.get("tree", [])
                 if item["path"].startswith(f"{SNAPSHOTS_DIR}/") and item["path"].endswith(".json")]

        if not files:
            return None, "No se encontraron archivos .json en la carpeta de snapshots"

        # Tomamos el último (por convención los nombres tienen fecha descendente)
        latest_path = sorted(files)[-1]
        filename = Path(latest_path).name

        # Descargamos el contenido
        raw_url = f"{GITHUB_RAW_BASE}/{filename}"
        resp = requests.get(raw_url, timeout=12)
        resp.raise_for_status()

        content = json.loads(resp.text)
        return content, f"✓ Snapshot cargado: {filename}"

    except requests.exceptions.RequestException as e:
        return None, f"Error de conexión/red → {str(e)}"
    except json.JSONDecodeError:
        return None, f"El archivo JSON está mal formado"
    except Exception as e:
        return None, f"Error inesperado: {str(e)}"


# ──────────────────────────────────────────────────────────────────────────────
# INTERFAZ PRINCIPAL
# ──────────────────────────────────────────────────────────────────────────────
data, status_message = get_latest_snapshot()

if data is None:
    st.error("**No se pudo cargar ningún snapshot**")
    st.warning(status_message)
    st.info("📡 Sincronizando... Esperando que el motor de GitHub genere el primer snapshot de datos.")
    st.caption("Última comprobación: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
else:
    st.success(status_message)
    st.caption("Última comprobación: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    # Aquí pones tu visualización real
    # Ejemplo básico (adapta a tu estructura de datos real)
    st.subheader("Últimos datos disponibles")

    try:
        # Suponiendo que tu JSON tiene una clave "data" o "results"
        df = pd.DataFrame(data.get("results", data.get("data", [])))
        if not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Los datos están vacíos o no tienen formato de tabla")
            st.json(data)
    except Exception as e:
        st.error(f"No se pudo convertir a tabla: {e}")
        st.json(data)  # fallback

st.markdown("---")
st.caption("Powered by Streamlit • Datos desde GitHub • Actualización automática")
