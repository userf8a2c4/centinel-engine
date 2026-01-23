"""Streamlit dashboard for the global Centinel engine."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import altair as alt
import pandas as pd
import streamlit as st

from src.sentinel.core.storage import LocalSnapshotStore

from src.utils.config import load_config
from src.utils.stats import benford_expected_distribution, last_digit_distribution


def load_snapshots(db_path: str, department_code: str) -> List[Dict[str, Any]]:
    store = LocalSnapshotStore(db_path)
    rows = store._fetch_department_rows(department_code)
    payloads = []
    for row in rows:
        payloads.append(
            {
                "timestamp_utc": row["timestamp_utc"],
                "total_votes": row["total_votes"],
                "valid_votes": row["valid_votes"],
                "null_votes": row["null_votes"],
                "blank_votes": row["blank_votes"],
                "candidates_json": row["candidates_json"],
            }
        )
    store.close()
    return payloads


def build_kpis(snapshot_df: pd.DataFrame) -> Dict[str, Any]:
    if snapshot_df.empty:
        return {
            "snapshots": 0,
            "latest_total_votes": 0,
            "latest_valid_votes": 0,
            "latest_updated": "-",
        }

    latest = snapshot_df.iloc[-1]
    return {
        "snapshots": len(snapshot_df),
        "latest_total_votes": int(latest["total_votes"]),
        "latest_valid_votes": int(latest["valid_votes"]),
        "latest_updated": latest["timestamp_utc"],
    }


def render_header(config: Dict[str, Any]) -> None:
    st.markdown(
        """
        <style>
        body { background-color: #0B1120; color: #E2E8F0; }
        .centinel-card { background-color: #111827; padding: 24px; border-radius: 16px; }
        .centinel-kpi { background-color: #0F172A; padding: 18px; border-radius: 12px; }
        .centinel-pill { background-color: #10B981; color: #052e16; padding: 4px 10px; border-radius: 999px; font-weight: 600; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <div class="centinel-card">
            <h1 style="margin-bottom: 0;">C.E.N.T.I.N.E.L. — {config['country_name']}</h1>
            <p style="margin-top: 6px;">Observación electoral en tiempo real con anclaje blockchain.</p>
            <span class="centinel-pill">Estado operativo</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpis(kpis: Dict[str, Any]) -> None:
    cols = st.columns(4)
    cols[0].metric("Snapshots (24h)", kpis["snapshots"])
    cols[1].metric("Total votos", kpis["latest_total_votes"])
    cols[2].metric("Votos válidos", kpis["latest_valid_votes"])
    cols[3].metric("Última actualización", kpis["latest_updated"])


def render_benford_chart(votes: List[int]) -> None:
    expected = benford_expected_distribution()
    observed = pd.Series(votes).astype(int)
    observed = observed[observed > 0].astype(str).str[0].astype(int)
    counts = observed.value_counts().sort_index().reindex(range(1, 10), fill_value=0)
    data = pd.DataFrame(
        {
            "digit": range(1, 10),
            "observed": counts.values,
            "expected": [expected[digit] for digit in range(1, 10)],
        }
    )
    chart = (
        alt.Chart(data)
        .transform_fold(["observed", "expected"], as_=["series", "value"])
        .mark_bar(opacity=0.7)
        .encode(
            x=alt.X("digit:O", title="Primer dígito"),
            y=alt.Y("value:Q", title="Frecuencia"),
            color=alt.Color("series:N", legend=alt.Legend(title="Serie")),
        )
        .properties(height=240)
    )
    st.altair_chart(chart, use_container_width=True)


def render_last_digit_chart(votes: List[int]) -> None:
    distribution = last_digit_distribution(votes)
    data = pd.DataFrame(
        {
            "digit": list(range(10)),
            "count": [distribution.get(digit, 0) for digit in range(10)],
        }
    )
    chart = (
        alt.Chart(data)
        .mark_bar(color="#10B981")
        .encode(x="digit:O", y="count:Q")
        .properties(height=240)
    )
    st.altair_chart(chart, use_container_width=True)


def render_activity(snapshot_df: pd.DataFrame) -> None:
    if snapshot_df.empty:
        st.info("No hay snapshots disponibles para analizar actividad horaria.")
        return
    snapshot_df["hour"] = pd.to_datetime(snapshot_df["timestamp_utc"]).dt.hour
    activity = snapshot_df.groupby("hour").size().reset_index(name="snapshots")
    chart = (
        alt.Chart(activity)
        .mark_line(point=True, color="#60A5FA")
        .encode(x="hour:O", y="snapshots:Q")
        .properties(height=240)
    )
    st.altair_chart(chart, use_container_width=True)


def main() -> None:
    config = load_config("HN")
    render_header(config)

    department_code = config["datasource"]["sources"][0]["department_code"]
    db_path = config["storage"]["sqlite_path"]
    snapshots = load_snapshots(db_path, department_code)

    snapshot_df = pd.DataFrame(snapshots)
    kpis = build_kpis(snapshot_df)
    render_kpis(kpis)

    st.divider()

    col_left, col_right = st.columns(2)
    votes = []
    if not snapshot_df.empty:
        latest_row = snapshot_df.iloc[-1]
        candidates_json = latest_row.get("candidates_json") or "[]"
        try:
            candidates = pd.DataFrame(json.loads(candidates_json))
        except json.JSONDecodeError:
            candidates = pd.DataFrame([])
        if not candidates.empty and "votes" in candidates.columns:
            votes = candidates["votes"].astype(int).tolist()

    with col_left:
        st.subheader("Ley de Benford")
        render_benford_chart(votes)

    with col_right:
        st.subheader("Últimos dígitos")
        render_last_digit_chart(votes)

    st.subheader("Actividad horaria")
    render_activity(snapshot_df)

    st.subheader("Snapshots recientes")
    if snapshot_df.empty:
        st.info("No hay snapshots disponibles aún.")
    else:
        st.dataframe(snapshot_df.tail(10), use_container_width=True)

    st.subheader("Reglas activas")
    rules = pd.DataFrame(config.get("integrity_rules", []))
    if rules.empty:
        st.info("No hay reglas configuradas.")
    else:
        st.dataframe(rules, use_container_width=True)

    st.divider()
    col_a, col_b, col_c = st.columns(3)
    col_a.button("Tomar Snapshot Ahora")
    col_b.button("Validar en Arbitrum")
    col_c.button("Descargar Reporte PDF")


if __name__ == "__main__":
    main()
