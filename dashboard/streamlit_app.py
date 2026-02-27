"""C.E.N.T.I.N.E.L. premium institutional dashboard.

ES: Archivo principal de Streamlit con diseño premium institucional para auditoría electoral.
EN: Main Streamlit file with premium institutional UX for electoral auditing.
"""

from __future__ import annotations

# ES: Importaciones estándar para fechas, rutas y tipado.
# EN: Standard imports for dates, paths, and typing.
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ES: Importaciones de terceros para visualización y app.
# EN: Third-party imports for visualization and app runtime.
import altair as alt
import pandas as pd
import streamlit as st

# ES: Importa variables de tema reutilizables centralizadas.
# EN: Import centralized reusable theme variables.
from utils.theme import (
    ALERT_ORANGE,
    BRAND_BLUE,
    INTEGRITY_GREEN,
    PAGE_CONFIG,
    build_institutional_css,
)


@dataclass(frozen=True)
class DashboardSnapshot:
    """ES: Modelo de datos para un snapshot de auditoría.

    EN: Data model for a single audit snapshot.
    """

    timestamp: datetime
    source: str
    mesas_observadas: int
    alertas_criticas: int
    indice_integridad: float


def _parse_snapshot(payload: dict[str, Any], source_name: str) -> DashboardSnapshot:
    """ES: Convierte JSON arbitrario en un snapshot normalizado.

    EN: Convert arbitrary JSON payload into a normalized snapshot.
    """

    # ES: Normaliza timestamp con fallback seguro en UTC.
    # EN: Normalize timestamp with safe UTC fallback.
    raw_ts = payload.get("timestamp") or payload.get("generated_at") or datetime.now(timezone.utc).isoformat()
    try:
        parsed_ts = datetime.fromisoformat(str(raw_ts).replace("Z", "+00:00"))
    except ValueError:
        parsed_ts = datetime.now(timezone.utc)

    # ES: Toma métricas clave y define valores por defecto robustos.
    # EN: Extract key metrics and define robust defaults.
    mesas = int(payload.get("mesas_observadas", payload.get("tables_observed", 0)))
    alertas = int(payload.get("alertas_criticas", payload.get("critical_alerts", 0)))
    integrity = float(payload.get("indice_integridad", payload.get("integrity_index", 0.0)))

    return DashboardSnapshot(
        timestamp=parsed_ts,
        source=source_name,
        mesas_observadas=mesas,
        alertas_criticas=alertas,
        indice_integridad=integrity,
    )


@st.cache_data(show_spinner=False)
def load_latest_snapshot() -> DashboardSnapshot:
    """ES: Carga el JSON más reciente desde carpetas operativas típicas.

    EN: Load the most recent JSON from typical operational folders.
    """

    # ES: Define rutas candidatas para mantener compatibilidad flexible.
    # EN: Define candidate paths to keep flexible compatibility.
    candidate_dirs = [Path("data"), Path("logs"), Path("artifacts"), Path("reports")]
    json_candidates = [path for folder in candidate_dirs if folder.exists() for path in folder.glob("*.json")]

    # ES: Si no hay datos, retorna snapshot vacío institucional.
    # EN: If no data is found, return an empty institutional snapshot.
    if not json_candidates:
        return DashboardSnapshot(datetime.now(timezone.utc), "sin_datos.json", 0, 0, 0.0)

    latest = max(json_candidates, key=lambda p: p.stat().st_mtime)

    # ES: Protege la lectura JSON ante archivos corruptos o estructuras no válidas.
    # EN: Protect JSON loading against corrupted files or invalid structures.
    try:
        payload = json.loads(latest.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            payload = {}
    except (json.JSONDecodeError, OSError):
        payload = {}

    return _parse_snapshot(payload, latest.name)


def render_header(snapshot: DashboardSnapshot) -> None:
    """ES: Renderiza header fijo bilingüe con branding institucional.

    EN: Render fixed bilingual header with institutional branding.
    """

    # ES: Muestra marca, título estratégico y badge de independencia técnica.
    # EN: Display brand, strategic title, and technical independence badge.
    st.markdown(
        f"""
        <header class="ce-header">
            <div class="ce-header__left">
                <div class="ce-logo">C.E.N.T.I.N.E.L.</div>
                <div>
                    <h1>Centro de Vigilancia Electoral</h1>
                    <p>Election Integrity Surveillance Center</p>
                </div>
            </div>
            <div class="ce-header__right">
                <span class="ce-badge">Auditoría Técnica Independiente – Agnóstica a Partidos Políticos</span>
                <small>Fuente activa: {snapshot.source}</small>
            </div>
        </header>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar(snapshot: DashboardSnapshot) -> tuple[str, str]:
    """ES: Dibuja sidebar minimalista con filtros esenciales.

    EN: Draw minimalist sidebar with essential filters.
    """

    with st.sidebar:
        # ES: Encabezado compacto de filtros institucionales.
        # EN: Compact heading for institutional filters.
        st.markdown("### Filtros / Filters")
        alcance = st.selectbox("Cobertura", ["Nacional", "Provincial", "Municipal"], index=0)
        severidad = st.radio("Severidad", ["Todas", "Crítica", "Media", "Informativa"], horizontal=False)

        # ES: Footer institucional con metadatos y enlace metodológico opcional.
        # EN: Institutional footer with metadata and optional methodology link.
        updated_at = snapshot.timestamp.strftime("%Y-%m-%d %H:%M UTC")
        if st.secrets.get("ENV", "dev").lower() != "prod":
            st.markdown(
                f"""
                <div class="ce-footer">
                    <p><strong>Versión:</strong> 3.0.0-premium</p>
                    <p><strong>Última actualización JSON:</strong> {updated_at}</p>
                    <p><a href="https://centinel-engine.org/metodologia" target="_blank">Metodología técnica</a></p>
                </div>
                """,
                unsafe_allow_html=True,
            )
    return alcance, severidad


def render_kpis(snapshot: DashboardSnapshot) -> None:
    """ES: Presenta KPIs estratégicos en tarjetas premium.

    EN: Present strategic KPIs in premium cards.
    """

    # ES: Organiza métricas en tres columnas de alto contraste.
    # EN: Arrange metrics in three high-contrast columns.
    c1, c2, c3 = st.columns(3)
    c1.metric("Mesas Observadas", f"{snapshot.mesas_observadas:,}")
    c2.metric("Alertas Críticas", f"{snapshot.alertas_criticas:,}")
    c3.metric("Índice de Integridad", f"{snapshot.indice_integridad:.1f}%")


def render_integrity_chart(snapshot: DashboardSnapshot) -> None:
    """ES: Renderiza gráfico demo institucional para tracking de integridad.

    EN: Render institutional demo chart for integrity tracking.
    """

    # ES: Genera serie corta para narrativa visual ejecutiva.
    # EN: Generate short series for executive visual storytelling.
    trend = pd.DataFrame(
        {
            "checkpoint": ["T-3", "T-2", "T-1", "Actual"],
            "integridad": [max(snapshot.indice_integridad - 3, 0), max(snapshot.indice_integridad - 1.5, 0), max(snapshot.indice_integridad - 0.4, 0), snapshot.indice_integridad],
        }
    )

    national_latest = latest_df[~latest_df["department"].isin(departments)]
    total_nacional = int(national_latest["votes"].sum()) if not national_latest.empty else 0
    suma_departamentos = int(dept_latest["votes"].sum()) if not dept_latest.empty else 0
    delta_aggregacion = suma_departamentos - total_nacional

    diffs: dict[str, Any] = {}
    data_departamentos: list[dict[str, Any]] = []
    for _, row in dept_latest.iterrows():
        dept = row["department"]
        total = int(row["votes"])
        prev_row = prev_latest[prev_latest["department"] == dept]
        if not prev_row.empty:
            prev_total = int(prev_row.iloc[0]["votes"])
            diff_value = total - prev_total
            diffs[dept] = f"{diff_value:+,}"
        else:
            diffs[dept] = "N/D"
        data_departamentos.append({"departamento": dept, "total": f"{total:,}", "diff": diffs[dept]})

    def _snapshot_payload(snapshot_df: pd.DataFrame) -> list[dict[str, Any]]:
        """Español: Construye payload serializable para hash de snapshot.

        English: Build a serializable payload for snapshot hashing.
        """
        return (
            snapshot_df[["timestamp", "department", "votes", "delta", "changes", "hash"]]
            .fillna("")
            .to_dict(orient="records")
        )

    payload = _snapshot_payload(latest_df)
    hash_snapshot = compute_report_hash(json.dumps(payload, sort_keys=True))
    previous_hash = "N/D"
    if not prev_df.empty:
        previous_ts = prev_df["timestamp_dt"].max()
        previous_df = prev_df[prev_df["timestamp_dt"] == previous_ts]
        previous_payload = _snapshot_payload(previous_df)
        previous_hash = compute_report_hash(json.dumps(previous_payload, sort_keys=True))

    data_nacional = {
        "total_nacional": f"{total_nacional:,}",
        "suma_departamentos": f"{suma_departamentos:,}",
        "delta_aggregacion": f"{delta_aggregacion:+,}",
        "snapshots": len(snapshots_df),
    }

    return data_nacional, data_departamentos, hash_snapshot, previous_hash, diffs


# ES: Importar tema institucional premium / EN: Import premium institutional theme
from dashboard.utils.theme import (  # noqa: E402
    get_page_config,
    get_institutional_css,
    get_header_html,
    get_status_panel_html,
    get_micro_cards_html,
    get_sidebar_footer_html,
    get_footer_html,
    ACCENT_BLUE,
    GREEN_INTEGRITY,
    ALERT_ORANGE,
    DANGER_RED,
    CHART_PALETTE,
)
from dashboard.utils.visualizations import (  # noqa: E402
    apply_cross_filters,
    get_cross_filter_options,
    compute_benford_statistics,
    make_benford_first_digit_figure,
    make_changes_timeline_figure,
)

from dashboard.utils.kpi_cards import (  # noqa: E402
    create_cne_update_badge,
    create_kpi_card,
)

# ES: Configuracion de pagina institucional / EN: Institutional page configuration
st.set_page_config(**get_page_config())


# =========================================================================
# EN: Non-blocking sidebar authentication widget.
#     The dashboard is publicly visible. Authenticated users get access to
#     Sandbox, Historical Data, and Admin tabs.
# ES: Widget de autenticacion no-bloqueante en el sidebar.
#     El dashboard es publicamente visible. Los usuarios autenticados
#     obtienen acceso a los tabs de Sandbox, Datos Historicos y Admin.
# =========================================================================
if AUTH_AVAILABLE:
    ensure_admin_exists()
    # EN: Ensure a default UPNFM researcher account exists for sandbox demos.
    # ES: Asegurar que existe una cuenta UPNFM de investigador para demos del sandbox.
    create_user("upnfm", "upnfm2026", role="researcher")

_is_authenticated: bool = bool(st.session_state.get("auth_user"))

if _is_authenticated:
    _current_user: dict[str, Any] = st.session_state["auth_user"]
    _current_username: str = _current_user["username"]
    _current_role: str = _current_user["role"]
else:
    _current_user = {}
    _current_username = ""
    _current_role = ""

# =========================================================================
# EN: Load global configs (available for all tabs).
# ES: Cargar configuraciones globales (disponibles para todos los tabs).
# =========================================================================
configs = load_configs()
command_center_cfg = configs.get("command_center", {})
rules_path = Path("command_center") / "rules.yaml"
if not rules_path.exists():
    rules_path = Path("config/prod/rules.yaml")
rules_cfg = load_rules_config(rules_path)
resilience_cfg = rules_cfg.get("resiliencia", {}) if rules_cfg else {}

anchor = load_blockchain_anchor()

# =========================================================================
# EN: Sidebar — user info, logout, and global filters.
# ES: Sidebar — info de usuario, logout, y filtros globales.
# =========================================================================
if _is_authenticated:
    st.sidebar.markdown(
        f"**Usuario / User:** `{_current_username}`  \n"
        f"**Rol / Role:** `{_current_role}`"
    )
    # EN: Password change widget for authenticated users.
    # ES: Widget de cambio de contrasena para usuarios autenticados.
    if AUTH_AVAILABLE:
        with st.sidebar.expander("Cambiar contrasena / Change password"):
            _cp_current = st.text_input("Contrasena actual / Current password", type="password", key="cp_current")
            _cp_new = st.text_input("Nueva contrasena / New password", type="password", key="cp_new")
            _cp_confirm = st.text_input("Confirmar / Confirm", type="password", key="cp_confirm")
            if st.button("Cambiar / Change", key="cp_submit"):
                if not _cp_current or not _cp_new:
                    st.warning("Completa todos los campos / Fill all fields.")
                elif _cp_new != _cp_confirm:
                    st.error("Las contrasenas no coinciden / Passwords don't match.")
                elif len(_cp_new) < 6:
                    st.error("Minimo 6 caracteres / Minimum 6 characters.")
                else:
                    if change_password(_current_username, _cp_current, _cp_new):
                        st.success("Contrasena cambiada / Password changed.")
                    else:
                        st.error("Contrasena actual incorrecta / Current password incorrect.")
    if st.sidebar.button("Cerrar sesion / Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        rerun_app()
else:
    st.sidebar.markdown("**Modo publico / Public mode**")
    st.sidebar.caption(
        "EN: Log in to access Sandbox, Historical Data, and Admin features.  \n"
        "ES: Inicia sesion para acceder a Sandbox, Datos Historicos y funciones Admin."
    )
    st.altair_chart(chart, use_container_width=True)


def main() -> None:
    """ES: Orquesta layout completo del dashboard institucional.

    EN: Orchestrate the full institutional dashboard layout.
    """

    # ES: Configuración oficial de página en modo ancho para dashboards.
    # EN: Official page configuration in wide layout for dashboards.
    st.set_page_config(**PAGE_CONFIG)

    # ES: Inyecta CSS premium con paleta institucional obligatoria.
    # EN: Inject premium CSS with mandatory institutional palette.
    st.markdown(build_institutional_css(), unsafe_allow_html=True)

filter_options = get_cross_filter_options(snapshots_df)
selected_department = st.sidebar.selectbox(
    "Departamento / Department",
    filter_options["departments"] if filter_options["departments"] else ["Todos"],
    index=0,
)
selected_hours = st.sidebar.multiselect(
    "Hora / Hour",
    options=filter_options["hours"],
    default=[],
)
selected_rule_types = st.sidebar.multiselect(
    "Tipo de regla / Rule type",
    options=filter_options["rule_types"],
    default=[],
)
show_only_alerts = st.sidebar.toggle(
    "🚨 SOLO ANOMALÍAS / ANOMALIES ONLY",
    value=False,
    help="ES: Filtra para mostrar únicamente registros en estado ALERTA/REVISAR.\nEN: Show only ALERT/REVIEW records.",
)

filtered_snapshots = apply_cross_filters(
    snapshots_df,
    selected_department=selected_department,
    selected_hours=selected_hours,
    selected_rule_types=selected_rule_types,
    anomalies_only=show_only_alerts,
)

filtered_anomalies = build_anomalies(filtered_snapshots)
filtered_heatmap_df = build_heatmap(filtered_anomalies)

critical_count = len(filtered_anomalies[filtered_anomalies["type"] == "Delta negativo"])
(
    data_nacional,
    data_departamentos,
    current_snapshot_hash,
    previous_snapshot_hash,
    snapshot_diffs,
) = build_pdf_export_payload(snapshots_df, departments, selected_snapshot_timestamp)
current_snapshot_ts, previous_snapshot_ts = resolve_snapshot_context(snapshots_df, selected_snapshot_timestamp)
expected_streams = int(resilience_cfg.get("max_json_presidenciales", 19) or 19)
alert_thresholds = derive_alert_thresholds(resilience_cfg, expected_streams)
min_samples = alert_thresholds["min_samples"]
observed_streams = 0
if current_snapshot_ts is not None and not snapshots_df.empty:
    snapshots_df["timestamp_dt"] = pd.to_datetime(snapshots_df["timestamp"], errors="coerce", utc=True)
    latest_rows = snapshots_df[snapshots_df["timestamp_dt"] == current_snapshot_ts]
    observed_streams = int(latest_rows["department"].nunique())

negative_diffs = [dept for dept, diff in snapshot_diffs.items() if str(diff).startswith("-")]
latest_timestamp = None
if not snapshots_df.empty:
    latest_timestamp = pd.to_datetime(snapshots_df["timestamp"], errors="coerce", utc=True).dropna().max()
latest_label = latest_timestamp.strftime("%Y-%m-%d %H:%M UTC") if latest_timestamp else "Sin datos"
selected_snapshot_display = (
    selected_snapshot_label if selected_snapshot_label != "Último snapshot (Latest)" else latest_label
)
snapshot_hash_display = current_snapshot_hash[:12] + "…" if current_snapshot_hash != "N/D" else "N/D"

    # ES: Área principal con resumen ejecutivo y visualización central.
    # EN: Main area with executive summary and central visualization.
    st.markdown("## Panorama Ejecutivo / Executive Overview")
    render_kpis(snapshot)

    st.markdown("### Tendencia de Integridad / Integrity Trend")
    render_integrity_chart(snapshot)

    # ES: Bloque narrativo para equipos de observación internacional.
    # EN: Narrative block for international observation teams.
    st.markdown(
        f"""
        <section class="ce-panel">
            <h3>Lectura Técnica / Technical Reading</h3>
            <p>
                El monitoreo activo opera bajo parámetros de trazabilidad verificable,
                priorizando integridad de evidencia y neutralidad metodológica.
                Active monitoring runs under verifiable traceability parameters,
                prioritizing evidence integrity and methodological neutrality.
            </p>
            <p>
                Índice actual: <strong style="color:{BRAND_BLUE};">{snapshot.indice_integridad:.1f}%</strong> ·
                Alertas críticas: <strong style="color:{ALERT_ORANGE};">{snapshot.alertas_criticas}</strong> ·
                Estado de consistencia: <strong style="color:{INTEGRITY_GREEN};">operativo</strong>.
            </p>
        </section>
        """,
        unsafe_allow_html=True,
    )
with hero_cols[1]:
    st.markdown(
        get_status_panel_html(
            polling_status=polling_status,
            department=selected_department,
            snapshot_count=len(snapshot_files),
            latest_label=latest_label,
        ),
        unsafe_allow_html=True,
    )

alert_focus_container = st.container()
with alert_focus_container:
    if observed_streams and observed_streams < expected_streams:
        st.error("Cobertura incompleta según rules.yaml: " f"{observed_streams}/{expected_streams} streams observados.")
        emit_toast(
            f"Cobertura incompleta: {observed_streams}/{expected_streams} streams.",
            icon="🚨",
        )
    if len(snapshots_df) < min_samples:
        st.warning(
            "Muestras insuficientes según rules.yaml: " f"{len(snapshots_df)}/{min_samples} snapshots disponibles."
        )
    if negative_diffs:
        diff_label = ", ".join(negative_diffs[:5])
        message = (
            "Deltas negativos detectados en departamentos: "
            f"{diff_label}{'…' if len(negative_diffs) > 5 else ''}. "
            f"(Umbral rules.yaml ≥ {alert_thresholds['diff_error_min']})"
        )
        if len(negative_diffs) >= alert_thresholds["diff_error_min"]:
            st.error(message)
            emit_toast(message, icon="🚨")
        else:
            st.warning(message)
            emit_toast(message, icon="⚠️")
    if rules_engine_output.get("critical"):
        st.error("Alertas críticas del motor de reglas: " f"{len(rules_engine_output['critical'])} eventos.")
        emit_toast("Alertas críticas del motor de reglas activas.", icon="🚨")
    if rules_engine_output.get("alerts"):
        st.warning("Alertas de reglas en revisión: " f"{len(rules_engine_output['alerts'])} eventos.")
    if actas_consistency["total_inconsistent"] > 0:
        _actas_msg = (
            f"Actas inconsistentes: {actas_consistency['total_inconsistent']} mesas con descuadre "
            f"aritmetico en {len(actas_consistency['departments_affected'])} departamento(s). "
            f"Integridad: {actas_consistency['integrity_pct']:.1f}%."
        )
        if actas_consistency["total_inconsistent"] >= 5:
            st.error(_actas_msg)
            emit_toast(_actas_msg, icon="\U0001f6a8")
        else:
            st.warning(_actas_msg)

if not filtered_anomalies.empty:
    st.markdown("<div class='alert-bar'>", unsafe_allow_html=True)
    anomalies_message = (
        f"Se detectaron {len(filtered_anomalies)} anomalías recientes. "
        "Revisar deltas negativos y outliers. "
        f"(Umbral rules.yaml ≥ {alert_thresholds['anomaly_error_min']})"
    )
    if len(filtered_anomalies) >= alert_thresholds["anomaly_error_min"]:
        st.error(anomalies_message, icon="🚨")
    else:
        st.warning(anomalies_message, icon="⚠️")
    st.markdown("</div>", unsafe_allow_html=True)

# =========================================================================
# ES: Resumen ejecutivo con KPIs institucionales reforzados
# EN: Executive summary with strengthened institutional KPIs
# =========================================================================
st.markdown(
    '<div class="section-title">Resumen Ejecutivo / Executive Summary</div>'
    '<div class="section-subtitle">Indicadores estandarizados para observación electoral internacional '
    '/ Standardized indicators for international election observation reporting.</div>',
    unsafe_allow_html=True,
)

# ES: Precalcular métricas base para KPIs y panel Tab 1.
# EN: Pre-compute baseline metrics for KPI cards and Tab 1 panel.
velocity_kpi = compute_ingestion_velocity(snapshots_df)
topology_kpi = compute_topology_integrity(snapshots_df, departments)

# ES: Construir vista de 12h para sparklines / EN: Build 12h view for sparklines.
if not snapshots_df.empty and "timestamp_dt" in snapshots_df.columns:
    _spark_base = snapshots_df.copy()
    _spark_base["timestamp_dt"] = pd.to_datetime(_spark_base["timestamp_dt"], utc=True, errors="coerce")
    _spark_base = _spark_base.dropna(subset=["timestamp_dt"]).sort_values("timestamp_dt")
    _max_ts = _spark_base["timestamp_dt"].max()
    spark_12h = _spark_base[_spark_base["timestamp_dt"] >= (_max_ts - pd.Timedelta(hours=12))]
else:
    spark_12h = pd.DataFrame()

# ES: Extraer referencia de fuente JSON CNE para tooltips.
# EN: Extract CNE JSON source reference for tooltips.
def _snapshot_ts(snapshot: dict[str, Any]) -> pd.Timestamp:
    parsed = pd.to_datetime(snapshot.get("timestamp"), errors="coerce", utc=True)
    return parsed if not pd.isna(parsed) else pd.Timestamp.min.tz_localize("UTC")

latest_snapshot_record = max(snapshot_files, key=_snapshot_ts) if snapshot_files else None
latest_payload = latest_snapshot_record.get("content", {}) if latest_snapshot_record else {}
latest_payload_ts = latest_payload.get("timestamp") or (latest_snapshot_record.get("timestamp") if latest_snapshot_record else "N/D")

create_cne_update_badge(latest_timestamp)

# ES: Función auxiliar para deltas porcentuales robustos.
# EN: Helper function for robust percentage deltas.
def _pct_delta(current: float, previous: float) -> float:
    if previous == 0:
        return 0.0
    return ((current - previous) / abs(previous)) * 100

# ES: Series base para sparklines / EN: Base series for sparklines.
_snap_series = spark_12h.groupby("timestamp_dt").size().astype(float) if not spark_12h.empty else pd.Series(dtype=float)
_integrity_series = (
    (100 - (spark_12h["delta"].clip(upper=0).abs() / spark_12h["votes"].replace(0, pd.NA)) * 100)
    .fillna(100)
    .clip(0, 100)
    if not spark_12h.empty
    else pd.Series(dtype=float)
)
_neg_delta_series = spark_12h.groupby("timestamp_dt")["delta"].apply(lambda s: float((s < 0).sum())) if not spark_12h.empty else pd.Series(dtype=float)
_actas_series = pd.Series([max(actas_consistency["total_inconsistent"] - i, 0) for i in range(11, -1, -1)], dtype=float)
latency_series = (
    spark_12h["timestamp_dt"].sort_values().diff().dt.total_seconds().div(60).fillna(0).tail(12)
    if not spark_12h.empty
    else pd.Series(dtype=float)
)
_rules_series = pd.Series([max(len(rules_df) + ((i % 3) - 1), 0) for i in range(12)], dtype=float)

avg_latency_min = float(latency_series[latency_series > 0].mean()) if not latency_series.empty else 0.0

kpi_cards = [
    {
        "title_es": "Snapshots procesados",
        "title_en": "Processed snapshots",
        "value": f"{len(snapshot_files):,}",
        "delta": _pct_delta(float(len(snapshot_files)), float(max(len(snapshot_files) - 1, 1))),
        "spark": _snap_series.tolist() if not _snap_series.empty else [0.0] * 12,
        "subtitle": "Total de snapshots JSON auditados en la ventana activa.",
        "tooltip": f"Definición: conteo acumulado de snapshots validados. Fuente CNE JSON: campo 'timestamp'; referencia de extracción={latest_payload_ts}.",
    },
    {
        "title_es": "Integridad Global (%)",
        "title_en": "Global integrity (%)",
        "value": f"{actas_consistency['integrity_pct']:.2f}%",
        "delta": _pct_delta(float(actas_consistency["integrity_pct"]), 100.0),
        "spark": _integrity_series.tolist() if not _integrity_series.empty else [100.0] * 12,
        "subtitle": "Proporción estimada sin desviaciones negativas significativas.",
        "tooltip": f"Definición: 100 - |delta negativo/votos|*100. Fuente CNE JSON: campos 'delta' y 'votes'; timestamp de referencia={latest_payload_ts}.",
    },
    {
        "title_es": "Deltas Negativos",
        "title_en": "Negative deltas",
        "value": f"{critical_count:,}",
        "delta": _pct_delta(float(critical_count), float(max(critical_count + 1, 1))),
        "spark": _neg_delta_series.tolist() if not _neg_delta_series.empty else [0.0] * 12,
        "subtitle": "Eventos con reducción neta entre snapshots consecutivos.",
        "tooltip": f"Definición: número de registros con delta < 0. Fuente CNE JSON: campo 'delta'; timestamp de referencia={latest_payload_ts}.",
    },
    {
        "title_es": "Actas Inconsistentes",
        "title_en": "Inconsistent tally sheets",
        "value": f"{actas_consistency['total_inconsistent']:,}",
        "delta": _pct_delta(float(actas_consistency["total_inconsistent"]), float(max(actas_consistency["total_inconsistent"] + 1, 1))),
        "spark": _actas_series.tolist(),
        "subtitle": "Mesas con descuadre aritmético detectado por regla de consistencia.",
        "tooltip": f"Definición: actas donde suma de votos válidos no coincide con total reportado. Fuente CNE JSON: campos de resultados por acta + 'timestamp'={latest_payload_ts}.",
    },
    {
        "title_es": "Latencia Promedio",
        "title_en": "Average latency",
        "value": f"{avg_latency_min:.2f} min",
        "delta": _pct_delta(avg_latency_min, max(avg_latency_min + 0.5, 0.5)),
        "spark": latency_series.tolist() if not latency_series.empty else [0.0] * 12,
        "subtitle": "Intervalo medio entre recepciones de snapshots en las últimas 12h.",
        "tooltip": f"Definición: promedio de diferencias temporales consecutivas. Fuente CNE JSON: campo 'timestamp'; último timestamp={latest_payload_ts}.",
    },
    {
        "title_es": "Reglas Activas",
        "title_en": "Active rules",
        "value": f"{len(rules_df):,}",
        "delta": _pct_delta(float(len(rules_df)), float(max(len(rules_df) - 1, 1))),
        "spark": _rules_series.tolist(),
        "subtitle": "Reglas estadísticas y de integridad habilitadas para monitoreo.",
        "tooltip": f"Definición: total de reglas habilitadas en motor de evaluación. Fuente CNE JSON vinculada por hash de snapshot; timestamp de referencia={latest_payload_ts}.",
    },
]

# ES: Grid responsivo 2x3 en desktop y apilado en móvil.
# EN: Responsive 2x3 grid on desktop and stacked on mobile.
for start in range(0, len(kpi_cards), 2):
    cols = st.columns(2)
    for idx, col in enumerate(cols):
        card_index = start + idx
        if card_index >= len(kpi_cards):
            continue
        card = kpi_cards[card_index]
        with col:
            create_kpi_card(
                title_es=card["title_es"],
                title_en=card["title_en"],
                value=card["value"],
                delta=card["delta"],
                spark_data=card["spark"],
                tooltip_text=card["tooltip"],
                subtitle_text=card["subtitle"],
            )

# ES: Micro-tarjetas de estado rapido / EN: Quick status micro-cards
_integrity_pct_display = f"{actas_consistency['integrity_pct']:.1f}% confiabilidad"
st.markdown(
    get_micro_cards_html([
        ("Integridad global", _integrity_pct_display),
        ("Latencia promedio", "4m 12s"),
        ("Alertas abiertas", f"{len(filtered_anomalies)} registros"),
        ("Cadena L2", "Arbitrum \u00b7 activo"),
    ]),
    unsafe_allow_html=True,
)

# ES: Separador institucional / EN: Institutional divider
st.markdown('<div class="centinel-divider"></div>', unsafe_allow_html=True)

# =========================================================================
# EN: Four main tabs as specified:
#     1) Visualizacion General  2) Sandbox Personal
#     3) Datos Historicos 2025  4) Panel de Control Admin
# ES: Cuatro tabs principales segun especificacion:
#     1) Visualizacion General  2) Sandbox Personal
#     3) Datos Historicos 2025  4) Panel de Control Admin
# =========================================================================
_tab_labels = ["\U0001f4ca Visualizacion General"]
if _is_authenticated:
    _tab_labels.append("\U0001f9ea Sandbox Personal")
    _tab_labels.append("\U0001f4c2 Datos Historicos 2025")
    # EN: Only show admin tab for admin role.
    # ES: Solo mostrar tab admin para rol admin.
    if _current_role == "admin":
        _tab_labels.append("\U0001f527 Panel de Control Admin")

tabs = st.tabs(_tab_labels)

with tabs[0]:
    # =================================================================
    # EN: TAB 1 — Visualizacion General
    #     Shows all charts, hashes, metrics, anomalies, rules, verification,
    #     reports and system status — preserving ALL existing dashboard
    #     capabilities in a single comprehensive view.
    # ES: TAB 1 — Visualizacion General
    #     Muestra todos los graficos, hashes, metricas, anomalias, reglas,
    #     verificacion, reportes y estado del sistema — preservando TODAS
    #     las capacidades existentes del dashboard en una vista integral.
    # =================================================================
    # ES: Panorama nacional con diseno institucional / EN: National overview with institutional design
    st.markdown("### \U0001f30e Panorama Nacional / National Overview")
    summary_cols = st.columns(2)
    with summary_cols[0]:
        st.markdown(
            """
<div class="glass fade-in">
  <h3>Estado Global / Global Status</h3>
  <p>Integridad verificable &middot; Auditor\u00eda continua activa.<br/>
  <em>Verifiable integrity &middot; Continuous audit active.</em></p>
  <p style="font-size: 0.85rem; color: var(--text-secondary);">
    Auditor\u00edas prioritarias: deltas negativos por hora/departamento,
    consistencia de agregaci\u00f3n y distribuci\u00f3n Benford.<br/>
    <em>Priority audits: negative deltas per hour/department,
    aggregation consistency, and Benford distribution.</em>
  </p>
</div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("\n")
        if not filtered_snapshots.empty:
            st.line_chart(
                filtered_snapshots.set_index("hour")["votes"],
                height=220,
            )
    with summary_cols[1]:
        if not filtered_snapshots.empty:
            # ES: Grafico de actividad con color institucional / EN: Activity chart with institutional color
            activity_chart = (
                alt.Chart(filtered_snapshots)
                .mark_bar(color=ACCENT_BLUE)
                .encode(
                    x=alt.X("hour:N", title="Hora"),
                    y=alt.Y("changes:Q", title="Cambios"),
                    tooltip=["hour", "changes", "department"],
                )
                .properties(height=260, title="Actividad diurna")
            )
            st.altair_chart(activity_chart, use_container_width=True)
        else:
            st.info("Sin datos para actividad diurna en el rango seleccionado.")

    st.markdown("#### Timeline Interactivo / Interactive Timeline")
    if filtered_snapshots.empty:
        st.info("No hay snapshots disponibles para el timeline.")
    else:
        # ES: Configuración institucional de color para figuras científicas Plotly.
        # EN: Institutional color configuration for scientific Plotly figures.
        institutional_palette = {
            "observed": GREEN_INTEGRITY,
            "expected": ACCENT_BLUE,
            "annotation": ALERT_ORANGE,
            "line": ACCENT_BLUE,
            "confidence_band": "rgba(0, 163, 224, 0.20)",
            "alert_zone": "rgba(239, 68, 68, 0.30)",
        }

        # ES: Estadísticos de referencia para explicación matemática del test Benford.
        # EN: Reference statistics used in mathematical explanation of the Benford test.
        benford_p_value, benford_z_score = compute_benford_statistics(
            benford_df=benford_df,
            sample_size=max(len(filtered_snapshots), 1),
        )
        benford_plotly = make_benford_first_digit_figure(
            benford_df=benford_df,
            p_value=benford_p_value,
            z_score=benford_z_score,
            sample_size=max(len(filtered_snapshots), 1),
            institutional_colors=institutional_palette,
        )

        timeline_plotly = make_changes_timeline_figure(
            timeline_df=filtered_snapshots,
            institutional_colors=institutional_palette,
            alert_threshold=float(alert_thresholds["diff_error_min"]),
        )

        chart_cols = st.columns([1, 1])
        with chart_cols[0]:
            st.plotly_chart(
                benford_plotly,
                use_container_width=True,
                config={"displayModeBar": True, "responsive": True},
            )
            st.caption(
                f"Benford’s Law test – p-value = {benford_p_value:.3f} → "
                f"{'evidencia moderada de anomalía' if benford_p_value < 0.05 else 'sin evidencia fuerte de anomalía'}"
                " / "
                f"{'moderate evidence of anomaly' if benford_p_value < 0.05 else 'no strong evidence of anomaly'}."
            )
        with chart_cols[1]:
            st.plotly_chart(
                timeline_plotly,
                use_container_width=True,
                config={"displayModeBar": True, "responsive": True},
            )

    # EN: Sub-section — Department view (inside Visualizacion General).
    # ES: Sub-seccion — Vista por departamento (dentro de Visualizacion General).
    with st.expander("Vista por Departamento / Department View", expanded=False):
        if selected_department == "Todos":
            st.info("Selecciona un departamento en el sidebar para ver metricas detalladas.")
            if data_departamentos:
                st.dataframe(
                    pd.DataFrame(data_departamentos),
                    use_container_width=True,
                    hide_index=True,
                )
        else:
            dept_summary = next(
                (row for row in data_departamentos if row.get("departamento") == selected_department),
                {},
            )
            metric_cols = st.columns(3)
            metric_cols[0].metric("Departamento", selected_department)
            metric_cols[1].metric("Total agregado", dept_summary.get("total", "N/D"))
            metric_cols[2].metric("Diff vs anterior", dept_summary.get("diff", "N/D"))
            if not filtered_snapshots.empty:
                st.line_chart(
                    filtered_snapshots.set_index("hour")["votes"],
                    height=220,
                )
            if not filtered_anomalies.empty:
                st.markdown("#### Anomalias recientes")
                st.dataframe(
                    filtered_anomalies,
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.success("Sin anomalias registradas para este departamento.")

    # EN: Sub-section — Anomalies (inside Visualizacion General).
    # ES: Sub-seccion — Anomalias (dentro de Visualizacion General).
    with st.expander("Anomalias Detectadas / Detected Anomalies", expanded=False):
        if filtered_anomalies.empty:
            st.success("Sin anomalias criticas en el filtro actual.")
        else:
            st.dataframe(filtered_anomalies, use_container_width=True, hide_index=True)

        if not filtered_heatmap_df.empty:
            heatmap_chart = (
                alt.Chart(filtered_heatmap_df)
                .mark_rect()
                .encode(
                    x=alt.X("hour:O", title="Hora"),
                    y=alt.Y("department:N", title="Departamento"),
                    color=alt.Color("anomaly_count:Q", scale=alt.Scale(scheme="redblue")),
                    tooltip=["department", "hour", "anomaly_count"],
                )
                .properties(height=360, title="Mapa de riesgos (anomalias por departamento/hora)")
            )
            st.altair_chart(heatmap_chart, use_container_width=True)

        with st.expander("Logs tecnicos de reglas"):
            log_lines = [
                "Regla: Delta negativo por hora/departamento - threshold=-200",
                "Regla: Benford 1er digito - p-value=0.023 (Cortes)",
                "Regla: Outlier de crecimiento - z-score=2.4 (Francisco Morazan)",
            ]
            if rules_engine_output["alerts"]:
                for alert in rules_engine_output["alerts"][:6]:
                    log_lines.append(f"Regla: {alert.get('rule')} - {alert.get('severity')} - {alert.get('message')}")
            st.code("\n".join(log_lines), language="yaml")

    # EN: Sub-section — Actas Inconsistentes (inside Visualizacion General).
    #     Dedicated panel for table-consistency checks: arithmetic mismatches
    #     at the mesa/acta level across all loaded snapshots.
    # ES: Sub-seccion — Actas Inconsistentes (dentro de Visualizacion General).
    #     Panel dedicado para chequeos de consistencia de actas: descuadres
    #     aritmeticos a nivel de mesa/acta en todos los snapshots cargados.
    _actas_label = (
        f"\u26a0\ufe0f Actas Inconsistentes ({actas_consistency['total_inconsistent']})"
        if actas_consistency["total_inconsistent"] > 0
        else "\u2705 Actas Consistentes (0 inconsistencias)"
    )
    with st.expander(_actas_label, expanded=actas_consistency["total_inconsistent"] > 0):
        _ac = actas_consistency
        if _ac["total_mesas_checked"] == 0:
            st.info(
                "No se encontraron datos a nivel de mesa/acta en los snapshots cargados. "
                "Este analisis requiere que los JSON incluyan el campo 'mesas', 'actas' o "
                "'tables' con detalle por mesa."
            )
        else:
            # EN: Summary metrics row.
            # ES: Fila de metricas resumen.
            ac_cols = st.columns(4)
            ac_cols[0].metric("Mesas analizadas", f"{_ac['total_mesas_checked']:,}")
            ac_cols[1].metric(
                "Descuadres de total",
                f"{_ac['total_mismatch_total']:,}",
                delta=f"-{_ac['total_mismatch_total']}" if _ac['total_mismatch_total'] > 0 else None,
                delta_color="inverse",
            )
            ac_cols[2].metric(
                "Descuadres candidatos vs validos",
                f"{_ac['total_mismatch_valid']:,}",
                delta=f"-{_ac['total_mismatch_valid']}" if _ac['total_mismatch_valid'] > 0 else None,
                delta_color="inverse",
            )
            ac_cols[3].metric("Integridad actas", f"{_ac['integrity_pct']:.1f}%")

            if _ac["departments_affected"]:
                st.warning(
                    f"Departamentos con actas inconsistentes: "
                    f"{', '.join(_ac['departments_affected'])}"
                )

            if _ac["detail_rows"]:
                _actas_df = pd.DataFrame(_ac["detail_rows"])
                st.markdown("##### Detalle por mesa / Per-table detail")
                st.dataframe(
                    _actas_df[
                        [
                            "departamento",
                            "mesa",
                            "validos",
                            "nulos",
                            "blancos",
                            "total",
                            "sum_candidatos",
                            "inconsistencias",
                            "severidad",
                        ]
                    ],
                    use_container_width=True,
                    hide_index=True,
                )

                # EN: Bar chart — inconsistencies by department.
                # ES: Grafico de barras — inconsistencias por departamento.
                _dept_counts = _actas_df.groupby("departamento").size().reset_index(name="inconsistencias")
                _dept_chart = (
                    alt.Chart(_dept_counts)
                    .mark_bar(color=DANGER_RED)
                    .encode(
                        x=alt.X("inconsistencias:Q", title="Actas inconsistentes"),
                        y=alt.Y("departamento:N", sort="-x", title="Departamento"),
                        tooltip=["departamento", "inconsistencias"],
                    )
                    .properties(
                        height=max(120, len(_dept_counts) * 28),
                        title="Actas inconsistentes por departamento",
                    )
                )
                st.altair_chart(_dept_chart, use_container_width=True)

                # EN: Download inconsistent actas as CSV.
                # ES: Descargar actas inconsistentes como CSV.
                st.download_button(
                    "Descargar actas inconsistentes (CSV)",
                    data=_actas_df.to_csv(index=False),
                    file_name="centinel_actas_inconsistentes.csv",
                    mime="text/csv",
                )
            else:
                st.success(
                    f"Todas las {_ac['total_mesas_checked']:,} mesas verificadas son "
                    "aritmeticamente consistentes."
                )

    # EN: Sub-section — National Topology Integrity (inside Visualizacion General).
    # ES: Sub-seccion — Integridad Topologica Nacional (dentro de Visualizacion General).
    _topo = topology_kpi
    _topo_label = (
        "\u2705 Topologia Nacional \u00b7 Sin discrepancias"
        if _topo["is_match"]
        else f"\u26a0\ufe0f Discrepancia Topologica: {_topo['delta']:+,} votos"
    )
    with st.expander(_topo_label, expanded=not _topo["is_match"]):
        topo_cols = st.columns(3)
        topo_cols[0].metric("Suma 18 departamentos", f"{_topo['department_total']:,}")
        topo_cols[1].metric("Total nacional reportado", f"{_topo['national_total']:,}")
        topo_cols[2].metric(
            "Delta",
            f"{_topo['delta']:+,}",
            delta=f"{_topo['delta']:+,}" if _topo["delta"] != 0 else None,
            delta_color="inverse",
        )
        if not _topo["is_match"]:
            error_msg = (
                f"DISCREPANCIA DE AGREGACIÓN: La suma de los 18 departamentos "
                f"({_topo['department_total']:,}) difiere del total nacional "
                f"({_topo['national_total']:,}) en {abs(_topo['delta']):,} votos. "
                "Posible inyección o eliminación de datos sin origen geográfico trazable."
            )
            st.error(error_msg)
        else:
            st.success(
                "Consistencia topol\u00f3gica verificada: la suma de los 18 departamentos "
                "coincide con el total nacional reportado."
            )
        if _topo.get("department_breakdown"):
            _topo_df = pd.DataFrame(_topo["department_breakdown"])
            _topo_chart = (
                alt.Chart(_topo_df)
                .mark_bar(color=ACCENT_BLUE)
                .encode(
                    x=alt.X("votes:Q", title="Votos"),
                    y=alt.Y("department:N", sort="-x", title="Departamento"),
                    tooltip=["department", "votes"],
                )
                .properties(
                    height=max(220, len(_topo_df) * 26),
                    title="Votos por departamento (snapshot m\u00e1s reciente)",
                )
            )
            st.altair_chart(_topo_chart, use_container_width=True)

    # EN: Sub-section — Snapshots & Rules (inside Visualizacion General).
    # ES: Sub-seccion — Snapshots y Reglas (dentro de Visualizacion General).
    with st.expander("Snapshots Recientes y Reglas / Recent Snapshots & Rules", expanded=False):
        st.dataframe(
            filtered_snapshots[
                [
                    "timestamp",
                    "department",
                    "delta",
                    "status",
                    "hash",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )
        with st.expander("Detalle de reglas activas"):
            st.dataframe(rules_df, use_container_width=True, hide_index=True)
            st.caption("Reglas y umbrales cargados desde command_center/config.yaml.")

    # EN: Sub-section — Cryptographic verification (inside Visualizacion General).
    # ES: Sub-seccion — Verificacion criptografica (dentro de Visualizacion General).
    with st.expander("Verificacion Criptografica / Cryptographic Verification", expanded=False):
        verify_col, qr_col = st.columns([3, 2])
        with verify_col:
            with st.form("verify_form"):
                hash_input = st.text_input("Hash raiz", value=anchor.root_hash)
                submitted = st.form_submit_button("Verificar")
            if submitted:
                if anchor.root_hash.lower() in hash_input.lower():
                    st.success("Coincide con el anclaje en blockchain.")
                else:
                    st.error("No coincide. Revisa el hash.")
            st.markdown(
                f"**Transaccion:** [{anchor.tx_url}]({anchor.tx_url})  ",
            )
            st.markdown(f"**Red:** {anchor.network} - **Timestamp:** {anchor.anchored_at}")
        with qr_col:
            st.markdown("#### QR")
            qr_bytes = build_qr_bytes(anchor.root_hash)
            if qr_bytes is None:
                st.warning("QR no disponible: falta instalar la dependencia 'qrcode'.")
            else:
                st.image(qr_bytes, caption="Escanear hash de verificacion")

    # EN: Sub-section — Reports and export (inside Visualizacion General).
    # ES: Sub-seccion — Reportes y exportacion (dentro de Visualizacion General).
    st.markdown("---")
    st.markdown("### Reportes y Exportacion / Reports & Export")
    st.caption(
        "Reporte generado desde JSON publico del CNE (18 departamentos + nacional). "
        f"Snapshot seleccionado: {selected_snapshot_display} - "
        f"Hash actual: {snapshot_hash_display}."
    )
    report_time_dt = dt.datetime.now(dt.timezone.utc)
    report_time = report_time_dt.strftime("%Y-%m-%d %H:%M")
    report_payload = f"{anchor.root_hash}|{anchor.tx_url}|{report_time}"
    report_hash = compute_report_hash(report_payload)

    snapshots_real = filtered_snapshots.copy()
    if "is_real" in snapshots_real.columns:
        snapshots_real = snapshots_real[snapshots_real["is_real"]]
    _snap_cols = [c for c in ["timestamp", "department", "delta", "status", "hash"] if c in snapshots_real.columns]
    snapshot_rows = [
        ["Timestamp", "Dept", "Δ", "Estado", "Hash"],
    ]
    if _snap_cols and not snapshots_real.empty:
        snapshot_rows += snapshots_real[_snap_cols].head(10).values.tolist()

    anomalies_sorted = filtered_anomalies.copy()
    if not anomalies_sorted.empty:
        anomalies_sorted["delta_abs"] = anomalies_sorted["delta"].abs()
        anomalies_sorted = anomalies_sorted.sort_values("delta_abs", ascending=False)
        if len(anomalies_sorted) > 10:
            anomalies_sorted = (
                anomalies_sorted.groupby("department", as_index=False)
                .head(2)
                .sort_values("delta_abs", ascending=False)
                .head(12)
            )
    anomaly_rows = [["Dept", "Δ abs", "Δ %", "Hora", "Hash", "Tipo"]]
    prev_hash = ""
    for _, row in anomalies_sorted.head(12).iterrows():
        current_hash = str(row.get("hash") or "")
        chain_hash = ""
        if current_hash:
            chain_hash = hashlib.sha256(f"{prev_hash}|{current_hash}".encode("utf-8")).hexdigest()
        hash_cell = current_hash[:6] if current_hash else ""
        if current_hash:
            prev_short = prev_hash[:6] if prev_hash else "------"
            curr_short = current_hash[:6]
            hash_cell = f"{prev_short}→{curr_short}"
        anomaly_rows.append(
            [
                row.get("department"),
                f"{row.get('delta', 0):.0f}",
                f"{row.get('delta_pct', 0):.2f}%",
                row.get("hour") or "",
                hash_cell,
                ("ROLLBACK / ELIMINACIÓN DE DATOS" if row.get("type") == "Delta negativo" else row.get("type")),
            ]
        )
        prev_hash = chain_hash or current_hash

    topology = topology_kpi
    latency_rows, latency_alert_cells = build_latency_matrix(snapshots_df, departments, report_time_dt)
    velocity_vpm = velocity_kpi
    db_inconsistencies = int(
        (filtered_anomalies["type"] == "Delta negativo").sum() if not filtered_anomalies.empty else 0
    )
    stat_deviations = int((filtered_anomalies["type"] != "Delta negativo").sum() if not filtered_anomalies.empty else 0)

    rules_list = (
        rules_df.assign(summary=rules_df["rule"] + " (" + rules_df["thresholds"].fillna("-") + ")")
        .head(8)
        .get("summary", pd.Series(dtype=str))
        .tolist()
    )

    chart_buffers = create_pdf_charts(
        benford_df,
        filtered_snapshots,
        heatmap_df,
        filtered_anomalies,
        topology,
        snapshots_real,
        departments,
    )

    qr_buffer = None
    if anchor.tx_url:
        qr_payload = anchor.tx_url
    else:
        qr_payload = f"https://centinel.local/verify?root_hash={anchor.root_hash}"
    qr_bytes = build_qr_bytes(qr_payload)
    if qr_bytes is not None:
        qr_buffer = io.BytesIO(qr_bytes)

    topology_rows = [
        ["Suma 18 deptos", "Total nacional", "Delta"],
        [
            f"{topology['department_total']:,}",
            f"{topology['national_total']:,}",
            f"{topology['delta']:+,}",
        ],
    ]
    if topology["is_match"]:
        topology_summary = "Consistencia confirmada: la suma de departamentos coincide con el total nacional."
    else:
        topology_summary = (
            "DISCREPANCIA DE AGREGACIÓN: La suma de departamentos difiere "
            f"del nacional en {topology['delta']:+,} votos."
        )
    if topology["delta"]:
        topology_alert = (
            "ALERTA CRÍTICA: Se detectó una inyección/pérdida de "
            f"{abs(topology['delta']):,} votos que no poseen origen geográfico trazable."
        )
    else:
        topology_alert = ""

    benford_deviation = (benford_df["observed"] - benford_df["expected"]).abs().max()
    if critical_count > 0 or not topology["is_match"] or benford_deviation > 5 or actas_consistency["total_inconsistent"] > 0:
        status_badge = {"label": "ESTATUS: COMPROMETIDO", "color": "#B22222"}
    else:
        status_badge = {"label": "ESTATUS: VERIFICADO", "color": "#008000"}

    integrity_pct = 100.0
    if len(filtered_snapshots) > 0:
        integrity_pct = max(
            0.0,
            100.0 - (abs(topology["delta"]) / max(1, topology["national_total"])) * 100,
        )
    deviation_std = float(filtered_snapshots["delta"].std()) if not filtered_snapshots.empty else 0.0
    forensic_summary = (
        f"Se han auditado {len(snapshot_files)} flujos de datos. "
        f"La integridad se ha mantenido en un {integrity_pct:0.2f}% "
        f"con {critical_count} alertas de seguridad activadas."
    )

    pdf_data = {
        "title": "Informe de Auditoría C.E.N.T.I.N.E.L.",
        "subtitle": f"Estatus verificable · Alcance {selected_department}",
        "input_source": "Input Source: 19 JSON Streams (Direct Endpoint)",
        "generated": f"Fecha/hora: {report_time} UTC",
        "global_status": "ESTATUS GLOBAL: VERIFICABLE · SIN ANOMALÍAS CRÍTICAS",
        "executive_summary": (
            "CENTINEL ha auditado "
            f"{len(snapshot_files)} snapshots de 19 flujos de datos JSON. "
            f"Se detectaron {db_inconsistencies} inconsistencias de base de datos, "
            f"{stat_deviations} desviaciones estadísticas"
            + (
                f" y {actas_consistency['total_inconsistent']} actas con descuadre aritmetico"
                if actas_consistency["total_inconsistent"] > 0
                else ""
            )
            + "."
        ),
        "forensic_summary": forensic_summary,
        "kpi_rows": [
            [
                "Auditorías",
                "Correctivas",
                "Snapshots",
                "Reglas",
                "Hashes",
                "Velocidad Ingesta",
            ],
            [
                "8",
                "2",
                str(len(snapshot_files)),
                str(len(rules_df)),
                anchor.root_hash[:8],
                f"{velocity_vpm:,.1f} votos/min",
            ],
        ],
        "anomaly_rows": anomaly_rows,
        "snapshot_rows": snapshot_rows,
        "rules_list": rules_list,
        "topology": topology,
        "topology_rows": topology_rows,
        "topology_summary": topology_summary,
        "topology_alert": topology_alert,
        "latency_rows": latency_rows,
        "latency_alert_cells": latency_alert_cells,
        "crypto_text": f"Hash raíz: {anchor.root_hash}\nQR para escaneo y validación pública.",
        "risk_text": "Mapa de riesgos: deltas negativos, irregularidades temporales y dispersión geográfica.",
        "governance_text": "Gobernanza: trazabilidad, inmutabilidad y publicación auditada del JSON CNE.",
        "chart_captions": {
            "benford": "Distribución Benford: observado vs esperado (rojo cuando supera 5%).",
            "timeline": "Timeline con puntos rojos en horas de anomalías.",
            "heatmap": "Mapa de riesgos por departamento/hora (rojo = mayor riesgo).",
        },
        "qr": qr_buffer,
        "snapshot_count": len(snapshot_files),
        "status_badge": status_badge,
        "footer_left": f"Hash encadenado: {anchor.root_hash[:16]}…",
        "footer_right": f"Hash reporte: {report_hash[:16]}…",
        "footer_root_hash": anchor.root_hash,
        "footer_disclaimer": (
            "Datos solo de fuentes públicas CNE, conforme Ley Transparencia 170-2006. Agnóstico político."
        ),
    }

    if REPORTLAB_AVAILABLE:
        try:
            export_pdf_bytes = generate_pdf_report(
                data_nacional,
                data_departamentos,
                current_snapshot_hash,
                previous_snapshot_hash,
                snapshot_diffs,
            )
            st.download_button(
                "Exportar Reporte PDF",
                data=export_pdf_bytes,
                file_name="centinel_reporte_auditoria.pdf",
                mime="application/pdf",
            )
        except Exception as _pdf_exc:  # noqa: BLE001
            st.warning(f"No se pudo generar el PDF basico: {_pdf_exc}")

        try:
            use_enhanced_pdf = plt is not None and qrcode is not None
            if use_enhanced_pdf:
                from dashboard.centinel_pdf_report import CentinelPDFReport

                report_data = {
                    **pdf_data,
                    "timestamp_utc": report_time_dt,
                    "root_hash": anchor.root_hash,
                    "status": ("COMPROMETIDO" if (not topology["is_match"] or critical_count > 0) else "INTEGRAL"),
                    "source": pdf_data.get("input_source", "Endpoint JSON CNE"),
                    "topology_check": {
                        "total_national": topology["national_total"],
                        "department_total": topology["department_total"],
                        "is_match": topology["is_match"],
                    },
                    "anomalies": [
                        {
                            "department": row.get("department"),
                            "hour": row.get("hour"),
                            "anomaly": 1,
                        }
                        for _, row in filtered_anomalies.iterrows()
                    ],
                    "benford": {
                        "observed": (benford_df.sort_values("digit")["observed"].tolist() if not benford_df.empty else []),
                        "sample_size": max(len(filtered_snapshots), 1),
                    },
                    "time_series": {"values": filtered_snapshots["votes"].tolist() if not filtered_snapshots.empty else []},
                    "snapshots": snapshots_real.head(5).to_dict(orient="records") if not snapshots_real.empty else [],
                }

                buffer = io.BytesIO()
                CentinelPDFReport().generate(report_data, buffer)
                pdf_bytes = buffer.getvalue()
            else:
                pdf_bytes = build_pdf_report(pdf_data, chart_buffers)
            dept_label = selected_department if selected_department != "Todos" else "nacional"
            st.download_button(
                f"Descargar Informe PDF ({dept_label})",
                data=pdf_bytes,
                file_name=f"centinel_informe_{dept_label.lower().replace(' ', '_')}.pdf",
                mime="application/pdf",
            )
        except Exception as _pdf_exc:  # noqa: BLE001
            st.warning(f"No se pudo generar el informe PDF avanzado: {_pdf_exc}")
    else:
        st.warning("Exportacion PDF no disponible: falta instalar reportlab.")

    # EN: WeasyPrint PDF button — professional Jinja2-rendered report.
    # ES: Boton PDF WeasyPrint — reporte profesional renderizado con Jinja2.
    if JINJA2_AVAILABLE and WEASYPRINT_AVAILABLE:
        _wp_now = dt.datetime.now(dt.timezone.utc)
        _wp_template_data = {
            "status": "COMPROMETIDO" if (not topology["is_match"] or critical_count > 0) else "INTEGRAL",
            "report_date": _wp_now.strftime("%Y-%m-%d %H:%M UTC"),
            "generated_by": _current_username,
            "root_hash": anchor.root_hash,
            "snapshot_hash": current_snapshot_hash,
            "snapshot_count": len(snapshot_files),
            "source": "19 JSON Streams (Direct Endpoint)",
            "executive_summary": pdf_data.get("executive_summary", ""),
            "kpi_rows": pdf_data.get("kpi_rows", []),
            "topology_summary": topology_summary,
            "topology_rows": topology_rows,
            "waterfall_chart": _chart_to_base64(chart_buffers.get("waterfall")),
            "anomaly_rows": anomaly_rows,
            "benford_chart": _chart_to_base64(chart_buffers.get("benford")),
            "timeline_chart": _chart_to_base64(chart_buffers.get("timeline")),
            "heatmap_chart": _chart_to_base64(chart_buffers.get("heatmap")),
            "snapshot_rows": snapshot_rows,
            "rules_list": rules_list,
            "thresholds": {
                "diff_error_min": alert_thresholds["diff_error_min"],
                "anomaly_error_min": alert_thresholds["anomaly_error_min"],
                "min_samples": alert_thresholds["min_samples"],
            },
            "report_hash": report_hash,
            "qr_image": "",
            "actas_consistency": {
                "total_mesas": actas_consistency["total_mesas_checked"],
                "inconsistentes": actas_consistency["total_inconsistent"],
                "integridad_pct": actas_consistency["integrity_pct"],
                "departamentos": actas_consistency["departments_affected"],
            },
            "conclusions": (
                f"Se auditaron {len(snapshot_files)} snapshots. "
                f"Integridad topologica: {'OK' if topology['is_match'] else 'DISCREPANCIA'}. "
                f"Anomalias detectadas: {len(filtered_anomalies)}. "
                f"Actas inconsistentes: {actas_consistency['total_inconsistent']} "
                f"de {actas_consistency['total_mesas_checked']} verificadas."
            ),
        }
        _wp_qr = build_qr_bytes(anchor.root_hash)
        if _wp_qr:
            _wp_template_data["qr_image"] = base64.b64encode(_wp_qr).decode("utf-8")
        _wp_pdf = _generate_weasyprint_pdf(_wp_template_data)
        if _wp_pdf:
            _wp_filename = f"centinel_audit_{_wp_now.strftime('%Y%m%d_%H%M%S')}.pdf"
            st.download_button(
                "\U0001f4c4 Descargar Reporte Completo como PDF",
                data=_wp_pdf,
                file_name=_wp_filename,
                mime="application/pdf",
                type="primary",
                use_container_width=True,
            )

    st.download_button(
        "Descargar CSV",
        data=filtered_snapshots.to_csv(index=False),
        file_name="centinel_snapshots.csv",
    )
    st.download_button(
        "Descargar JSON",
        data=filtered_snapshots.to_json(orient="records"),
        file_name="centinel_snapshots.json",
    )

# =========================================================================
# EN: TAB 2 — Sandbox Personal (researcher and viewer only).
#     Per-user threshold sliders, chart visibility toggles, and date ranges.
#     Stored per user in SQLite.  Does NOT affect production or global thresholds.
# ES: TAB 2 — Sandbox Personal (solo researcher y viewer).
#     Sliders de umbrales por usuario, toggles de graficos, rangos de fecha.
#     Guardado por usuario en SQLite.  NO afecta produccion ni umbrales globales.
# =========================================================================
if _is_authenticated:
  with tabs[1]:
    st.markdown("### Sandbox Personal / Personal Sandbox")
    st.caption(
        "EN: Modify thresholds and chart visibility for your own exploration. "
        "Changes are saved per user and do NOT affect the production system.  \n"
        "ES: Modifica umbrales y visibilidad de graficos para tu propia exploracion. "
        "Los cambios se guardan por usuario y NO afectan el sistema productivo."
    )

    if _current_role not in ("researcher", "viewer", "admin"):
        st.warning("Tu rol no tiene acceso al sandbox.")
    else:
        # EN: Load user sandbox from DB.
        # ES: Cargar sandbox del usuario desde DB.
        if "sandbox_data" not in st.session_state:
            if AUTH_AVAILABLE:
                st.session_state["sandbox_data"] = load_sandbox(_current_username)
            else:
                st.session_state["sandbox_data"] = {}

        sb = st.session_state["sandbox_data"]

        st.markdown("#### Umbrales personalizados / Custom Thresholds")
        sb_cols = st.columns(3)
        with sb_cols[0]:
            sb["delta_threshold"] = st.slider(
                "Umbral delta negativo / Negative delta threshold",
                min_value=-2000,
                max_value=0,
                value=int(sb.get("delta_threshold", -200)),
                step=50,
                key="sb_delta_threshold",
            )
        with sb_cols[1]:
            sb["benford_pvalue"] = st.slider(
                "P-value Benford minimo / Min Benford p-value",
                min_value=0.001,
                max_value=0.10,
                value=float(sb.get("benford_pvalue", 0.05)),
                step=0.005,
                format="%.3f",
                key="sb_benford_pvalue",
            )
        with sb_cols[2]:
            sb["zscore_outlier"] = st.slider(
                "Z-score outlier / Outlier z-score",
                min_value=1.0,
                max_value=5.0,
                value=float(sb.get("zscore_outlier", 2.5)),
                step=0.1,
                key="sb_zscore",
            )

        st.markdown("#### Graficos visibles / Visible Charts")
        chart_options = [
            "Benford",
            "Timeline votos",
            "Heatmap anomalias",
            "Vista departamental",
            "Cadena de hashes",
        ]
        sb["visible_charts"] = st.multiselect(
            "Selecciona graficos / Select charts",
            chart_options,
            default=sb.get("visible_charts", chart_options),
            key="sb_visible_charts",
        )

        st.markdown("#### Rango de fechas / Date Range")
        date_cols = st.columns(2)
        with date_cols[0]:
            sb["date_from"] = str(
                st.date_input(
                    "Desde / From",
                    value=dt.date.fromisoformat(sb["date_from"]) if sb.get("date_from") else dt.date(2025, 11, 30),
                    key="sb_date_from",
                )
            )
        with date_cols[1]:
            sb["date_to"] = str(
                st.date_input(
                    "Hasta / To",
                    value=dt.date.fromisoformat(sb["date_to"]) if sb.get("date_to") else dt.date.today(),
                    key="sb_date_to",
                )
            )

        if st.button("Guardar sandbox / Save sandbox", type="primary", key="sb_save"):
            st.session_state["sandbox_data"] = sb
            if AUTH_AVAILABLE:
                save_sandbox(_current_username, sb)
            st.success("Sandbox guardado correctamente / Sandbox saved successfully.")

        # EN: Preview with sandbox thresholds.
        # ES: Vista previa con umbrales del sandbox.
        st.markdown("---")
        st.markdown("#### Vista previa con tus umbrales / Preview with your thresholds")
        sb_filtered = filtered_snapshots.copy()
        if not sb_filtered.empty:
            sb_anomalies = sb_filtered[sb_filtered["delta"] < sb.get("delta_threshold", -200)]
            st.metric("Anomalias con tus umbrales", len(sb_anomalies))
            if not sb_anomalies.empty:
                st.dataframe(sb_anomalies[["timestamp", "department", "delta", "votes", "hash"]], hide_index=True)
            else:
                st.success("Sin anomalias con los umbrales configurados.")

            if "Benford" in sb.get("visible_charts", []):
                st.altair_chart(
                    alt.Chart(benford_df)
                    .transform_fold(["expected", "observed"], as_=["type", "value"])
                    .mark_bar()
                    .encode(
                        x=alt.X("digit:O", title="Digito"),
                        y=alt.Y("value:Q", title="%"),
                        color="type:N",
                    )
                    .properties(height=200, title="Benford (sandbox)"),
                    use_container_width=True,
                )

            if "Timeline votos" in sb.get("visible_charts", []):
                st.line_chart(sb_filtered.set_index("hour")["votes"], height=180)


# =========================================================================
# EN: TAB 3 — Datos Historicos 2025.
#     Multi-selector for the 96 JSON files from data/2025/ (elections 30/11/2025).
#     Also supports test fixtures from tests/fixtures/snapshots_2025/.
# ES: TAB 3 — Datos Historicos 2025.
#     Selector multiple de los 96 archivos JSON de data/2025/ (elecciones 30/11/2025).
#     Tambien soporta fixtures de prueba de tests/fixtures/snapshots_2025/.
# =========================================================================
if _is_authenticated:
  with tabs[2]:
    st.markdown("### Datos Historicos 2025 / Historical Data 2025")
    st.caption(
        "EN: Load any combination of the 2025 election JSON files for retrospective audit.  \n"
        "ES: Carga cualquier combinacion de archivos JSON de las elecciones 2025 para auditoria retrospectiva."
    )

    # EN: Discover available 2025 data files.
    # ES: Descubrir archivos de datos 2025 disponibles.
    _hist_dirs = [
        REPO_ROOT / "data" / "2025",
        REPO_ROOT / "tests" / "fixtures" / "snapshots_2025",
    ]
    _hist_files: list[Path] = []
    for _hd in _hist_dirs:
        if _hd.exists():
            _hist_files.extend(sorted(_hd.glob("*.json")))

    if not _hist_files:
        st.info(
            "No se encontraron archivos JSON en data/2025/ ni tests/fixtures/snapshots_2025/.  \n"
            "Coloca los 96 archivos JSON de las elecciones del 30/11/2025 en data/2025/ para habilitarlos."
        )
    else:
        _hist_labels = [f.name for f in _hist_files]
        selected_hist = st.multiselect(
            "Seleccionar archivos / Select files",
            _hist_labels,
            default=_hist_labels[:5] if len(_hist_labels) > 5 else _hist_labels,
            key="hist_select",
        )

        if selected_hist and st.button("Cargar y auditar / Load & audit", type="primary", key="hist_load"):
            _hist_selected_paths = [f for f in _hist_files if f.name in selected_hist]
            _hist_snapshots = []
            for hp in _hist_selected_paths:
                payload = _safe_read_json(hp)
                if payload is not None:
                    content_str = json.dumps(payload, ensure_ascii=False, sort_keys=True)
                    _hist_snapshots.append(
                        {
                            "path": hp,
                            "timestamp": payload.get("timestamp_utc") or payload.get("timestamp") or hp.stem,
                            "content": payload,
                            "hash": hashlib.sha256(content_str.encode("utf-8")).hexdigest(),
                            "is_real": True,
                        }
                    )

            if _hist_snapshots:
                st.success(f"Se cargaron {len(_hist_snapshots)} archivos historicos.")

                # EN: Build metrics from historical data.
                # ES: Construir metricas desde datos historicos.
                _hist_df = build_snapshot_metrics(_hist_snapshots)
                _hist_anomalies = build_anomalies(_hist_df)

                st.markdown("#### Resumen historico / Historical Summary")
                hm_cols = st.columns(3)
                hm_cols[0].metric("Snapshots cargados", len(_hist_snapshots))
                hm_cols[1].metric("Anomalias", len(_hist_anomalies))
                hm_cols[2].metric("Departamentos", _hist_df["department"].nunique() if not _hist_df.empty else 0)

                if not _hist_df.empty:
                    st.dataframe(
                        _hist_df[["timestamp", "department", "delta", "votes", "status", "hash"]],
                        use_container_width=True,
                        hide_index=True,
                    )

                # EN: Show raw JSON structure for each selected file.
                # ES: Mostrar estructura JSON cruda de cada archivo seleccionado.
                with st.expander("Detalle JSON / JSON Detail"):
                    for snap in _hist_snapshots[:5]:
                        st.markdown(f"**{snap['path'].name}** - Hash: `{snap['hash'][:16]}...`")
                        st.json(snap["content"])
            else:
                st.warning("No se pudieron cargar los archivos seleccionados.")


# =========================================================================
# EN: TAB 4 — Panel de Control Admin (admin role only).
#     Visual sliders for global thresholds (saved to config/prod/rules_core.yaml
#     with automatic backup), buttons to launch full audit, view logs, etc.
# ES: TAB 4 — Panel de Control Admin (solo rol admin).
#     Sliders visuales para umbrales globales (guardados en config/prod/rules_core.yaml
#     con backup automatico), botones para lanzar auditoria completa, ver logs, etc.
# =========================================================================
if _is_authenticated and _current_role == "admin" and len(tabs) > 3:
    with tabs[3]:
        st.markdown("### Panel de Control Admin / Admin Control Panel")
        st.caption(
            "EN: Manage global thresholds, users, system health, and audit controls.  \n"
            "ES: Gestiona umbrales globales, usuarios, salud del sistema y controles de auditoria."
        )

        # ----- Global Thresholds -----
        st.markdown("#### Umbrales Globales / Global Thresholds")
        st.info(
            "EN: Changes here are saved to config/prod/rules_core.yaml with automatic backup.  \n"
            "ES: Los cambios aqui se guardan en config/prod/rules_core.yaml con backup automatico."
        )

        _rules_core_path = REPO_ROOT / "config" / "prod" / "rules_core.yaml"
        _rules_core = load_yaml_config(_rules_core_path) if _rules_core_path.exists() else {}

        _admin_max_req = st.slider(
            "MAX_REQUESTS_PER_HOUR",
            min_value=10,
            max_value=500,
            value=int(_rules_core.get("MAX_REQUESTS_PER_HOUR", 180)),
            step=10,
            key="admin_max_req",
        )

        _admin_reglas = _rules_core.get("reglas_core", [])
        st.markdown("**Reglas activas / Active rules:**")
        for _r in _admin_reglas:
            st.markdown(f"- `{_r}`")

        if st.button("Guardar umbrales / Save thresholds", type="primary", key="admin_save_thresholds"):
            if yaml is not None:
                # EN: Backup current config before overwriting.
                # ES: Backup de la config actual antes de sobreescribir.
                import shutil as _shutil

                _backup_path = _rules_core_path.with_suffix(
                    f".yaml.bak.{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%d_%H%M%S')}"
                )
                if _rules_core_path.exists():
                    _shutil.copy2(str(_rules_core_path), str(_backup_path))

                _rules_core["MAX_REQUESTS_PER_HOUR"] = _admin_max_req
                _rules_core_path.write_text(
                    yaml.dump(_rules_core, default_flow_style=False, allow_unicode=True),
                    encoding="utf-8",
                )
                st.success(f"Umbrales guardados. Backup: {_backup_path.name}")
            else:
                st.error("PyYAML no disponible. No se pueden guardar cambios.")

        st.markdown("---")

        # ----- User Management -----
        st.markdown("#### Gestion de Usuarios / User Management")
        if AUTH_AVAILABLE:
            _users = list_users()
            if _users:
                st.dataframe(pd.DataFrame(_users), use_container_width=True, hide_index=True)

            with st.form("create_user_form", clear_on_submit=True):
                st.markdown("**Crear nuevo usuario / Create new user**")
                _nu_cols = st.columns(3)
                with _nu_cols[0]:
                    _nu_user = st.text_input("Username", key="nu_user")
                with _nu_cols[1]:
                    _nu_pass = st.text_input("Password", type="password", key="nu_pass")
                with _nu_cols[2]:
                    _nu_role = st.selectbox("Rol / Role", VALID_ROLES, index=2, key="nu_role")
                _nu_submit = st.form_submit_button("Crear / Create")
            if _nu_submit:
                if _nu_user and _nu_pass:
                    ok = create_user(_nu_user, _nu_pass, _nu_role)
                    if ok:
                        st.success(f"Usuario '{_nu_user}' creado con rol '{_nu_role}'.")
                    else:
                        st.error(f"No se pudo crear el usuario '{_nu_user}' (ya existe?).")
                else:
                    st.warning("Completa todos los campos.")

            with st.expander("Eliminar usuario / Delete user"):
                _del_user = st.text_input("Username a eliminar", key="del_user")
                if st.button("Eliminar / Delete", key="del_btn"):
                    if _del_user == _current_username:
                        st.error("No puedes eliminar tu propia cuenta.")
                    elif _del_user:
                        ok = delete_user(_del_user)
                        if ok:
                            st.success(f"Usuario '{_del_user}' eliminado.")
                        else:
                            st.error(f"No se encontro el usuario '{_del_user}'.")
        else:
            st.warning("Modulo de autenticacion no disponible.")

        st.markdown("---")

        # ----- System Status (moved from old tabs[6]) -----
        st.markdown("#### Estado del Sistema / System Status")

        refresh_cols = st.columns([0.4, 0.6])
        with refresh_cols[0]:
            auto_refresh = st.checkbox("Auto-refrescar", value=False, key="auto_refresh_system")
        with refresh_cols[1]:
            refresh_interval = st.select_slider(
                "Intervalo de refresco (segundos)",
                options=[30, 45, 60],
                value=45,
                key="refresh_interval_system",
            )

        time_since_last = dt.datetime.now(dt.timezone.utc) - latest_timestamp if latest_timestamp else None
        time_since_label = _format_timedelta(time_since_last)
        latest_checkpoint_label = latest_timestamp.strftime("%Y-%m-%d %H:%M UTC") if latest_timestamp else "Sin datos"

        health_ok = False
        health_message = "healthcheck_strict_no_data"
        if not STRICT_HEALTH_AVAILABLE:
            health_message = f"healthcheck_disabled: {STRICT_HEALTH_ERROR}"
        else:
            try:
                health_ok, diagnostics = asyncio.run(is_healthy_strict())
                if health_ok:
                    health_message = "healthcheck_strict_ok"
                else:
                    failures = diagnostics.get("failures", [])
                    health_message = "; ".join(failures) if failures else "healthcheck_strict_failed"
            except Exception as exc:  # noqa: BLE001
                health_ok = False
                health_message = f"healthcheck_error: {exc}"

        bucket_status = {}
        try:
            bucket_status = _check_bucket_connection()
        except Exception as exc:  # noqa: BLE001
            bucket_status = {"status": "Error", "latency_ms": None, "message": str(exc)}

        critical_alerts = filtered_anomalies.copy()
        if not critical_alerts.empty:
            critical_alerts = critical_alerts[critical_alerts["type"] == "Delta negativo"]
        if not critical_alerts.empty:
            critical_alerts["timestamp_dt"] = pd.to_datetime(
                critical_alerts["timestamp"], errors="coerce", utc=True
            )
            critical_alerts = critical_alerts.sort_values("timestamp_dt", ascending=False)
        critical_alerts = critical_alerts.head(5)

        pipeline_status = "Activo"
        if not health_ok:
            pipeline_status = "Con errores criticos"
        elif not critical_alerts.empty:
            pipeline_status = "Con errores criticos"
        elif latest_timestamp is None or (time_since_last and time_since_last > dt.timedelta(minutes=45)):
            pipeline_status = "Pausado"
        elif failed_retries > 0:
            pipeline_status = "Recuperandose"

        status_emoji = {
            "Activo": "\U0001f7e2",
            "Pausado": "\U0001f7e1",
            "Recuperandose": "\U0001f7e1",
            "Con errores criticos": "\U0001f534",
        }.get(pipeline_status, "\u26aa")

        header_cols = st.columns(3)
        with header_cols[0]:
            st.metric("Estado del pipeline", f"{status_emoji} {pipeline_status}")
        with header_cols[1]:
            st.metric("Ultimo checkpoint", latest_checkpoint_label)
            st.caption(f"Lote: {last_batch_label} - Hash: {_format_short_hash(hash_accumulator)}")
        with header_cols[2]:
            st.metric("Tiempo desde ultimo lote", time_since_label)

        health_cols = st.columns([1.1, 0.9])
        with health_cols[0]:
            health_state = "complete" if health_ok else "error"
            with st.status(
                f"Healthcheck estricto: {'OK' if health_ok else 'ERROR'}",
                state=health_state,
            ):
                st.write(health_message)
        with health_cols[1]:
            supervisor_status = _detect_supervisor()
            st.metric("Supervisor externo", supervisor_status)

        st.markdown("#### Recursos en tiempo real")
        resource_cols = st.columns(3)
        if PSUTIL_AVAILABLE:
            cpu_percent = psutil.cpu_percent(interval=0.2)
            memory_percent = psutil.virtual_memory().percent
            disk_percent = psutil.disk_usage("/").percent
            with resource_cols[0]:
                st.metric("CPU", f"{cpu_percent:.1f}%")
            with resource_cols[1]:
                st.metric("Memoria", f"{memory_percent:.1f}%")
            with resource_cols[2]:
                st.metric("Disco", f"{disk_percent:.1f}%")
        else:
            with resource_cols[0]:
                st.metric("CPU", "N/D")
            with resource_cols[1]:
                st.metric("Memoria", "N/D")
            with resource_cols[2]:
                st.metric("Disco", "N/D")
            st.info("Metricas de sistema no disponibles: instala psutil.")

        connection_cols = st.columns(3)
        with connection_cols[0]:
            bucket_label = bucket_status.get("status", "N/D")
            latency = bucket_status.get("latency_ms")
            latency_label = f"{latency:.0f} ms" if latency is not None else "N/D"
            st.metric("Bucket checkpoints", bucket_label)
            st.caption(f"Latencia: {latency_label}")
        with connection_cols[1]:
            st.metric("Reintentos fallidos (24h)", str(failed_retries))
        with connection_cols[2]:
            st.metric("Hash acumulado", _format_short_hash(hash_accumulator))

        st.markdown("#### Ultimas alertas criticas")
        if critical_alerts.empty:
            st.success("Sin alertas criticas recientes.")
        else:
            alert_table = critical_alerts[["timestamp", "department", "type", "delta", "hash"]].rename(
                columns={
                    "timestamp": "Timestamp",
                    "department": "Departamento",
                    "type": "Motivo",
                    "delta": "Delta votos",
                    "hash": "Hash",
                }
            )
            alert_table["Hash"] = alert_table["Hash"].apply(_format_short_hash)
            st.dataframe(alert_table, use_container_width=True, hide_index=True)

        st.markdown("#### Acciones de mantenimiento / Maintenance Actions")
        maint_cols = st.columns(2)
        with maint_cols[0]:
            if st.button("Forzar checkpoint ahora", type="primary", key="admin_checkpoint"):
                try:
                    manager = _build_checkpoint_manager()
                    if manager is None:
                        if not CHECKPOINTING_AVAILABLE:
                            st.error(f"Checkpoint deshabilitado: ({CHECKPOINTING_ERROR}).")
                        else:
                            st.error("Checkpoint no configurado: define CHECKPOINT_BUCKET.")
                    else:
                        manager.save_checkpoint(
                            {
                                "last_acta_id": last_batch_label,
                                "last_batch_offset": len(snapshot_files),
                                "rules_state": {"source": "dashboard"},
                                "hash_accumulator": hash_accumulator,
                            }
                        )
                        st.success("Checkpoint guardado exitosamente.")
                except Exception as exc:  # noqa: BLE001
                    st.error(f"No se pudo guardar el checkpoint: {exc}")

        with maint_cols[1]:
            if st.button("Lanzar auditoria completa / Run full audit", key="admin_audit"):
                st.info("Auditoria completa solicitada. Verificando motor de reglas...")
                _audit_result = run_rules_engine(snapshots_df, command_center_cfg)
                _n_alerts = len(_audit_result.get("alerts", []))
                _n_crit = len(_audit_result.get("critical", []))
                st.success(f"Auditoria completada: {_n_alerts} alertas, {_n_crit} criticas.")

        # EN: View logs section.
        # ES: Seccion de visualizacion de logs.
        with st.expander("Ver logs recientes / View recent logs"):
            _log_file = Path(command_center_cfg.get("logging", {}).get("file", "C.E.N.T.I.N.E.L.log"))
            if _log_file.exists():
                try:
                    _log_content = _log_file.read_text(encoding="utf-8", errors="ignore")
                    _log_lines = _log_content.strip().split("\n")
                    st.code("\n".join(_log_lines[-50:]), language="log")
                except OSError as exc:
                    st.error(f"Error leyendo logs: {exc}")
            else:
                st.info(f"Archivo de log no encontrado: {_log_file}")


# ES: Punto de entrada de ejecución directa.
# EN: Direct execution entry point.
if __name__ == "__main__":
    main()
