import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from sklearn.linear_model import LinearRegression
from sklearn.feature_extraction.text import TfidfVectorizer

from sentinel.dashboard.data_loader import (
    build_candidates_frame,
    build_totals_frame,
    latest_record,
    load_snapshot_records,
)

st.set_page_config(page_title="Predicciones y NLP - Sentinel", layout="wide")

st.title("Predicciones y análisis en lenguaje natural")
st.markdown(
    """
Esta sección genera **predicciones rápidas** sobre los totales de votos usando modelos simples de
machine learning y ofrece un **resumen en lenguaje natural** a partir del último snapshot.
"""
)


@st.cache_data(ttl=600, show_spinner="Cargando snapshots...")
def get_records() -> list:
    return load_snapshot_records(max_files=200)


records = get_records()
latest = latest_record(records)

if not records or not latest:
    st.warning("No se encontraron snapshots con datos suficientes.")
    st.stop()

# -----------------------------------------------------------------------------
# Preparación de datos
# -----------------------------------------------------------------------------

totals_df = build_totals_frame(records).sort_values("timestamp")
totals_df["timestamp"] = pd.to_datetime(totals_df["timestamp"])

candidates_df = build_candidates_frame(records)

if totals_df.shape[0] < 2:
    st.warning("Se necesitan al menos 2 snapshots para generar predicciones.")
    st.stop()

# -----------------------------------------------------------------------------
# Predicción de votos totales (ML)
# -----------------------------------------------------------------------------

st.subheader("Predicción de tendencia de votos")

base_time = totals_df["timestamp"].min()
totals_df["time_delta"] = (totals_df["timestamp"] - base_time).dt.total_seconds()

X = totals_df[["time_delta"]].values
y = totals_df["total_votes"].values

model = LinearRegression()
model.fit(X, y)

median_step = totals_df["time_delta"].diff().median()
if pd.isna(median_step) or median_step == 0:
    median_step = 3600

future_steps = st.slider(
    "Horizonte de predicción (pasos)", min_value=1, max_value=6, value=3
)
last_time = totals_df["time_delta"].iloc[-1]
future_times = np.array(
    [last_time + median_step * (i + 1) for i in range(future_steps)]
)
future_predictions = model.predict(future_times.reshape(-1, 1))

future_df = pd.DataFrame(
    {
        "timestamp": [
            base_time + pd.to_timedelta(seconds, unit="s") for seconds in future_times
        ],
        "total_votes": future_predictions,
        "Serie": "Predicción",
    }
)

history_df = totals_df[["timestamp", "total_votes"]].copy()
history_df["Serie"] = "Histórico"

plot_df = pd.concat([history_df, future_df], ignore_index=True)
fig = px.line(
    plot_df,
    x="timestamp",
    y="total_votes",
    color="Serie",
    markers=True,
    labels={"total_votes": "Votos totales"},
)
fig.update_layout(legend_title_text="Serie")

st.plotly_chart(fig, use_container_width=True)

col1, col2, col3 = st.columns(3)
col1.metric("Último total", f"{history_df['total_votes'].iloc[-1]:,.0f}")
col2.metric("Predicción próxima", f"{future_predictions[0]:,.0f}")
col3.metric("Pendiente estimada", f"{model.coef_[0]:,.2f} votos/seg")

# -----------------------------------------------------------------------------
# Resumen en lenguaje natural (NLP)
# -----------------------------------------------------------------------------

st.subheader("Resumen automático (NLP)")

latest_candidates = candidates_df[
    candidates_df["source_path"] == latest.source_path
].copy()
latest_candidates = latest_candidates.sort_values("votes", ascending=False)

if latest_candidates.empty:
    st.info("No hay información de candidatos para generar un resumen.")
    st.stop()

leader = latest_candidates.iloc[0]
runner_up = latest_candidates.iloc[1] if len(latest_candidates) > 1 else None
margin = leader["votes"] - (runner_up["votes"] if runner_up is not None else 0)

summary_lines = [
    f"En el último snapshot ({latest.timestamp:%Y-%m-%d %H:%M}), "
    f"lidera **{leader['candidate']}** con **{leader['votes']:,} votos**.",
]

if runner_up is not None:
    summary_lines.append(
        f"El segundo lugar es **{runner_up['candidate']}** con **{runner_up['votes']:,} votos** "
        f"(diferencia de **{margin:,}**)."
    )

summary_lines.append(
    "El modelo lineal sugiere que la tendencia sigue en crecimiento si se mantiene el ritmo actual."
)

st.markdown("\n".join(f"- {line}" for line in summary_lines))

# -----------------------------------------------------------------------------
# Extracción de temas (TF-IDF sobre nombres y partidos)
# -----------------------------------------------------------------------------

st.markdown("### Palabras clave detectadas")

text_corpus = (
    latest_candidates["candidate"].fillna("")
    + " "
    + latest_candidates["party"].fillna("")
).tolist()

vectorizer = TfidfVectorizer(stop_words=None)

tfidf = vectorizer.fit_transform(text_corpus)
feature_names = np.array(vectorizer.get_feature_names_out())

scores = np.asarray(tfidf.mean(axis=0)).ravel()
if scores.size:
    top_indices = scores.argsort()[::-1][:8]
    keywords = feature_names[top_indices]
    st.write(", ".join(str(word) for word in keywords))
else:
    st.write("No se pudieron extraer palabras clave.")

st.markdown("---")
st.caption("Predicciones rápidas basadas en regresión lineal y resumen automático NLP.")
