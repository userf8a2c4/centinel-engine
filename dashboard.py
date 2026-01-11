"""
C.E.N.T.I.N.E.L. Dashboard
v3.1 - enero 2026 - refactor dashboard modos simple/avanzado

Cambios principales:
- Modo Simple (visitantes) y Modo Avanzado (auditores) con sidebar organizada.
- UI más limpia con tarjetas, métricas destacadas y manejo de estados sin datos.
- Alertas, timeline, estadísticas resumidas y sección de estado del sistema.
- Vista avanzada con JSON, diffs, reglas/anomalías, logs y configuración read-only.
- Caché inteligente para lecturas de snapshots, alertas y hashes.

Ejecución rápida:
1) streamlit run dashboard.py
2) Configura config.yaml y coloca snapshots en data/ (o tests/fixtures/).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import json

import pandas as pd
import streamlit as st

from scripts.download_and_hash import load_config, normalize_master_switch


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
HASH_DIR = BASE_DIR / "hashes"
FIXTURES_DIR = BASE_DIR / "tests" / "fixtures" / "snapshots_2025"
ALERTS_JSON = DATA_DIR / "alerts.json"
ANOMALIES_REPORT = BASE_DIR / "anomalies_report.json"
ALERTS_LOG = BASE_DIR / "alerts.log"
LOG_FILE = BASE_DIR / "centinel.log"


st.set_page_config(
    page_title="C.E.N.T.I.N.E.L. Dashboard",
    page_icon="📡",
    layout="wide",
)

st.markdown(
    """
    <style>
    .stApp { background-color: #f7f9fc; color: #111827; }
    .centinel-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 16px;
        padding: 1rem 1.25rem;
        box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
    }
    .badge {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.35rem 0.65rem;
        border-radius: 999px;
        font-size: 0.85rem;
        font-weight: 700;
        letter-spacing: 0.04em;
    }
    .badge-success { background: #dcfce7; color: #166534; }
    .badge-danger { background: #fee2e2; color: #991b1b; }
    .badge-warn { background: #ffedd5; color: #9a3412; }
    .muted { color: #6b7280; }
    .title-subtle { font-size: 1.05rem; font-weight: 600; color: #1f2937; }
    .hero-title { font-size: 2rem; font-weight: 800; margin-bottom: 0.25rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


@dataclass
class DashboardState:
    mode: str
    password_ok: bool
    alerts_seen: int


def parse_timestamp(value: Any, fallback: str | None = None) -> datetime | None:
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if fallback:
        try:
            return datetime.fromisoformat(fallback)
        except ValueError:
            return None
    return None


def extract_timestamp_from_filename(name: str) -> datetime | None:
    if "snapshot_" not in name:
        return None
    raw = name.split("snapshot_")[-1].split(".")[0]
    for fmt in ("%Y-%m-%d_%H-%M-%S", "%Y-%m-%dT%H-%M-%SZ", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(raw.replace("_", " ").replace("-", ":", 2))
    except ValueError:
        return None


@st.cache_data(ttl=300)
def load_snapshots() -> list[dict[str, Any]]:
    search_paths = [
        *sorted(FIXTURES_DIR.glob("*.json")),
        *sorted(DATA_DIR.glob("*.json")),
    ]
    snapshots: list[dict[str, Any]] = []
    for file_path in search_paths:
        try:
            payload = json.loads(file_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        payload["source_path"] = file_path.name
        if "timestamp" not in payload and "timestamp_utc" not in payload:
            timestamp = extract_timestamp_from_filename(file_path.name)
            if timestamp:
                payload["timestamp"] = timestamp.isoformat()
        snapshots.append(payload)
    return snapshots


@st.cache_data(ttl=300)
def load_alerts() -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    for path in (ALERTS_JSON, ANOMALIES_REPORT):
        if path.exists():
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if isinstance(payload, list):
                alerts.extend(payload)
            elif isinstance(payload, dict) and "alerts" in payload:
                alerts.extend(payload.get("alerts", []))
    if ALERTS_LOG.exists():
        lines = ALERTS_LOG.read_text(encoding="utf-8").splitlines()[-25:]
        for line in lines:
            alerts.append({"descripcion": line, "source": "alerts.log"})
    return alerts


@st.cache_data(ttl=300)
def load_hashes() -> list[dict[str, str]]:
    hashes: list[dict[str, str]] = []
    for path in sorted(HASH_DIR.glob("*.sha256")):
        content = path.read_text(encoding="utf-8").strip()
        hashes.append({"file": path.stem, "hash": content})
    return hashes


@st.cache_data(ttl=120)
def load_logs() -> list[str]:
    if not LOG_FILE.exists():
        return []
    return LOG_FILE.read_text(encoding="utf-8").splitlines()[-200:]


def normalize_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    timestamp_raw = snapshot.get("timestamp") or snapshot.get("timestamp_utc")
    timestamp = parse_timestamp(timestamp_raw)
    if not timestamp:
        timestamp = extract_timestamp_from_filename(snapshot.get("source_path", ""))
    department = snapshot.get("departamento") or snapshot.get("department")
    candidates = snapshot.get("candidatos") or snapshot.get("candidates") or []
    if not candidates:
        votos_blancos = snapshot.get("votos_blancos")
        if isinstance(votos_blancos, dict):
            candidates = votos_blancos.get("candidatos", [])
    if not candidates and snapshot.get("resultados"):
        candidates = [
            {
                "candidato": item.get("candidato", ""),
                "partido": item.get("partido", ""),
                "votos": item.get("votos"),
            }
            for item in snapshot.get("resultados", [])
        ]
    return {
        "timestamp": timestamp,
        "registered_voters": snapshot.get("inscritos")
        or snapshot.get("registered_voters")
        or 0,
        "total_votes": snapshot.get("votos_emitidos")
        or snapshot.get("total_votes")
        or 0,
        "valid_votes": snapshot.get("votos_validos")
        or snapshot.get("valid_votes")
        or 0,
        "null_votes": snapshot.get("votos_nulos") or snapshot.get("null_votes") or 0,
        "blank_votes": (
            snapshot.get("votos_blancos")
            if isinstance(snapshot.get("votos_blancos"), int)
            else snapshot.get("blank_votes") or 0
        ),
        "department": department,
        "candidates": candidates,
        "source_path": snapshot.get("source_path", ""),
        "raw": snapshot,
    }


def build_snapshot_frame(snapshots: list[dict[str, Any]]) -> pd.DataFrame:
    normalized = [normalize_snapshot(item) for item in snapshots]
    df = pd.DataFrame(normalized)
    if not df.empty:
        df = df.dropna(subset=["timestamp"]).sort_values("timestamp")
    return df


def get_master_switch_status(config: dict[str, Any]) -> tuple[str, str]:
    status = normalize_master_switch(config.get("master_switch"))
    if status == "ON":
        return "ON", "badge-success"
    if status == "OFF":
        return "OFF", "badge-danger"
    return "UNKNOWN", "badge-warn"


def compute_changes(df: pd.DataFrame, days: int) -> int:
    if df.empty:
        return 0
    cutoff = datetime.now() - timedelta(days=days)
    recent = df[df["timestamp"] >= cutoff]
    if len(recent) < 2:
        return 0
    deltas = recent["total_votes"].diff().fillna(0)
    return int((deltas != 0).sum())


def build_department_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "department" not in df.columns:
        return pd.DataFrame()
    summary = (
        df.dropna(subset=["department"])
        .groupby("department", as_index=False)
        .agg(changes=("total_votes", "count"))
        .sort_values("changes", ascending=False)
    )
    return summary.head(5)


def build_alerts_frame(alerts: list[dict[str, Any]]) -> pd.DataFrame:
    if not alerts:
        return pd.DataFrame()
    rows = []
    for alert in alerts:
        if not isinstance(alert, dict):
            continue
        rows.append(
            {
                "timestamp": alert.get("timestamp")
                or alert.get("fecha")
                or alert.get("time")
                or "",
                "rule": alert.get("rule") or alert.get("type") or "Alerta",
                "descripcion": alert.get("descripcion")
                or alert.get("description")
                or alert.get("detail")
                or alert.get("message")
                or "",
                "source": alert.get("source") or alert.get("file") or "",
            }
        )
    return pd.DataFrame(rows)


def diff_snapshots(previous: dict[str, Any], current: dict[str, Any]) -> pd.DataFrame:
    keys = [
        "registered_voters",
        "total_votes",
        "valid_votes",
        "null_votes",
        "blank_votes",
    ]
    rows = []
    for key in keys:
        prev_val = previous.get(key)
        curr_val = current.get(key)
        rows.append(
            {
                "campo": key,
                "anterior": prev_val,
                "actual": curr_val,
                "delta": (curr_val or 0) - (prev_val or 0),
            }
        )
    return pd.DataFrame(rows)


def render_alerts_list(alerts_df: pd.DataFrame, limit: int = 8) -> None:
    if alerts_df.empty:
        st.info("No hay alertas recientes registradas.")
        return
    st.dataframe(alerts_df.head(limit), use_container_width=True, hide_index=True)


def render_timeline(df: pd.DataFrame) -> None:
    if df.empty or len(df) < 2:
        st.info("Aún no hay suficientes snapshots para mostrar la evolución.")
        return
    timeline = df.set_index("timestamp")[["total_votes"]]
    st.line_chart(timeline, height=220)


def render_system_status(
    df: pd.DataFrame, hashes: list[dict[str, str]], logs: list[str]
) -> None:
    last_snapshot = df.iloc[-1] if not df.empty else None
    last_ts = last_snapshot["timestamp"] if last_snapshot is not None else None
    avg_interval = None
    if not df.empty and len(df) > 1:
        deltas = df["timestamp"].diff().dropna().dt.total_seconds()
        if not deltas.empty:
            avg_interval = deltas.mean() / 60
    fallback_used = any("fallback" in line.lower() for line in logs)

    col_a, col_b, col_c = st.columns(3)
    col_a.metric(
        "Último scraping exitoso",
        last_ts.strftime("%Y-%m-%d %H:%M") if last_ts else "Sin datos",
    )
    col_b.metric(
        "Intervalo promedio (min)",
        f"{avg_interval:.1f}" if avg_interval else "N/D",
    )
    col_c.metric(
        "Fallback Playwright",
        "Sí" if fallback_used else "No detectado",
    )

    if hashes:
        st.caption("Último hash registrado")
        st.code(hashes[-1]["hash"], language="text")


def render_simple_mode(
    state: DashboardState,
    df: pd.DataFrame,
    alerts_df: pd.DataFrame,
    dept_summary: pd.DataFrame,
    hashes: list[dict[str, str]],
    master_status: tuple[str, str],
) -> None:
    status_label, badge_class = master_status
    st.markdown(
        "<div class='hero-title'>📡 C.E.N.T.I.N.E.L.</div>", unsafe_allow_html=True
    )
    st.markdown(
        "Monitoreo ciudadano de datos electorales públicos en tiempo casi real.",
    )

    badge_text = f"MASTER SWITCH: {status_label}"
    st.markdown(
        f"<span class='badge {badge_class}'>⚡ {badge_text}</span>",
        unsafe_allow_html=True,
    )

    if status_label == "OFF":
        st.warning(
            "El monitoreo automático está en pausa. Algunos datos podrían no estar actualizados."
        )

    last_snapshot = df.iloc[-1] if not df.empty else None
    last_ts = last_snapshot["timestamp"] if last_snapshot is not None else None
    changes_today = compute_changes(df, 1)
    changes_week = compute_changes(df, 7)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric(
        "Último snapshot", last_ts.strftime("%Y-%m-%d %H:%M") if last_ts else "--"
    )
    col2.metric("Cambios hoy", changes_today)
    col3.metric("Cambios 7 días", changes_week)
    col4.metric("Alertas recientes", len(alerts_df))

    st.markdown("---")
    with st.container():
        st.markdown(
            "<div class='title-subtle'>Alertas recientes</div>", unsafe_allow_html=True
        )
        render_alerts_list(alerts_df, limit=8)

    with st.container():
        st.markdown(
            "<div class='title-subtle'>Timeline simple</div>", unsafe_allow_html=True
        )
        render_timeline(df)

    with st.container():
        st.markdown(
            "<div class='title-subtle'>Top cambios por departamento</div>",
            unsafe_allow_html=True,
        )
        if dept_summary.empty:
            st.info("No hay datos de departamentos disponibles.")
        else:
            st.dataframe(dept_summary, use_container_width=True, hide_index=True)

    if hashes:
        st.markdown(
            "<div class='title-subtle'>Hash actual</div>", unsafe_allow_html=True
        )
        st.code(hashes[-1]["hash"], language="text")
        if st.button("Copiar hash actual"):
            st.toast("Hash listo para copiar. Usa Ctrl+C o el botón copiar del bloque.")

    st.markdown(
        "<div class='centinel-card'><strong>¿Necesitas más detalle?</strong><br/>"
        "Activa el modo avanzado en el panel lateral para ver datos crudos, diffs y logs.</div>",
        unsafe_allow_html=True,
    )


def render_advanced_mode(
    df: pd.DataFrame,
    alerts_df: pd.DataFrame,
    hashes: list[dict[str, str]],
    config: dict[str, Any],
    logs: list[str],
) -> None:
    st.header("🔎 Modo Avanzado")
    if df.empty:
        st.warning("No hay snapshots suficientes para análisis avanzado.")
        return

    last_snapshot = df.iloc[-1]
    previous_snapshot = df.iloc[-2] if len(df) > 1 else last_snapshot

    st.subheader("Totales principales")
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Registrados", f"{last_snapshot['registered_voters']:,}")
    col2.metric(
        "Votos emitidos",
        f"{last_snapshot['total_votes']:,}",
        delta=f"{(last_snapshot['total_votes'] - previous_snapshot['total_votes']):,}",
    )
    col3.metric("Votos válidos", f"{last_snapshot['valid_votes']:,}")
    col4.metric("Votos nulos", f"{last_snapshot['null_votes']:,}")
    col5.metric("Votos blancos", f"{last_snapshot['blank_votes']:,}")

    st.subheader("Differences entre el último snapshot y el anterior")
    diff_df = diff_snapshots(previous_snapshot.to_dict(), last_snapshot.to_dict())
    st.dataframe(diff_df, use_container_width=True, hide_index=True)

    st.subheader("Snapshots recientes")
    st.dataframe(
        df[
            [
                "timestamp",
                "department",
                "registered_voters",
                "total_votes",
                "valid_votes",
            ]
        ].tail(20),
        use_container_width=True,
        hide_index=True,
    )
    st.download_button(
        "Exportar snapshots CSV",
        df.to_csv(index=False).encode("utf-8"),
        file_name="snapshots.csv",
        mime="text/csv",
    )

    st.subheader("Alertas y reglas")
    if alerts_df.empty:
        st.info("No hay alertas para mostrar.")
    else:
        st.dataframe(alerts_df, use_container_width=True, hide_index=True)
        st.download_button(
            "Exportar alertas CSV",
            alerts_df.to_csv(index=False).encode("utf-8"),
            file_name="alertas.csv",
            mime="text/csv",
        )

    st.subheader("JSON crudo")
    st.json(last_snapshot["raw"], expanded=False)

    st.subheader("Hashes")
    if hashes:
        st.dataframe(pd.DataFrame(hashes), use_container_width=True, hide_index=True)
    else:
        st.info("No hay hashes disponibles en la carpeta hashes/.")

    st.subheader("Configuración (solo lectura)")
    st.json(config, expanded=False)

    st.subheader("Logs recientes")
    if logs:
        st.code("\n".join(logs[-120:]), language="text")
    else:
        st.info("No se encontró centinel.log.")

    with st.expander("Debug / Inspección avanzada"):
        st.write("Session state", st.session_state)
        st.write("Query params", dict(st.query_params))


def get_dashboard_state(config: dict[str, Any]) -> DashboardState:
    query_mode = st.query_params.get("mode", "").lower()
    default_mode = "advanced" if query_mode == "advanced" else "simple"
    if "dashboard_mode" not in st.session_state:
        st.session_state.dashboard_mode = default_mode
    if "alerts_seen" not in st.session_state:
        st.session_state.alerts_seen = 0

    password_required = config.get("dashboard_password")
    password_ok = True
    if password_required:
        input_value = st.session_state.get("dashboard_password_input", "")
        password_ok = input_value == password_required
    return DashboardState(
        mode=st.session_state.dashboard_mode,
        password_ok=password_ok,
        alerts_seen=st.session_state.alerts_seen,
    )


config = {}
try:
    config = load_config()
except Exception as exc:
    st.warning(f"No se pudo cargar config.yaml: {exc}")

snapshots = load_snapshots()
alerts = load_alerts()
hashes = load_hashes()
logs = load_logs()

snapshot_df = build_snapshot_frame(snapshots)
alerts_df = build_alerts_frame(alerts)

state = get_dashboard_state(config)

st.sidebar.title("⚙️ Configuración")
mode_choice = st.sidebar.radio(
    "Modo de visualización",
    options=["simple", "advanced"],
    index=0 if state.mode == "simple" else 1,
    format_func=lambda value: "Simple" if value == "simple" else "Avanzado",
)
if mode_choice != st.session_state.dashboard_mode:
    st.session_state.dashboard_mode = mode_choice

if config.get("dashboard_password"):
    st.sidebar.text_input(
        "Password modo avanzado",
        type="password",
        key="dashboard_password_input",
        help="Requerido para ver el modo avanzado.",
    )

st.sidebar.markdown("---")

if not snapshot_df.empty:
    min_date = snapshot_df["timestamp"].min().date()
    max_date = snapshot_df["timestamp"].max().date()
else:
    today = datetime.now().date()
    min_date = today
    max_date = today

date_range = st.sidebar.date_input(
    "Rango de fechas",
    value=(min_date, max_date),
)
if isinstance(date_range, tuple):
    start_date, end_date = date_range
else:
    start_date = date_range
    end_date = date_range

sources = ["Todos"]
if not snapshot_df.empty:
    sources += sorted(snapshot_df["source_path"].dropna().unique().tolist())
source_filter = st.sidebar.selectbox("Fuente", sources)

departments = ["Todos"]
if not snapshot_df.empty and "department" in snapshot_df.columns:
    departments += sorted(
        [dept for dept in snapshot_df["department"].dropna().unique().tolist() if dept]
    )

department_filter = st.sidebar.selectbox("Departamento", departments)

if st.sidebar.button("Actualizar datos"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")
if st.sidebar.button("Marcar alertas como vistas"):
    st.session_state.alerts_seen = len(alerts_df)

filtered_df = snapshot_df.copy()
if not filtered_df.empty:
    filtered_df = filtered_df[
        (filtered_df["timestamp"].dt.date >= start_date)
        & (filtered_df["timestamp"].dt.date <= end_date)
    ]
    if source_filter != "Todos":
        filtered_df = filtered_df[filtered_df["source_path"] == source_filter]
    if department_filter != "Todos":
        filtered_df = filtered_df[filtered_df["department"] == department_filter]

master_status = get_master_switch_status(config)

st.caption(f"Última actualización del dashboard: {datetime.now():%Y-%m-%d %H:%M}")

alert_badge = ""
if len(alerts_df) > state.alerts_seen:
    alert_badge = "🔴 Nuevas alertas"
    st.warning("Hay alertas recientes no vistas.")

if st.session_state.dashboard_mode == "simple":
    render_simple_mode(
        state=state,
        df=filtered_df,
        alerts_df=alerts_df,
        dept_summary=build_department_summary(filtered_df),
        hashes=hashes,
        master_status=master_status,
    )
else:
    if not state.password_ok:
        st.error("Modo avanzado bloqueado. Ingresa el password en el panel lateral.")
    else:
        render_advanced_mode(
            df=filtered_df,
            alerts_df=alerts_df,
            hashes=hashes,
            config=config,
            logs=logs,
        )

st.markdown("---")
render_system_status(filtered_df, hashes, logs)

if alert_badge:
    st.info(alert_badge)

st.caption("C.E.N.T.I.N.E.L. • Monitoreo ciudadano de datos electorales")
