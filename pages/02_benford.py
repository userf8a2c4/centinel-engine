import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from sentinel.dashboard.data_loader import (
    build_candidates_frame,
    build_totals_frame,
    latest_record,
    load_snapshot_records,
)

# -----------------------------------------------------------------------------
# Configuración básica de la página
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Ley de Benford - Sentinel", layout="wide")

st.title("Análisis de la Ley de Benford")
st.markdown(
    """
Esta vista permite analizar la distribución de los **dígitos iniciales** de diferentes campos numéricos
para compararlos con la **Ley de Benford** (distribución teórica esperada).
"""
)


@st.cache_data(ttl=600, show_spinner="Cargando snapshots...")
def get_records() -> list:
    return load_snapshot_records(max_files=150)


records = get_records()
latest = latest_record(records)

if not records or not latest:
    st.warning("No se encontraron snapshots con datos suficientes.")
    st.stop()

# -----------------------------------------------------------------------------
# Preparar datos
# -----------------------------------------------------------------------------

totals_df = build_totals_frame(records)
candidates_df = build_candidates_frame(records)

source_option = st.sidebar.selectbox(
    "Fuente de datos",
    (
        "Totales por snapshot",
        "Votos por candidato (último snapshot)",
        "Votos por candidato (todos los snapshots)",
    ),
)

if source_option == "Totales por snapshot":
    numeric_cols = [
        "registered_voters",
        "total_votes",
        "valid_votes",
        "null_votes",
        "blank_votes",
    ]
    selected_col = st.sidebar.selectbox("Columna numérica", numeric_cols)
    series = totals_df[selected_col]
    series_title = f"{selected_col} (totales)"
elif source_option == "Votos por candidato (último snapshot)":
    series = candidates_df[candidates_df["source_path"] == latest.source_path]["votes"]
    series_title = "votos por candidato (último snapshot)"
else:
    series = candidates_df["votes"]
    series_title = "votos por candidato (todos los snapshots)"

series = pd.to_numeric(series, errors="coerce")

if series.empty:
    st.error("No hay valores disponibles para el análisis seleccionado.")
    st.stop()

# -----------------------------------------------------------------------------
# Función para extraer primer dígito (ignora 0 y negativos)
# -----------------------------------------------------------------------------


def get_first_digit(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.replace(r"[-.]", "", regex=True).str.lstrip("0")
    return s.str[0].replace("", np.nan).astype(float)


# -----------------------------------------------------------------------------
# Cálculos
# -----------------------------------------------------------------------------
with st.spinner("Calculando distribución..."):
    first_digits = get_first_digit(series.dropna())
    first_digits = first_digits[first_digits.between(1, 9)]

    observed = first_digits.value_counts(normalize=True).sort_index()
    observed = observed.reindex(range(1, 10), fill_value=0)

    benford = np.log10(1 + 1 / np.arange(1, 10))
    benford = pd.Series(benford, index=range(1, 10))

# -----------------------------------------------------------------------------
# Visualización principal
# -----------------------------------------------------------------------------

col1, col2 = st.columns([3, 2])

with col1:
    fig, ax = plt.subplots(figsize=(10, 6))

    x = np.arange(1, 10)
    width = 0.35

    ax.bar(
        x - width / 2, observed, width, label="Observado", color="skyblue", alpha=0.8
    )
    ax.bar(
        x + width / 2,
        benford,
        width,
        label="Benford (teórico)",
        color="orange",
        alpha=0.7,
    )

    ax.set_xticks(x)
    ax.set_xticklabels([str(i) for i in x])
    ax.set_xlabel("Primer dígito")
    ax.set_ylabel("Proporción")
    ax.set_title(f"Ley de Benford - {series_title}")
    ax.legend()
    ax.grid(True, alpha=0.3, axis="y")

    st.pyplot(fig)

with col2:
    st.markdown("### Diferencias absolutas")
    diff = (observed - benford).abs()
    st.bar_chart(diff, color="#ff6b6b")

    st.markdown("### Métricas de desviación")
    mad = diff.mean()
    st.metric("Mean Absolute Deviation (MAD)", f"{mad:.4f}")

    if mad < 0.006:
        st.success("Conformidad alta con Benford")
    elif mad < 0.012:
        st.info("Conformidad aceptable")
    else:
        st.warning("Posible desviación significativa - revisar")

# Tabla comparativa
st.subheader("Tabla comparativa")
comparison = (
    pd.DataFrame(
        {
            "Dígito": range(1, 10),
            "Observado": observed.round(4),
            "Benford": benford.round(4),
            "Diferencia": (observed - benford).round(4),
        }
    )
    .set_index("Dígito")
    .style.format("{:.4f}")
)
st.dataframe(comparison)

st.markdown("---")
st.caption(
    "Análisis básico de Ley de Benford – Sentinel v3 • No sustituye auditoría completa"
)
