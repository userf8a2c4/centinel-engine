# Panel Replay Module
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

"""Laboratorio UPNFM — Reproduccion de Datos para C.E.N.T.I.N.E.L.

Panel para reproducir datos historicos/mock, manipular tiempos de scraping
y variables de reglas en tiempo real, orientado a los matematicos de la UPNFM.

UPNFM Laboratory — Data Replay for C.E.N.T.I.N.E.L.

Panel for replaying historical/mock data, manipulating scraping timing and
rule variables in real-time, designed for UPNFM mathematicians.
"""

from __future__ import annotations

import copy
import datetime as dt
import json
import sys
import time
from pathlib import Path
from typing import Any

import altair as alt
import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

try:
    from centinel.core.rules_engine import RulesEngine
except Exception:  # noqa: BLE001
    RulesEngine = None  # type: ignore[assignment,misc]

# ---------------------------------------------------------------------------
# Data source definitions
# ---------------------------------------------------------------------------
DATA_SOURCES: dict[str, dict[str, Any]] = {
    "Mock Normal": {
        "path": REPO_ROOT / "data" / "mock" / "mock_normal.json",
        "multi": False,
    },
    "Mock Anomalia": {
        "path": REPO_ROOT / "data" / "mock" / "mock_anomaly.json",
        "multi": False,
    },
    "Mock Reversion": {
        "path": REPO_ROOT / "data" / "mock" / "mock_reversal.json",
        "multi": False,
    },
    "Snapshots 2025 (fixtures)": {
        "path": REPO_ROOT / "tests" / "fixtures" / "snapshots_2025",
        "multi": True,
        "pattern": "snapshot_*.json",
    },
    "Snapshots 2026 (reales)": {
        "path": REPO_ROOT / "data",
        "multi": True,
        "pattern": "snapshot_*.json",
    },
}

SPEED_MAP: dict[str, float] = {
    "0.25x": 4.0,
    "0.5x": 2.0,
    "1x": 1.0,
    "2x": 0.5,
    "4x": 0.25,
    "10x": 0.1,
    "Instantaneo": 0.0,
}

# Sensible ranges for rule parameters that are numeric
PARAM_RANGES: dict[str, dict[str, tuple[float, float, float]]] = {
    "granular_anomaly": {
        "negative_delta_threshold": (-10000, 10000, 1),
        "delta_pct_alert": (0.0, 50.0, 0.1),
        "delta_pct_time_window_minutes": (1, 360, 1),
        "zscore_threshold": (1.0, 10.0, 0.1),
        "zscore_min_abs_delta": (0, 100000, 10),
        "zscore_min_departments": (1, 18, 1),
        "benford_pvalue_threshold": (0.001, 0.5, 0.001),
        "benford_min_samples": (1, 1000, 1),
        "benford_min_vote": (0, 10000, 1),
        "turnout_min_pct": (0, 100, 1),
        "turnout_max_pct": (0, 200, 1),
        "reversal_min_lead_margin": (0, 100000, 50),
        "reversal_time_window_minutes": (1, 360, 1),
        "reversal_min_negative_delta": (0, 100000, 10),
        "sum_mismatch_threshold": (0, 10000, 1),
    },
    "trend_shift": {
        "threshold_percent": (0, 100, 1),
        "max_hours": (0.5, 48.0, 0.5),
    },
    "irreversibility": {
        "historical_participation_rate": (0.0, 1.0, 0.01),
    },
}


# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------
def _load_single_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _load_multi_snapshots(directory: Path, pattern: str) -> list[dict]:
    if not directory.exists():
        return []
    snapshots = []
    for p in sorted(directory.glob(pattern)):
        data = _load_single_json(p)
        if data:
            snapshots.append(data)
    return snapshots


def _generate_synthetic_steps(mock_data: dict, num_steps: int = 10) -> list[dict]:
    """Generate intermediate snapshots from a single mock for replay.

    Scales all vote counts linearly from fraction 1/num_steps to 1.0.
    """
    steps = []
    base_ts_str = mock_data.get("timestamp", "2026-01-07T08:00:00Z")
    try:
        base_ts = dt.datetime.fromisoformat(base_ts_str.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        base_ts = dt.datetime(2026, 1, 7, 8, 0, tzinfo=dt.timezone.utc)

    for i in range(num_steps):
        fraction = (i + 1) / num_steps
        step = copy.deepcopy(mock_data)

        step_ts = base_ts - dt.timedelta(minutes=5 * (num_steps - i))
        step["timestamp"] = step_ts.isoformat().replace("+00:00", "Z")

        # Scale national totals
        for key in ("total_votos", "actas_escrutadas", "votos_emitidos", "votos_validos"):
            if key in step and isinstance(step[key], (int, float)):
                step[key] = int(step[key] * fraction)

        # Scale candidates (dict format: {"Candidato A": 412300, ...})
        if isinstance(step.get("candidatos"), dict):
            for cand in step["candidatos"]:
                if isinstance(step["candidatos"][cand], (int, float)):
                    step["candidatos"][cand] = int(step["candidatos"][cand] * fraction)
        # Scale candidates (list format: [{"candidato": "...", "votos": 300}, ...])
        elif isinstance(step.get("candidatos"), list):
            for cand in step["candidatos"]:
                if isinstance(cand.get("votos"), (int, float)):
                    cand["votos"] = int(cand["votos"] * fraction)

        # Scale departments
        for dept in step.get("departamentos", []):
            for key in ("total_votos", "actas_escrutadas", "votos_emitidos"):
                if key in dept and isinstance(dept[key], (int, float)):
                    dept[key] = int(dept[key] * fraction)
            if isinstance(dept.get("candidatos"), dict):
                for cand in dept["candidatos"]:
                    if isinstance(dept["candidatos"][cand], (int, float)):
                        dept["candidatos"][cand] = int(dept["candidatos"][cand] * fraction)
            elif isinstance(dept.get("candidatos"), list):
                for cand in dept.get("candidatos", []):
                    if isinstance(cand.get("votos"), (int, float)):
                        cand["votos"] = int(cand["votos"] * fraction)

        steps.append(step)

    return steps


def _load_source_snapshots(source_name: str) -> list[dict]:
    """Load snapshots for the given data source."""
    cfg = DATA_SOURCES.get(source_name)
    if cfg is None:
        return []

    if cfg["multi"]:
        return _load_multi_snapshots(cfg["path"], cfg.get("pattern", "*.json"))
    else:
        data = _load_single_json(cfg["path"])
        if data is None:
            return []
        return _generate_synthetic_steps(data, num_steps=12)


def _extract_candidates(snapshot: dict) -> dict[str, int]:
    """Extract candidate -> votes from any snapshot format."""
    cands = snapshot.get("candidatos", {})
    if isinstance(cands, dict):
        return {k: v for k, v in cands.items() if isinstance(v, (int, float))}
    elif isinstance(cands, list):
        return {c.get("candidato", c.get("id", f"pos-{c.get('posicion', '?')}")): c.get("votos", 0) for c in cands}
    return {}


def _get_timestamp(snapshot: dict) -> str:
    return snapshot.get("timestamp") or snapshot.get("timestamp_utc") or "N/D"


# ---------------------------------------------------------------------------
# Replay engine
# ---------------------------------------------------------------------------
def _replay_step(rules_config: dict) -> None:
    """Advance the replay by one step and run the rules engine."""
    state = st.session_state.replay_state
    idx = state["current_index"]
    snapshots = state["snapshots"]

    if idx >= len(snapshots):
        return

    current = snapshots[idx]
    previous = snapshots[idx - 1] if idx > 0 else None

    # Run rules engine with user-modified config
    alerts: list[dict] = []
    critical: list[dict] = []
    error_msg = None

    if RulesEngine is not None:
        try:
            engine = RulesEngine(config={"rules": rules_config})
            result = engine.run(current, previous, snapshot_id=_get_timestamp(current))
            alerts = result.alerts
            critical = result.critical_alerts
        except Exception as exc:  # noqa: BLE001
            error_msg = str(exc)

    state["results_history"].append(
        {
            "step": idx,
            "timestamp": _get_timestamp(current),
            "alerts": alerts,
            "critical": critical,
            "total_alerts": len(alerts),
            "total_critical": len(critical),
            "error": error_msg,
        }
    )

    for alert in alerts:
        enriched = copy.copy(alert)
        enriched["replay_step"] = idx
        enriched["replay_timestamp"] = _get_timestamp(current)
        state["alerts_timeline"].append(enriched)

    state["current_index"] = idx + 1


def _run_comparison(
    snapshot: dict,
    previous: dict | None,
    original_config: dict,
    modified_config: dict,
) -> tuple[int, int]:
    """Run rules engine with both configs and return (original_count, modified_count)."""
    if RulesEngine is None:
        return 0, 0

    try:
        orig_engine = RulesEngine(config={"rules": original_config})
        orig_result = orig_engine.run(snapshot, previous)
        orig_count = len(orig_result.alerts)
    except Exception:  # noqa: BLE001
        orig_count = 0

    try:
        mod_engine = RulesEngine(config={"rules": modified_config})
        mod_result = mod_engine.run(snapshot, previous)
        mod_count = len(mod_result.alerts)
    except Exception:  # noqa: BLE001
        mod_count = 0

    return orig_count, mod_count


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
def _init_replay_state() -> None:
    if "replay_state" not in st.session_state:
        st.session_state.replay_state = {
            "snapshots": [],
            "current_index": 0,
            "is_playing": False,
            "results_history": [],
            "alerts_timeline": [],
            "source_name": None,
        }
    if "replay_rules_config" not in st.session_state:
        st.session_state.replay_rules_config = None
    if "replay_original_rules" not in st.session_state:
        st.session_state.replay_original_rules = None


def _reset_replay() -> None:
    st.session_state.replay_state = {
        "snapshots": st.session_state.replay_state.get("snapshots", []),
        "current_index": 0,
        "is_playing": False,
        "results_history": [],
        "alerts_timeline": [],
        "source_name": st.session_state.replay_state.get("source_name"),
    }


# ---------------------------------------------------------------------------
# Sidebar: rule parameter editors
# ---------------------------------------------------------------------------
def _render_rule_editors(rules_cfg: dict) -> None:
    """Render sidebar expanders for each rule's parameters."""
    st.sidebar.markdown("### Variables de Reglas")
    st.sidebar.caption("Modifica umbrales y ve como cambia la deteccion")

    for rule_key, rule_settings in sorted(rules_cfg.items()):
        if rule_key == "global_enabled":
            continue
        if not isinstance(rule_settings, dict):
            continue

        # Count configurable params (beyond 'enabled')
        param_keys = [k for k in rule_settings if k not in ("enabled", "sqlite_path")]
        label = rule_key.replace("_", " ").title()
        badge = f" ({len(param_keys)} params)" if param_keys else ""

        with st.sidebar.expander(f"{label}{badge}"):
            rules_cfg[rule_key]["enabled"] = st.toggle(
                "Habilitada",
                value=rule_settings.get("enabled", True),
                key=f"replay_rule_enabled_{rule_key}",
            )

            known_ranges = PARAM_RANGES.get(rule_key, {})

            for param_key in param_keys:
                param_value = rule_settings[param_key]
                nice_label = param_key.replace("_", " ").title()

                if isinstance(param_value, float):
                    ranges = known_ranges.get(param_key)
                    if ranges:
                        mn, mx, stp = ranges
                        rules_cfg[rule_key][param_key] = st.number_input(
                            nice_label,
                            min_value=float(mn),
                            max_value=float(mx),
                            value=float(param_value),
                            step=float(stp),
                            key=f"replay_{rule_key}_{param_key}",
                        )
                    else:
                        rules_cfg[rule_key][param_key] = st.number_input(
                            nice_label,
                            value=float(param_value),
                            step=0.01,
                            key=f"replay_{rule_key}_{param_key}",
                        )

                elif isinstance(param_value, int):
                    ranges = known_ranges.get(param_key)
                    if ranges:
                        mn, mx, stp = ranges
                        rules_cfg[rule_key][param_key] = st.number_input(
                            nice_label,
                            min_value=int(mn),
                            max_value=int(mx),
                            value=int(param_value),
                            step=int(stp),
                            key=f"replay_{rule_key}_{param_key}",
                        )
                    else:
                        rules_cfg[rule_key][param_key] = st.number_input(
                            nice_label,
                            value=int(param_value),
                            step=1,
                            key=f"replay_{rule_key}_{param_key}",
                        )

                elif isinstance(param_value, str) and param_key != "sqlite_path":
                    rules_cfg[rule_key][param_key] = st.text_input(
                        nice_label,
                        value=param_value,
                        key=f"replay_{rule_key}_{param_key}",
                    )

    if st.sidebar.button("Restaurar valores por defecto", use_container_width=True):
        if st.session_state.replay_original_rules is not None:
            st.session_state.replay_rules_config = copy.deepcopy(st.session_state.replay_original_rules)
            st.rerun()


# ---------------------------------------------------------------------------
# Main render function
# ---------------------------------------------------------------------------
def render_replay_panel() -> None:
    """Render the full Data Replay / UPNFM Laboratory panel."""
    _init_replay_state()

    st.title("Laboratorio UPNFM — Reproduccion de Datos")
    st.caption(
        "Reproduce datos historicos/mock, manipula variables de reglas en tiempo real "
        "y observa como cambian las detecciones de anomalias"
    )

    # Load config
    from streamlit_app import load_configs

    configs = load_configs()
    command_center_cfg = configs.get("command_center", {})

    # Initialize rules config from command_center if not yet done
    if st.session_state.replay_rules_config is None:
        st.session_state.replay_rules_config = copy.deepcopy(command_center_cfg.get("rules", {}))
    if st.session_state.replay_original_rules is None:
        st.session_state.replay_original_rules = copy.deepcopy(command_center_cfg.get("rules", {}))

    rules_cfg = st.session_state.replay_rules_config

    # ==================================================================
    # SIDEBAR Controls
    # ==================================================================
    st.sidebar.markdown("---")
    st.sidebar.markdown("## Controles de Replay")

    # --- Data source ---
    source_name = st.sidebar.radio(
        "Fuente de datos",
        list(DATA_SOURCES.keys()),
        index=0,
        key="replay_source",
    )

    # Load snapshots if source changed
    replay_state = st.session_state.replay_state
    if replay_state["source_name"] != source_name:
        snapshots = _load_source_snapshots(source_name)
        st.session_state.replay_state = {
            "snapshots": snapshots,
            "current_index": 0,
            "is_playing": False,
            "results_history": [],
            "alerts_timeline": [],
            "source_name": source_name,
        }
        replay_state = st.session_state.replay_state

    snapshots = replay_state["snapshots"]
    max_idx = max(len(snapshots) - 1, 0)
    current_idx = min(replay_state["current_index"], max_idx)

    if not snapshots:
        st.warning(f"No se encontraron snapshots para '{source_name}'")
        return

    st.sidebar.info(f"{len(snapshots)} snapshots cargados")

    # --- Timing ---
    st.sidebar.markdown("### Control de Tiempo")
    replay_speed = st.sidebar.select_slider(
        "Velocidad de replay",
        options=list(SPEED_MAP.keys()),
        value="1x",
        key="replay_speed",
    )

    btn_cols = st.sidebar.columns(3)
    with btn_cols[0]:
        play_clicked = st.button(
            "▶ Play" if not replay_state["is_playing"] else "⏸ Pausa",
            use_container_width=True,
            key="replay_play_btn",
        )
    with btn_cols[1]:
        prev_clicked = st.button("⏮ Prev", use_container_width=True, key="replay_prev_btn")
    with btn_cols[2]:
        next_clicked = st.button("Next ⏭", use_container_width=True, key="replay_next_btn")

    if st.sidebar.button("🔄 Reiniciar", use_container_width=True, key="replay_reset_btn"):
        _reset_replay()
        st.rerun()

    # Handle button actions
    if play_clicked:
        replay_state["is_playing"] = not replay_state["is_playing"]
        st.rerun()

    if prev_clicked and current_idx > 0:
        replay_state["current_index"] = current_idx - 1
        # Remove last result if going back
        if replay_state["results_history"]:
            replay_state["results_history"].pop()
        st.rerun()

    if next_clicked and current_idx < max_idx:
        _replay_step(rules_cfg)
        st.rerun()

    # Timeline position slider
    position = st.sidebar.slider(
        "Posicion en timeline",
        min_value=0,
        max_value=max_idx,
        value=min(current_idx, max_idx),
        key="replay_position_slider",
    )
    if position != current_idx and not replay_state["is_playing"]:
        # Jump to position — re-run all steps up to that point
        replay_state["current_index"] = 0
        replay_state["results_history"].clear()
        replay_state["alerts_timeline"].clear()
        for _ in range(position):
            _replay_step(rules_cfg)
        st.rerun()

    # --- Rule parameter editors ---
    _render_rule_editors(rules_cfg)

    # ==================================================================
    # MAIN AREA
    # ==================================================================
    viz_col, alerts_col = st.columns([0.6, 0.4])

    current_snap = snapshots[min(current_idx, max_idx)]
    previous_snap = snapshots[current_idx - 1] if current_idx > 0 else None

    with viz_col:
        # --- Progress ---
        progress_pct = current_idx / max(max_idx, 1)
        st.progress(progress_pct, text=f"Paso {current_idx}/{max_idx}")

        # --- Vote accumulation chart ---
        if replay_state["results_history"]:
            st.markdown("### Alertas a lo largo del replay")
            history_df = pd.DataFrame(
                [
                    {
                        "Paso": r["step"],
                        "Timestamp": r["timestamp"],
                        "Alertas": r["total_alerts"],
                        "Criticas": r["total_critical"],
                    }
                    for r in replay_state["results_history"]
                ]
            )

            alert_chart = (
                alt.Chart(history_df)
                .mark_bar()
                .encode(
                    x=alt.X("Paso:Q", title="Paso de replay"),
                    y=alt.Y("Alertas:Q", title="Alertas detectadas"),
                    color=alt.condition(
                        alt.datum.Criticas > 0,
                        alt.value("#EF4444"),
                        alt.value("#3B82F6"),
                    ),
                    tooltip=["Paso", "Timestamp", "Alertas", "Criticas"],
                )
                .properties(height=250)
            )
            st.altair_chart(alert_chart, use_container_width=True)

        # --- Candidate vote distribution ---
        st.markdown("### Distribucion de votos — Snapshot actual")
        candidates = _extract_candidates(current_snap)
        if candidates:
            cand_df = pd.DataFrame([{"Candidato": k, "Votos": v} for k, v in candidates.items()]).sort_values(
                "Votos", ascending=False
            )

            bar_chart = (
                alt.Chart(cand_df)
                .mark_bar()
                .encode(
                    x=alt.X("Votos:Q"),
                    y=alt.Y("Candidato:N", sort="-x"),
                    color=alt.Color("Candidato:N", legend=None),
                    tooltip=["Candidato", "Votos"],
                )
                .properties(height=max(len(candidates) * 40, 120))
            )
            st.altair_chart(bar_chart, use_container_width=True)
        else:
            st.info("Sin datos de candidatos en este snapshot")

        # --- Vote evolution chart (candidates over time) ---
        if len(replay_state["results_history"]) > 1:
            st.markdown("### Evolucion de votos por candidato")
            evolution_rows = []
            for step_idx in range(min(current_idx, len(snapshots))):
                snap = snapshots[step_idx]
                cands = _extract_candidates(snap)
                for cand_name, votes in cands.items():
                    evolution_rows.append({"Paso": step_idx, "Candidato": cand_name, "Votos": votes})

            if evolution_rows:
                evo_df = pd.DataFrame(evolution_rows)
                evo_chart = (
                    alt.Chart(evo_df)
                    .mark_line(point=True)
                    .encode(
                        x=alt.X("Paso:Q", title="Paso de replay"),
                        y=alt.Y("Votos:Q"),
                        color=alt.Color("Candidato:N"),
                        tooltip=["Paso", "Candidato", "Votos"],
                    )
                    .properties(height=300)
                )
                st.altair_chart(evo_chart, use_container_width=True)

        # --- Raw snapshot ---
        with st.expander("JSON del snapshot actual"):
            st.json(current_snap)

    with alerts_col:
        # --- Current step alerts ---
        st.markdown("### Alertas — Paso actual")

        current_step_results = [r for r in replay_state["results_history"] if r["step"] == current_idx - 1]

        if current_step_results:
            step_result = current_step_results[0]
            if step_result.get("error"):
                st.error(f"Error en reglas: {step_result['error']}")

            m1, m2 = st.columns(2)
            with m1:
                st.metric("Alertas", step_result["total_alerts"])
            with m2:
                st.metric("Criticas", step_result["total_critical"])

            for alert in step_result["alerts"]:
                severity = str(alert.get("severity", "")).upper()
                msg = f"**{alert.get('type', 'N/D')}** — {alert.get('justification', alert.get('message', ''))}"
                rule_name = alert.get("rule", "")
                if rule_name:
                    msg += f" `[{rule_name}]`"

                if severity in ("CRITICAL", "HIGH"):
                    st.error(msg)
                elif severity == "WARNING":
                    st.warning(msg)
                else:
                    st.info(msg)
        else:
            if current_idx == 0:
                st.info("Presiona Play o Next para iniciar el replay")
            else:
                st.info("Sin resultados para este paso")

        # --- Threshold impact comparison ---
        st.markdown("### Impacto de umbrales")
        st.caption("Compara alertas con config original vs. modificada")

        orig_count, mod_count = _run_comparison(
            current_snap,
            previous_snap,
            st.session_state.replay_original_rules,
            rules_cfg,
        )
        c1, c2 = st.columns(2)
        with c1:
            st.metric("Config original", orig_count)
        with c2:
            delta = mod_count - orig_count
            st.metric("Config modificada", mod_count, delta=delta if delta != 0 else None)

        # --- Cumulative alerts table ---
        st.markdown("### Historial de alertas acumuladas")
        timeline = replay_state["alerts_timeline"]
        if timeline:
            # Cap display at 200 most recent
            display_alerts = timeline[-200:]
            alerts_df = pd.DataFrame(
                [
                    {
                        "Paso": a.get("replay_step", ""),
                        "Tipo": a.get("type", ""),
                        "Severidad": a.get("severity", ""),
                        "Regla": a.get("rule", ""),
                        "Departamento": a.get("department", a.get("departamento", "")),
                    }
                    for a in display_alerts
                ]
            )
            st.dataframe(alerts_df, use_container_width=True, hide_index=True)
        else:
            st.info("Sin alertas acumuladas aun")

    # ==================================================================
    # Auto-play loop
    # ==================================================================
    if replay_state["is_playing"] and current_idx < len(snapshots):
        delay = SPEED_MAP.get(replay_speed, 1.0)
        if delay > 0:
            time.sleep(delay)
        _replay_step(rules_cfg)
        if replay_state["current_index"] >= len(snapshots):
            replay_state["is_playing"] = False
            st.success("Replay completado")
        st.rerun()
