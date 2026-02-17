"""Panel de Caos – Inyección de anomalías y visualización en vivo de alertas.

Permite inyectar distintos tipos de anomalías sobre un snapshot base (real o simulado)
y ver en tiempo real qué reglas se activan, con qué severidad y justificación.

Todo opera en memoria (sandbox). No toca producción.

---

Chaos Panel – Anomaly injection and live alert visualization.

Injects anomalies into a base snapshot and shows which rules fire in real time.
Fully in-memory sandbox. Does not touch production.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import copy
from datetime import datetime, timedelta

from sentinel.dashboard.sandbox_engine import (
    CHAOS_INJECTIONS,
    DEFAULT_RULE_PARAMS,
    RULE_MODULES,
    build_replay_dataframe,
    inject_acta_speed_anomaly,
    inject_arithmetic_mismatch,
    inject_benford_violation,
    inject_scrutiny_jump,
    inject_vote_regression,
    inject_vote_spike,
    load_historical_snapshots,
    rule_format_to_df_row,
    run_rules_sandbox,
    snapshot_to_rule_format,
)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Panel de Caos - Sentinel",
    page_icon="🧪",
    layout="wide",
)

# Persistent sandbox banner
st.markdown(
    """
    <div style="background-color:#ff4b4b22;border:2px solid #ff4b4b;border-radius:8px;
    padding:8px 16px;margin-bottom:16px;text-align:center;">
    <strong>MODO SANDBOX</strong> — Datos en memoria. No afecta producción.
    </div>
    """,
    unsafe_allow_html=True,
)

st.title("Panel de Caos")
st.markdown(
    "Inyecta anomalías controladas sobre snapshots reales de 2025 y observa "
    "en vivo qué reglas del motor de detección se activan."
)

# ---------------------------------------------------------------------------
# Load base data
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
# Sidebar – Snapshot selection & injection config
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("Configuración de Caos")

    # Select base snapshot
    snapshot_labels = [
        f"{s['timestamp'].strftime('%Y-%m-%d %H:%M')} ({i+1}/{len(snapshots)})"
        for i, s in enumerate(snapshots)
    ]
    selected_idx = st.selectbox(
        "Snapshot base",
        range(len(snapshots)),
        format_func=lambda i: snapshot_labels[i],
        index=len(snapshots) // 2,
    )

    st.markdown("---")
    st.subheader("Inyecciones activas")

    # Injection toggles
    active_injections: dict[str, dict] = {}

    # 1. Vote spike
    if st.checkbox("Pico de votos", value=False, key="chk_spike"):
        col1, col2 = st.columns(2)
        with col1:
            spike_candidate = st.number_input(
                "Candidato (índice)", 0, 4, 0, key="spike_cand"
            )
        with col2:
            spike_amount = st.number_input(
                "Votos extra", 1000, 5_000_000, 500_000, step=50_000, key="spike_amt"
            )
        active_injections["spike_votos"] = {
            "candidate_idx": spike_candidate,
            "extra_votes": spike_amount,
        }

    # 2. Arithmetic mismatch
    if st.checkbox("Descuadre aritmético", value=False, key="chk_arith"):
        offset = st.number_input(
            "Offset total", -500_000, 500_000, 50_000, step=10_000, key="arith_off"
        )
        active_injections["descuadre_aritmetico"] = {"offset": offset}

    # 3. Vote regression
    if st.checkbox("Regresión de votos", value=False, key="chk_regr"):
        col1, col2 = st.columns(2)
        with col1:
            regr_candidate = st.number_input(
                "Candidato (índice)", 0, 4, 0, key="regr_cand"
            )
        with col2:
            regr_amount = st.number_input(
                "Reducción", 1000, 2_000_000, 100_000, step=10_000, key="regr_amt"
            )
        active_injections["regresion_votos"] = {
            "candidate_idx": regr_candidate,
            "reduction": regr_amount,
        }

    # 4. Acta speed anomaly
    if st.checkbox("Velocidad anómala de actas", value=False, key="chk_speed"):
        extra_actas = st.number_input(
            "Actas extra", 100, 10_000, 3_000, step=500, key="speed_actas"
        )
        active_injections["velocidad_actas"] = {"extra_actas": extra_actas}

    # 5. Scrutiny jump
    if st.checkbox("Salto de escrutinio", value=False, key="chk_scrut"):
        jump_pct = st.slider(
            "Salto (%)", 1.0, 30.0, 10.0, step=0.5, key="scrut_pct"
        )
        active_injections["salto_escrutinio"] = {"jump_pct": jump_pct}

    # 6. Benford violation
    if st.checkbox("Violación Benford", value=False, key="chk_benf"):
        active_injections["violacion_benford"] = {}

# ---------------------------------------------------------------------------
# Build base and modified snapshots
# ---------------------------------------------------------------------------

base_snap = snapshots[selected_idx]
prev_snap = snapshots[selected_idx - 1] if selected_idx > 0 else None

base_rule_data = snapshot_to_rule_format(base_snap["payload"], base_snap["timestamp"])
prev_rule_data = (
    snapshot_to_rule_format(prev_snap["payload"], prev_snap["timestamp"])
    if prev_snap
    else None
)

# Apply injections
modified_data = copy.deepcopy(base_rule_data)

for injection_key, params in active_injections.items():
    if injection_key == "spike_votos":
        modified_data = inject_vote_spike(
            modified_data, params["candidate_idx"], params["extra_votes"]
        )
    elif injection_key == "descuadre_aritmetico":
        modified_data = inject_arithmetic_mismatch(modified_data, params["offset"])
    elif injection_key == "regresion_votos":
        modified_data = inject_vote_regression(
            modified_data, params["candidate_idx"], params["reduction"]
        )
    elif injection_key == "velocidad_actas":
        modified_data = inject_acta_speed_anomaly(
            modified_data, params["extra_actas"]
        )
    elif injection_key == "salto_escrutinio":
        modified_data = inject_scrutiny_jump(modified_data, params["jump_pct"])
    elif injection_key == "violacion_benford":
        modified_data = inject_benford_violation(modified_data)

# ---------------------------------------------------------------------------
# Run rules on both base and modified
# ---------------------------------------------------------------------------

rule_configs = {k: dict(v) for k, v in DEFAULT_RULE_PARAMS.items()}

alerts_base = run_rules_sandbox(base_rule_data, prev_rule_data, rule_configs)
alerts_modified = run_rules_sandbox(modified_data, prev_rule_data, rule_configs)

# ---------------------------------------------------------------------------
# Display results
# ---------------------------------------------------------------------------

st.markdown("---")

# Summary metrics
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Inyecciones activas",
        len(active_injections),
    )

with col2:
    st.metric(
        "Alertas (original)",
        len(alerts_base),
    )

with col3:
    new_alerts = len(alerts_modified) - len(alerts_base)
    st.metric(
        "Alertas (modificado)",
        len(alerts_modified),
        delta=f"+{new_alerts}" if new_alerts > 0 else str(new_alerts),
        delta_color="inverse",
    )

with col4:
    high_sev = sum(1 for a in alerts_modified if a.get("severity") == "High")
    st.metric("Severidad Alta", high_sev)

# Tabs: comparison and detail
tab_compare, tab_data, tab_alerts = st.tabs(
    ["Comparación", "Datos Snapshot", "Detalle de Alertas"]
)

with tab_compare:
    st.subheader("Antes vs. Después de la inyección")

    base_candidates = base_rule_data.get("candidatos", [])
    mod_candidates = modified_data.get("candidatos", [])

    if base_candidates and mod_candidates:
        compare_rows = []
        for i, (b, m) in enumerate(zip(base_candidates, mod_candidates)):
            name = b.get("party", "") or b.get("name", f"Candidato {i}")
            compare_rows.append({
                "Candidato": name[:40],
                "Votos Original": b.get("votes", 0),
                "Votos Modificado": m.get("votes", 0),
                "Diferencia": m.get("votes", 0) - b.get("votes", 0),
            })

        compare_df = pd.DataFrame(compare_rows)
        st.dataframe(
            compare_df.style.format({
                "Votos Original": "{:,}",
                "Votos Modificado": "{:,}",
                "Diferencia": "{:+,}",
            }),
            use_container_width=True,
        )

        # Bar chart comparison
        melted = compare_df.melt(
            id_vars="Candidato",
            value_vars=["Votos Original", "Votos Modificado"],
            var_name="Versión",
            value_name="Votos",
        )
        fig = px.bar(
            melted,
            x="Candidato",
            y="Votos",
            color="Versión",
            barmode="group",
            title="Comparación de votos: Original vs. Inyectado",
            color_discrete_map={
                "Votos Original": "#636EFA",
                "Votos Modificado": "#EF553B",
            },
        )
        st.plotly_chart(fig, use_container_width=True)

    # Totals comparison
    base_totals = base_rule_data.get("totals", {})
    mod_totals = modified_data.get("totals", {})

    totals_compare = pd.DataFrame([
        {
            "Métrica": "Total votos",
            "Original": base_totals.get("total_votes", 0),
            "Modificado": mod_totals.get("total_votes", 0),
        },
        {
            "Métrica": "Votos válidos",
            "Original": base_totals.get("valid_votes", 0),
            "Modificado": mod_totals.get("valid_votes", 0),
        },
        {
            "Métrica": "Actas procesadas",
            "Original": base_totals.get("actas_procesadas", 0),
            "Modificado": mod_totals.get("actas_procesadas", 0),
        },
    ])
    st.dataframe(
        totals_compare.style.format({
            "Original": "{:,}",
            "Modificado": "{:,}",
        }),
        use_container_width=True,
    )

with tab_data:
    st.subheader("Snapshot base (formato reglas)")
    st.json(base_rule_data)

    if active_injections:
        st.subheader("Snapshot modificado (formato reglas)")
        st.json(modified_data)

with tab_alerts:
    st.subheader("Alertas generadas")

    if not alerts_modified:
        st.success("Sin alertas — el motor no detectó anomalías.")
    else:
        for alert in alerts_modified:
            severity = alert.get("severity", "Low")
            icon = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(severity, "⚪")
            rule = alert.get("rule", "?")

            # Check if this alert is new (from injection)
            is_new = alert not in alerts_base
            new_badge = " **[NUEVA]**" if is_new else ""

            with st.expander(
                f"{icon} [{severity}] {alert.get('type', 'Alerta')} — regla: {rule}{new_badge}",
                expanded=is_new,
            ):
                st.markdown(f"**Departamento:** {alert.get('department', 'N/A')}")
                st.markdown(f"**Justificación:** {alert.get('justification', '')}")

    # Alert severity distribution chart
    if alerts_modified:
        sev_counts = pd.DataFrame(alerts_modified).groupby("severity").size().reset_index(name="count")
        fig_sev = px.pie(
            sev_counts,
            values="count",
            names="severity",
            title="Distribución de severidad",
            color="severity",
            color_discrete_map={"High": "#EF553B", "Medium": "#FFA15A", "Low": "#00CC96"},
        )
        st.plotly_chart(fig_sev, use_container_width=True)

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown("---")
st.caption(
    "Panel de Caos — Sentinel v4 | "
    "Todas las inyecciones son efímeras y no afectan datos reales."
)
