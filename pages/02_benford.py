import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# -----------------------------------------------------------------------------
# Configuración básica de la página
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Ley de Benford - Sentinel", layout="wide")

st.title("Análisis de la Ley de Benford")
st.markdown("""
Esta vista permite analizar la distribución de los **dígitos iniciales** de diferentes campos numéricos 
de los datos electorales y compararlos con la **Ley de Benford** (distribución teórica esperada).
""")

# -----------------------------------------------------------------------------
# Rutas y carga de datos (ajusta según tu estructura real)
# -----------------------------------------------------------------------------
DATA_FOLDER = Path("data/processed")           # ejemplo - cámbialo a donde estén tus datos
AVAILABLE_FILES = list(DATA_FOLDER.glob("*.parquet")) + list(DATA_FOLDER.glob("*.csv"))

if not AVAILABLE_FILES:
    st.warning("No se encontraron archivos procesados en data/processed/")
    st.stop()

# Selección de archivo
file_options = [f.name for f in AVAILABLE_FILES]
selected_file = st.sidebar.selectbox("Archivo de datos a analizar", file_options)

# Cargar datos
@st.cache_data
def load_data(file_path: Path):
    if file_path.suffix == ".parquet":
        return pd.read_parquet(file_path)
    else:
        return pd.read_csv(file_path)

df = load_data(DATA_FOLDER / selected_file)
st.sidebar.success(f"Datos cargados: {len(df):,} filas")

# -----------------------------------------------------------------------------
# Selección de columna numérica
# -----------------------------------------------------------------------------
numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

if not numeric_cols:
    st.error("No se encontraron columnas numéricas en el dataset seleccionado.")
    st.stop()

selected_col = st.sidebar.selectbox("Columna numérica para analizar", numeric_cols)

# -----------------------------------------------------------------------------
# Función para extraer primer dígito (ignora 0 y negativos)
# -----------------------------------------------------------------------------
def get_first_digit(series: pd.Series) -> pd.Series:
    # Convertir a string, quitar signo y ceros iniciales
    s = series.astype(str).str.replace(r'[-.]', '', regex=True).str.lstrip('0')
    # Primer carácter (debería ser 1-9)
    return s.str[0].replace('', np.nan).astype(float)

# -----------------------------------------------------------------------------
# Cálculos
# -----------------------------------------------------------------------------
with st.spinner("Calculando distribución..."):
    first_digits = get_first_digit(df[selected_col].dropna())
    first_digits = first_digits[first_digits.between(1, 9)]  # solo 1-9
    
    observed = first_digits.value_counts(normalize=True).sort_index()
    observed = observed.reindex(range(1,10), fill_value=0)  # asegurar todos
    
    # Distribución teórica de Benford
    benford = np.log10(1 + 1/np.arange(1,10))
    benford = pd.Series(benford, index=range(1,10))

# -----------------------------------------------------------------------------
# Visualización principal
# -----------------------------------------------------------------------------
col1, col2 = st.columns([3, 2])

with col1:
    fig, ax = plt.subplots(figsize=(10, 6))
    
    x = np.arange(1,10)
    width = 0.35
    
    ax.bar(x - width/2, observed, width, label='Observado', color='skyblue', alpha=0.8)
    ax.bar(x + width/2, benford, width, label='Benford (teórico)', color='orange', alpha=0.7)
    
    ax.set_xticks(x)
    ax.set_xticklabels([str(i) for i in x])
    ax.set_xlabel("Primer dígito")
    ax.set_ylabel("Proporción")
    ax.set_title(f"Ley de Benford - {selected_col} ({selected_file})")
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    st.pyplot(fig)

with col2:
    st.markdown("### Diferencias absolutas")
    diff = (observed - benford).abs()
    st.bar_chart(diff, color="#ff6b6b")
    
    st.markdown("### Métricas de desviación")
    mad = diff.mean()
    st.metric("Mean Absolute Deviation (MAD)", f"{mad:.4f}")
    
    # Interpretación rápida
    if mad < 0.006:
        st.success("Conformidad alta con Benford")
    elif mad < 0.012:
        st.info("Conformidad aceptable")
    else:
        st.warning("Posible desviación significativa - revisar")

# Tabla comparativa
st.subheader("Tabla comparativa")
comparison = pd.DataFrame({
    "Dígito": range(1,10),
    "Observado": observed.round(4),
    "Benford": benford.round(4),
    "Diferencia": (observed - benford).round(4)
}).set_index("Dígito")
st.dataframe(comparison.style.format("{:.4f}"))

st.markdown("---")
st.caption("Análisis básico de Ley de Benford – Sentinel v3 • No sustituye auditoría completa")
