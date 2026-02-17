"""Laboratorio de Reglas – Reproducción de datos 2025 con parámetros ajustables.

Permite reproducir la secuencia temporal de snapshots históricos 2025, controlar
la velocidad de reproducción, y ajustar en vivo los umbrales de cada regla para
observar cómo cambian las alertas generadas.

Diseñado para que matemáticos e investigadores de la UPNFM puedan experimentar
con los valores y validar el comportamiento del motor de detección.

---

Rules Laboratory – 2025 data replay with adjustable parameters.

Replays the historical 2025 snapshot timeline, allows speed control and live
rule threshold adjustment. Designed for UPNFM mathematicians to experiment
with detection engine parameters.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import time
import copy
from datetime import datetime, timedelta

from sentinel.dashboard.sandbox_engine import (
    DEFAULT_RULE_PARAMS,
    RULE_MODULES,
    build_replay_dataframe,
    load_historical_snapshots,
    rule_format_to_df_row,
    run_rules_sandbox,
    snapshot_to_rule_format,
    _short_party_name,
)
from sentinel.dashboard.utils.benford import benford_analysis

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Laboratorio de Reglas - Sentinel",
    page_icon="🔬",
    layout="wide",
)

# Persistent sandbox banner
st.markdown(
    """
    <div style="background-color:#1f77b422;border:2px solid #1f77b4;border-radius:8px;
    padding:8px 16px;margin-bottom:16px;text-align:center;">
    <strong>MODO LABORATORIO</strong> — Reproducción de datos históricos. No afecta producción.
    </div>
    """,
    unsafe_allow_html=True,
)

st.title("Laboratorio de Reglas")
st.markdown(
    "Reproduce la secuencia de snapshots 2025 del CNE y ajusta en tiempo real "
    "los umbrales de cada regla para observar el comportamiento del motor de detección."
)


# ---------------------------------------------------------------------------
# Load historical data
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600, show_spinner="Cargando snapshots históricos 2025...")
def _load_snapshots():
    return load_historical_snapshots()


snapshots = _load_snapshots()

if not snapshots:
    st.error(
        "No se encontraron snapshots en data/2025/. "
        "Asegúrate de que la carpeta existe y contiene archivos JSON."
    )
    st.stop()

# ---------------------------------------------------------------------------
# Sidebar – Rule parameter sliders & replay controls
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("Control de Reproducción")

    # Replay range
    st.subheader("Rango de snapshots")
    total_snaps = len(snapshots)
    snap_range = st.slider(
        "Snapshots a reproducir",
        1,
        total_snaps,
        (1, total_snaps),
        key="snap_range",
    )
    start_idx = snap_range[0] - 1
    end_idx = snap_range[1]

    # Replay speed
    replay_speed = st.select_slider(
        "Velocidad de reproducción",
        options=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0],
        value=1.0,
        format_func=lambda x: f"{x}x",
        key="replay_speed",
    )

    st.markdown("---")
    st.header("Parámetros de Reglas")
    st.caption("Ajusta los umbrales y observa el efecto en las alertas.")

    # Rule parameter sliders
    rule_configs: dict[str, dict] = {}

    # Benford
    with st.expander("Ley de Benford", expanded=False):
        rule_configs["benford_law"] = {
            "chi_square_threshold": st.slider(
                "Chi² p-value umbral",
                0.001, 0.20, 0.05, step=0.005,
                key="bf_chi",
                help="Valores más bajos = más estricto",
            ),
            "deviation_pct": st.slider(
                "Desviación máx. (%)",
                1.0, 50.0, 15.0, step=1.0,
                key="bf_dev",
            ),
            "min_samples": st.slider(
                "Muestras mínimas",
                2, 50, 10, key="bf_min",
            ),
        }

    # Basic diff
    with st.expander("Diferencia Básica", expanded=False):
        rule_configs["basic_diff"] = {
            "relative_vote_change_pct": st.slider(
                "Cambio relativo máx. (%)",
                1.0, 50.0, 15.0, step=1.0,
                key="bd_pct",
            ),
        }

    # Trend shift
    with st.expander("Desviación de Tendencia", expanded=False):
        rule_configs["trend_shift"] = {
            "threshold_percent": st.slider(
                "Umbral de desviación (%)",
                1.0, 30.0, 10.0, step=0.5,
                key="ts_pct",
            ),
            "max_hours": st.slider(
                "Ventana máxima (horas)",
                0.5, 12.0, 3.0, step=0.5,
                key="ts_hrs",
            ),
        }

    # Processing speed
    with st.expander("Velocidad de Procesamiento", expanded=False):
        rule_configs["processing_speed"] = {
            "max_actas_per_15min": st.slider(
                "Máx. actas por 15 min",
                50, 2000, 500, step=50,
                key="ps_actas",
            ),
        }

    # Participation anomaly
    with st.expander("Anomalía de Participación", expanded=False):
        rule_configs["participation_anomaly"] = {
            "scrutiny_jump_pct": st.slider(
                "Salto escrutinio (%)",
                0.5, 20.0, 5.0, step=0.5,
                key="pa_jump",
            ),
        }

    # ML outliers
    with st.expander("Outliers ML", expanded=False):
        rule_configs["ml_outliers"] = {
            "contamination": st.slider(
                "Contaminación (Isolation Forest)",
                0.01, 0.50, 0.10, step=0.01,
                key="ml_cont",
            ),
            "min_samples": st.slider(
                "Muestras mínimas",
                2, 20, 5, key="ml_min",
            ),
        }

    st.markdown("---")
    # Rules to enable/disable
    st.subheader("Reglas activas")
    enabled_rules = []
    for rule_name, module_path in RULE_MODULES.items():
        if st.checkbox(rule_name, value=True, key=f"en_{rule_name}"):
            enabled_rules.append(rule_name)


# ---------------------------------------------------------------------------
# Process all snapshots with current rule config
# ---------------------------------------------------------------------------

selected_snapshots = snapshots[start_idx:end_idx]

# Convert to rule format
rule_data_list = [
    snapshot_to_rule_format(s["payload"], s["timestamp"])
    for s in selected_snapshots
]

# Run rules on each consecutive pair
all_alerts_timeline: list[dict] = []
alerts_per_snapshot: list[int] = []
severity_per_snapshot: list[dict] = []

for i, current in enumerate(rule_data_list):
    previous = rule_data_list[i - 1] if i > 0 else None
    alerts = run_rules_sandbox(current, previous, rule_configs, enabled_rules)
    for alert in alerts:
        alert["snapshot_idx"] = i
        alert["timestamp"] = current.get("timestamp", "")
    all_alerts_timeline.extend(alerts)
    alerts_per_snapshot.append(len(alerts))

    sev_counts = {"High": 0, "Medium": 0, "Low": 0}
    for a in alerts:
        sev = a.get("severity", "Low")
        sev_counts[sev] = sev_counts.get(sev, 0) + 1
    severity_per_snapshot.append(sev_counts)

# Build display DataFrame
replay_df = build_replay_dataframe(selected_snapshots)

# ---------------------------------------------------------------------------
# Main display area
# ---------------------------------------------------------------------------

# Summary metrics
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Snapshots analizados", len(selected_snapshots))

with col2:
    st.metric("Total alertas", len(all_alerts_timeline))

with col3:
    high_total = sum(s["High"] for s in severity_per_snapshot)
    st.metric("Alertas Alta Severidad", high_total)

with col4:
    st.metric("Reglas activas", len(enabled_rules))

st.markdown("---")

# Tabs
tab_timeline, tab_alerts, tab_benford, tab_explorer = st.tabs([
    "Evolución Temporal",
    "Línea de Alertas",
    "Análisis Benford",
    "Explorador de Snapshots",
])

with tab_timeline:
    st.subheader("Evolución de votos por partido")

    if not replay_df.empty:
        # Detect party columns (non-standard columns)
        base_cols = {"timestamp", "departamento", "total_votos", "actas_divulgadas",
                     "actas_totales", "votos_validos", "votos_nulos", "votos_blancos", "hash"}
        party_cols = [c for c in replay_df.columns if c not in base_cols]

        if party_cols:
            melted = replay_df.melt(
                id_vars="timestamp",
                value_vars=party_cols,
                var_name="Partido",
                value_name="Votos",
            )
            fig_votes = px.line(
                melted,
                x="timestamp",
                y="Votos",
                color="Partido",
                title="Evolución temporal de votos (datos reales 2025)",
                markers=True,
            )
            st.plotly_chart(fig_votes, use_container_width=True)

        # Actas timeline
        if "actas_divulgadas" in replay_df.columns:
            fig_actas = px.line(
                replay_df,
                x="timestamp",
                y="actas_divulgadas",
                title="Actas divulgadas en el tiempo",
                markers=True,
            )
            if "actas_totales" in replay_df.columns:
                fig_actas.add_hline(
                    y=replay_df["actas_totales"].max(),
                    line_dash="dash",
                    line_color="red",
                    annotation_text="Total actas",
                )
            st.plotly_chart(fig_actas, use_container_width=True)

        # Scrutiny percentage
        if "actas_divulgadas" in replay_df.columns and "actas_totales" in replay_df.columns:
            replay_df["pct_escrutado"] = (
                replay_df["actas_divulgadas"] / replay_df["actas_totales"].replace(0, 1) * 100
            )
            fig_pct = px.area(
                replay_df,
                x="timestamp",
                y="pct_escrutado",
                title="% Escrutado en el tiempo",
            )
            fig_pct.update_yaxes(range=[0, 105])
            st.plotly_chart(fig_pct, use_container_width=True)
    else:
        st.info("No hay datos para visualizar.")

with tab_alerts:
    st.subheader("Línea temporal de alertas")

    if all_alerts_timeline:
        # Alerts per snapshot bar chart
        alert_timeline_df = pd.DataFrame({
            "Snapshot": range(len(alerts_per_snapshot)),
            "Timestamp": [s["timestamp"].strftime("%m-%d %H:%M") for s in selected_snapshots],
            "Alertas": alerts_per_snapshot,
            "High": [s["High"] for s in severity_per_snapshot],
            "Medium": [s["Medium"] for s in severity_per_snapshot],
            "Low": [s["Low"] for s in severity_per_snapshot],
        })

        fig_alert_bar = go.Figure()
        fig_alert_bar.add_trace(go.Bar(
            x=alert_timeline_df["Timestamp"],
            y=alert_timeline_df["High"],
            name="Alta",
            marker_color="#EF553B",
        ))
        fig_alert_bar.add_trace(go.Bar(
            x=alert_timeline_df["Timestamp"],
            y=alert_timeline_df["Medium"],
            name="Media",
            marker_color="#FFA15A",
        ))
        fig_alert_bar.add_trace(go.Bar(
            x=alert_timeline_df["Timestamp"],
            y=alert_timeline_df["Low"],
            name="Baja",
            marker_color="#00CC96",
        ))
        fig_alert_bar.update_layout(
            barmode="stack",
            title="Alertas por snapshot (apiladas por severidad)",
            xaxis_title="Timestamp",
            yaxis_title="Alertas",
        )
        st.plotly_chart(fig_alert_bar, use_container_width=True)

        # Alerts by rule
        alerts_df = pd.DataFrame(all_alerts_timeline)
        if "rule" in alerts_df.columns:
            rule_counts = alerts_df.groupby("rule").size().reset_index(name="count")
            fig_rule = px.bar(
                rule_counts.sort_values("count", ascending=True),
                x="count",
                y="rule",
                orientation="h",
                title="Alertas por regla",
                color="count",
                color_continuous_scale="Reds",
            )
            st.plotly_chart(fig_rule, use_container_width=True)

        # Full alert table
        st.subheader("Tabla completa de alertas")
        display_cols = ["timestamp", "rule", "severity", "type", "department", "justification"]
        available_cols = [c for c in display_cols if c in alerts_df.columns]
        st.dataframe(
            alerts_df[available_cols].sort_values(
                ["timestamp", "severity"],
                ascending=[True, True],
            ),
            use_container_width=True,
            height=400,
        )
    else:
        st.success(
            "Sin alertas en todo el rango reproducido. "
            "Prueba ajustar umbrales más estrictos para ver alertas."
        )

with tab_benford:
    st.subheader("Análisis de Benford sobre datos reproducidos")

    if not replay_df.empty and "total_votos" in replay_df.columns:
        observed, theoretical, deviation = benford_analysis(replay_df["total_votos"])

        if observed is not None and theoretical is not None:
            fig_benford = go.Figure()
            fig_benford.add_trace(go.Bar(
                x=list(range(1, 10)),
                y=observed,
                name="Observado",
                marker_color="#636EFA",
            ))
            fig_benford.add_trace(go.Scatter(
                x=list(range(1, 10)),
                y=theoretical,
                mode="lines+markers",
                name="Benford teórico",
                line=dict(color="#EF553B", width=2),
            ))
            fig_benford.update_layout(
                title=f"Ley de Benford — Desviación media: {deviation:.2f}%",
                xaxis_title="Primer dígito",
                yaxis_title="Proporción",
            )
            st.plotly_chart(fig_benford, use_container_width=True)

            chi_threshold = rule_configs.get("benford_law", {}).get("chi_square_threshold", 0.05)
            if deviation > rule_configs.get("benford_law", {}).get("deviation_pct", 15):
                st.error(f"Desviación ({deviation:.2f}%) supera el umbral configurado.")
            else:
                st.success(f"Desviación ({deviation:.2f}%) dentro del umbral.")
        else:
            st.info("Datos insuficientes para análisis de Benford.")

        # Per-party Benford analysis
        base_cols = {"timestamp", "departamento", "total_votos", "actas_divulgadas",
                     "actas_totales", "votos_validos", "votos_nulos", "votos_blancos", "hash"}
        party_cols = [c for c in replay_df.columns if c not in base_cols and c != "pct_escrutado"]

        if party_cols:
            st.subheader("Benford por partido")
            for party in party_cols:
                series = replay_df[party].dropna()
                if len(series) < 20:
                    continue
                obs_p, theo_p, dev_p = benford_analysis(series)
                if obs_p is not None:
                    st.markdown(f"**{party}** — Desviación: {dev_p:.2f}%")
    else:
        st.info("No hay datos disponibles.")

with tab_explorer:
    st.subheader("Explorador de snapshots individuales")

    if selected_snapshots:
        explorer_idx = st.slider(
            "Seleccionar snapshot",
            0,
            len(selected_snapshots) - 1,
            0,
            format_func=lambda i: selected_snapshots[i]["timestamp"].strftime("%Y-%m-%d %H:%M"),
            key="explorer_slider",
        )

        snap = selected_snapshots[explorer_idx]
        rule_data = snapshot_to_rule_format(snap["payload"], snap["timestamp"])
        prev_data = (
            snapshot_to_rule_format(
                selected_snapshots[explorer_idx - 1]["payload"],
                selected_snapshots[explorer_idx - 1]["timestamp"],
            )
            if explorer_idx > 0
            else None
        )

        # Run rules on this specific snapshot
        snap_alerts = run_rules_sandbox(rule_data, prev_data, rule_configs, enabled_rules)

        col1, col2 = st.columns([2, 1])

        with col1:
            st.markdown(f"**Timestamp:** {snap['timestamp']}")
            st.markdown(f"**Archivo:** `{snap['filename']}`")

            candidates = rule_data.get("candidatos", [])
            if candidates:
                cand_df = pd.DataFrame([
                    {
                        "Candidato": c.get("name", "")[:50],
                        "Partido": c.get("party", "")[:30],
                        "Votos": c.get("votes", 0),
                    }
                    for c in candidates
                ])
                st.dataframe(
                    cand_df.style.format({"Votos": "{:,}"}),
                    use_container_width=True,
                )

        with col2:
            st.markdown(f"**Alertas en este snapshot:** {len(snap_alerts)}")
            for alert in snap_alerts:
                severity = alert.get("severity", "Low")
                icon = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(severity, "⚪")
                st.markdown(
                    f"{icon} **{alert.get('type', '')}** ({alert.get('rule', '')})"
                )

        # Raw JSON
        with st.expander("JSON crudo del snapshot"):
            st.json(snap["payload"])

        with st.expander("Formato de reglas (normalizado)"):
            st.json(rule_data)

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown("---")
st.caption(
    "Laboratorio de Reglas — Sentinel v4 | "
    "Todos los análisis son sobre datos históricos 2025 en modo sandbox."
)
