# Panel Chaos Module
# AUTO-DOC-INDEX
#
# ES: Índice rápido
#   1) Propósito del módulo
#   2) Componentes principales
#   3) Puntos de extensión
#
# EN: Quick index
#   1) Module purpose
#   2) Main components
#   3) Extension points
#
# Secciones / Sections:
#   - Configuración / Configuration
#   - Lógica principal / Core logic
#   - Integraciones / Integrations

"""Panel de Control de Caos para C.E.N.T.I.N.E.L.

Permite inyectar JSON personalizado y ejecutar escenarios de caos
sobre el pipeline simulado, monitoreando en vivo la respuesta del sistema.

Chaos Control Panel for C.E.N.T.I.N.E.L.

Allows injecting custom JSON and running chaos scenarios on the simulated
pipeline, with live monitoring of system response.
"""

from __future__ import annotations

import copy
import datetime as dt
import json
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import altair as alt
import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Path setup so we can import from project root and src/
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from chaos_test import (  # noqa: E402
    ChaosScenario,
    FakeBucket,
    FakePipelineRunner,
    PipelineState,
    SCENARIOS,
    SimulatedBucketError,
    SimulatedDiskFullError,
    SimulatedNetworkError,
)

try:
    from centinel.core.rules_engine import RulesEngine
except Exception:  # noqa: BLE001
    RulesEngine = None  # type: ignore[assignment,misc]

# ---------------------------------------------------------------------------
# Template JSON (based on mock_normal.json structure)
# ---------------------------------------------------------------------------
JSON_TEMPLATE = json.dumps(
    {
        "timestamp": "2026-01-07T08:30:00Z",
        "source": "MOCK-CNE",
        "actas_escrutadas": 1450,
        "actas_total": 1600,
        "total_votos": 1054320,
        "candidatos": {
            "Candidato A": 412300,
            "Candidato B": 356450,
            "Candidato C": 181220,
            "Candidato D": 104350,
        },
        "departamentos": [
            {
                "nombre": "Francisco Morazan",
                "actas_escrutadas": 210,
                "actas_total": 230,
                "total_votos": 162500,
                "candidatos": {
                    "Candidato A": 59200,
                    "Candidato B": 62000,
                    "Candidato C": 27500,
                    "Candidato D": 13800,
                },
            },
        ],
    },
    indent=2,
    ensure_ascii=False,
)

# ---------------------------------------------------------------------------
# Chaos scenarios metadata for the UI
# ---------------------------------------------------------------------------
SCENARIO_UI = [
    {"key": "kill", "label": "Kill -9", "icon": "💀", "desc": "Simula muerte subita del proceso"},
    {"key": "docker_kill", "label": "Docker Kill", "icon": "🐳", "desc": "Simula docker kill forzado"},
    {"key": "docker_stop", "label": "Docker Stop", "icon": "⏹", "desc": "Simula docker stop graceful"},
    {"key": "network_cut", "label": "Corte de Red", "icon": "🌐", "desc": "Simula perdida total de red"},
    {"key": "disk_fill", "label": "Disco Lleno", "icon": "💾", "desc": "Simula disco sin espacio"},
    {"key": "bucket_write", "label": "Fallo Bucket", "icon": "☁", "desc": "Simula fallo escritura en bucket"},
    {
        "key": "checkpoint_corruption",
        "label": "Corrupcion Checkpoint",
        "icon": "📄",
        "desc": "Corrompe el checkpoint de estado",
    },
]


def _now_str() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%H:%M:%S.%f")[:-3]


def _init_session_state() -> None:
    """Initialize all chaos panel session state keys."""
    if "chaos_runner" not in st.session_state:
        st.session_state.chaos_runner = None
    if "chaos_temp_dir" not in st.session_state:
        st.session_state.chaos_temp_dir = None
    if "chaos_event_log" not in st.session_state:
        st.session_state.chaos_event_log = []
    if "chaos_injected_snapshots" not in st.session_state:
        st.session_state.chaos_injected_snapshots = []
    if "chaos_rules_results" not in st.session_state:
        st.session_state.chaos_rules_results = []


def _get_or_create_runner(actas_before_failure: int) -> FakePipelineRunner:
    """Get existing runner or create a new one."""
    if st.session_state.chaos_runner is None:
        if st.session_state.chaos_temp_dir is None:
            st.session_state.chaos_temp_dir = tempfile.mkdtemp(prefix="centinel_chaos_")
        runner = FakePipelineRunner(temp_dir=Path(st.session_state.chaos_temp_dir))
        runner.start_test_pipeline()
        st.session_state.chaos_runner = runner
        _log_event("info", "Pipeline de prueba iniciado")

    runner = st.session_state.chaos_runner
    if runner.state.processed < actas_before_failure:
        try:
            runner.process_until(actas_before_failure)
            _log_event("info", f"Procesadas {runner.state.processed} actas (pre-fallo)")
        except (SimulatedNetworkError, SimulatedDiskFullError) as exc:
            _log_event("error", f"Fallo durante pre-procesamiento: {exc}")
    return runner


def _log_event(event_type: str, message: str) -> None:
    st.session_state.chaos_event_log.append({"time": _now_str(), "type": event_type, "message": message})


def _run_chaos_scenario(runner: FakePipelineRunner, scenario_key: str) -> None:
    """Execute a chaos scenario and record events (no pytest dependency)."""
    _log_event("warning", f"Ejecutando escenario: {scenario_key}")

    if scenario_key == "kill":
        runner.simulate_kill()
        _log_event("error", "Proceso terminado (kill -9)")

    elif scenario_key == "docker_kill":
        runner.simulate_docker_kill()
        _log_event("error", "Contenedor eliminado (docker kill)")

    elif scenario_key == "docker_stop":
        runner.simulate_docker_stop()
        _log_event("warning", "Contenedor detenido (docker stop) — checkpoint guardado")

    elif scenario_key == "network_cut":
        runner.simulate_network_cut()
        _log_event("error", "Red cortada — puertos 80/443 bloqueados")
        try:
            runner.process_until(runner.state.processed + 1)
        except SimulatedNetworkError:
            _log_event("error", "Procesamiento fallido: red no disponible")

    elif scenario_key == "disk_fill":
        runner.simulate_disk_fill()
        _log_event("error", "Disco lleno")
        try:
            runner.process_until(runner.state.processed + runner.checkpoint_interval)
        except SimulatedDiskFullError:
            _log_event("error", "Checkpoint fallido: disco sin espacio")

    elif scenario_key == "bucket_write":
        runner.simulate_bucket_write_failure()
        _log_event("warning", "Escritura a bucket deshabilitada")
        try:
            runner.process_until(runner.state.processed + runner.checkpoint_interval)
            _log_event("warning", "Procesamiento continua pero bucket no recibe datos")
        except SimulatedBucketError:
            _log_event("error", "Fallo critico de bucket")

    elif scenario_key == "checkpoint_corruption":
        runner.simulate_checkpoint_corruption()
        _log_event("error", "Checkpoint corrompido — datos de estado invalidados")


def _attempt_recovery(runner: FakePipelineRunner, timeout: int) -> None:
    """Attempt auto-recovery and log results."""
    _log_event("info", f"Intentando recuperacion (timeout={timeout}s)...")
    try:
        runner.restart_within(timeout_seconds=timeout)
        _log_event("recovery", f"Recuperacion exitosa — actas: {runner.state.processed}")
    except TimeoutError:
        _log_event("error", f"Timeout de recuperacion ({timeout}s)")
    except Exception as exc:  # noqa: BLE001
        _log_event("error", f"Error en recuperacion: {exc}")


def _validate_injected_json(raw: str) -> tuple[dict | None, str]:
    """Validate injected JSON and return (parsed, error_msg)."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return None, f"JSON invalido: {exc}"

    if not isinstance(data, dict):
        return None, "El JSON debe ser un objeto (dict)"

    missing = []
    if "candidatos" not in data:
        missing.append("candidatos")
    if "timestamp" not in data:
        missing.append("timestamp")
    if missing:
        return None, f"Campos requeridos faltantes: {', '.join(missing)}"

    return data, ""


def _run_rules_on_snapshot(
    snapshot: dict,
    previous: dict | None,
    config: dict,
) -> dict[str, Any]:
    """Run the RulesEngine on an injected snapshot."""
    if RulesEngine is None:
        return {"alerts": [], "critical": [], "error": "RulesEngine no disponible"}
    try:
        engine = RulesEngine(config=config)
        result = engine.run(snapshot, previous, snapshot_id=snapshot.get("timestamp"))
        return {"alerts": result.alerts, "critical": result.critical_alerts, "error": None}
    except Exception as exc:  # noqa: BLE001
        return {"alerts": [], "critical": [], "error": str(exc)}


# ---------------------------------------------------------------------------
# Main render function
# ---------------------------------------------------------------------------
def render_chaos_panel() -> None:
    """Render the full Chaos Control Panel."""
    _init_session_state()

    st.title("Panel de Control de Caos")
    st.caption("Inyecta datos y ejecuta escenarios de fallo para probar la resiliencia del sistema")

    # Load config for rules engine
    from streamlit_app import load_configs

    configs = load_configs()
    command_center_cfg = configs.get("command_center", {})

    control_col, monitor_col = st.columns([0.4, 0.6])

    # ==================================================================
    # LEFT COLUMN — Controls
    # ==================================================================
    with control_col:
        # --- Section A: JSON Injection ---
        st.markdown("### Inyeccion de JSON")
        json_input = st.text_area(
            "JSON personalizado",
            value=JSON_TEMPLATE,
            height=280,
            key="chaos_json_input",
        )

        inject_col1, inject_col2 = st.columns(2)
        with inject_col1:
            if st.button("Inyectar snapshot", type="primary", use_container_width=True):
                parsed, error = _validate_injected_json(json_input)
                if error:
                    st.error(error)
                else:
                    st.session_state.chaos_injected_snapshots.append(parsed)
                    _log_event("info", f"Snapshot inyectado: {parsed.get('timestamp', 'N/D')}")

                    # Run rules engine
                    previous = (
                        st.session_state.chaos_injected_snapshots[-2]
                        if len(st.session_state.chaos_injected_snapshots) > 1
                        else None
                    )
                    result = _run_rules_on_snapshot(parsed, previous, command_center_cfg)
                    st.session_state.chaos_rules_results.append(result)
                    n_alerts = len(result["alerts"])
                    n_critical = len(result["critical"])
                    _log_event(
                        "warning" if n_alerts > 0 else "info",
                        f"RulesEngine: {n_alerts} alertas, {n_critical} criticas",
                    )
                    st.rerun()

        with inject_col2:
            if st.button("Limpiar historial", use_container_width=True):
                st.session_state.chaos_injected_snapshots.clear()
                st.session_state.chaos_rules_results.clear()
                _log_event("info", "Historial de inyecciones limpiado")
                st.rerun()

        if st.session_state.chaos_injected_snapshots:
            with st.expander(f"Snapshots inyectados ({len(st.session_state.chaos_injected_snapshots)})"):
                for i, snap in enumerate(st.session_state.chaos_injected_snapshots):
                    st.caption(f"#{i + 1} — {snap.get('timestamp', 'N/D')}")

        st.markdown("---")

        # --- Section B: Chaos Scenarios ---
        st.markdown("### Escenarios de Caos")

        config_col1, config_col2 = st.columns(2)
        with config_col1:
            actas_before = st.slider(
                "Actas antes del fallo",
                min_value=0,
                max_value=200,
                value=50,
                step=5,
                key="chaos_actas_before",
            )
        with config_col2:
            recovery_timeout = st.number_input(
                "Timeout recuperacion (s)",
                min_value=1,
                max_value=600,
                value=120,
                key="chaos_timeout",
            )

        auto_recover = st.checkbox(
            "Auto-recuperar despues del fallo",
            value=True,
            key="chaos_auto_recover",
        )

        # Scenario buttons in a 2-column grid
        for i in range(0, len(SCENARIO_UI), 2):
            cols = st.columns(2)
            for j, col in enumerate(cols):
                idx = i + j
                if idx >= len(SCENARIO_UI):
                    break
                scenario = SCENARIO_UI[idx]
                with col:
                    if st.button(
                        f"{scenario['icon']} {scenario['label']}",
                        key=f"chaos_btn_{scenario['key']}",
                        use_container_width=True,
                        help=scenario["desc"],
                    ):
                        runner = _get_or_create_runner(actas_before)
                        _run_chaos_scenario(runner, scenario["key"])
                        if auto_recover:
                            _attempt_recovery(runner, recovery_timeout)
                        st.rerun()

        st.markdown("---")

        # --- Section C: Pipeline Controls ---
        pipeline_cols = st.columns(2)
        with pipeline_cols[0]:
            if st.button("Reiniciar Pipeline", use_container_width=True):
                st.session_state.chaos_runner = None
                st.session_state.chaos_temp_dir = None
                _log_event("info", "Pipeline reiniciado completamente")
                st.rerun()
        with pipeline_cols[1]:
            if st.button("Limpiar Log", use_container_width=True):
                st.session_state.chaos_event_log.clear()
                st.rerun()

    # ==================================================================
    # RIGHT COLUMN — Live Monitoring
    # ==================================================================
    with monitor_col:
        # --- Pipeline Metrics ---
        st.markdown("### Estado del Pipeline")
        runner = st.session_state.chaos_runner
        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric(
                "Actas procesadas",
                runner.state.processed if runner else 0,
            )
        with m2:
            st.metric(
                "Hashes acumulados",
                len(runner.state.hashes) if runner else 0,
            )
        with m3:
            st.metric(
                "Ultimo checkpoint",
                runner.state.last_checkpoint if runner else 0,
            )

        # --- Alert Log from runner ---
        if runner and runner.alert_log:
            st.markdown("### Alertas del Pipeline")
            alert_df = pd.DataFrame([{"Alerta": a, "Indice": i} for i, a in enumerate(runner.alert_log)])
            st.dataframe(alert_df, use_container_width=True, hide_index=True)

        # --- Rules Engine Results (from injected snapshots) ---
        if st.session_state.chaos_rules_results:
            st.markdown("### Resultados del Motor de Reglas")
            latest_result = st.session_state.chaos_rules_results[-1]

            if latest_result.get("error"):
                st.error(f"Error: {latest_result['error']}")
            else:
                r1, r2 = st.columns(2)
                with r1:
                    st.metric("Alertas totales", len(latest_result["alerts"]))
                with r2:
                    st.metric("Alertas criticas", len(latest_result["critical"]))

                if latest_result["alerts"]:
                    with st.expander(f"Detalle de alertas ({len(latest_result['alerts'])})"):
                        for alert in latest_result["alerts"]:
                            severity = alert.get("severity", "").upper()
                            msg = f"**{alert.get('type', 'N/D')}** — {alert.get('justification', alert.get('message', ''))}"
                            if severity in ("CRITICAL", "HIGH"):
                                st.error(msg)
                            elif severity == "WARNING":
                                st.warning(msg)
                            else:
                                st.info(msg)

        # --- Event Log ---
        st.markdown("### Log de Eventos")
        events = st.session_state.chaos_event_log
        if not events:
            st.info("Sin eventos registrados. Ejecuta un escenario o inyecta datos.")
        else:
            for event in reversed(events[-50:]):
                t = event["time"]
                msg = event["message"]
                etype = event["type"]
                if etype == "error":
                    st.error(f"`{t}` {msg}")
                elif etype == "recovery":
                    st.success(f"`{t}` {msg}")
                elif etype == "warning":
                    st.warning(f"`{t}` {msg}")
                else:
                    st.info(f"`{t}` {msg}")

        # --- Recovery Timeline Chart ---
        if len(events) > 1:
            st.markdown("### Timeline de Eventos")
            timeline_data = []
            for i, ev in enumerate(events):
                timeline_data.append(
                    {
                        "paso": i,
                        "tipo": ev["type"],
                        "mensaje": ev["message"][:60],
                    }
                )
            timeline_df = pd.DataFrame(timeline_data)

            color_map = {
                "error": "#EF4444",
                "recovery": "#22C55E",
                "warning": "#F59E0B",
                "info": "#3B82F6",
            }

            chart = (
                alt.Chart(timeline_df)
                .mark_circle(size=120)
                .encode(
                    x=alt.X("paso:Q", title="Evento #"),
                    y=alt.Y("tipo:N", title="Tipo"),
                    color=alt.Color(
                        "tipo:N",
                        scale=alt.Scale(
                            domain=list(color_map.keys()),
                            range=list(color_map.values()),
                        ),
                        legend=alt.Legend(title="Tipo"),
                    ),
                    tooltip=["paso", "tipo", "mensaje"],
                )
                .properties(height=200)
            )
            st.altair_chart(chart, use_container_width=True)
