"""Streamlit dashboard para monitoreo de snapshots electorales."""

import json
import logging
import os
import subprocess
import sys
from datetime import datetime
from hashlib import sha256
from pathlib import Path

import pandas as pd
import streamlit as st

from sentinel.utils.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

DATA_DIR = Path("data")
HASH_DIR = Path("hashes")
ALERTS_LOG = Path("alerts.log")
ALERTS_JSON = DATA_DIR / "alerts.json"
REPORTS_DIR = Path("reports")
DEFAULT_PDF_REPORT = REPORTS_DIR / "latest_report.pdf"
READ_ERROR_PREFIX = "No se pudo leer"
NO_DATA_MESSAGE = (
    "No hay datos disponibles aún. Ejecuta primero: python -m scripts.download_and_hash"
)


def parse_timestamp_from_name(filename: str) -> datetime | None:
    """Extrae timestamp del nombre del archivo si es posible.

    Espera nombres de archivo tipo: snapshot_2026-01-07_14-30-00.json.
    """
    stem = Path(filename).stem
    parts = stem.split("_")
    if len(parts) < 3:
        return None
    date_part = parts[-2]
    time_part = parts[-1]
    for fmt in ("%Y-%m-%d_%H-%M-%S", "%Y-%m-%d_%H-%M"):
        try:
            return datetime.strptime(f"{date_part}_{time_part}", fmt)
        except ValueError:
            continue
    return None


def format_read_error(label: str, path: Path, detail: str) -> str:
    """Genera mensajes consistentes para errores de lectura."""
    return f"{READ_ERROR_PREFIX} {label} en {path}: {detail}"


def handle_read_exception(
    label: str,
    path: Path,
    exc: Exception,
    errors: list[str] | None = None,
) -> str:
    """Registra y muestra errores de lectura con severidad adecuada."""
    message = format_read_error(label, path, str(exc))
    if isinstance(exc, FileNotFoundError):
        st.warning(message)
        logger.warning(message)
    else:
        st.error(message)
        logger.error(message)
    if errors is not None:
        errors.append(message)
    return message


def safe_read_json(
    path: Path,
    label: str = "JSON",
    errors: list[str] | None = None,
) -> tuple[dict, str | None]:
    """Carga JSON con manejo de errores y mensaje uniforme."""
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle), None
    except FileNotFoundError as exc:
        return {}, handle_read_exception(label, path, exc, errors)
    except (OSError, json.JSONDecodeError) as exc:
        return {}, handle_read_exception(label, path, exc, errors)


def read_hash_file(snapshot_path: Path, errors: list[str] | None = None) -> tuple[str, str | None]:
    """Lee el hash SHA256 desde el archivo .sha256 si existe."""
    hash_path = HASH_DIR / f"{snapshot_path.name}.sha256"
    try:
        if hash_path.exists():
            return hash_path.read_text(encoding="utf-8").strip(), None
        if snapshot_path.exists():
            return sha256(snapshot_path.read_bytes()).hexdigest(), None
        raise FileNotFoundError("archivo no encontrado")
    except (OSError, FileNotFoundError) as exc:
        return "", handle_read_exception("snapshot/hash", hash_path, exc, errors)


def load_snapshots_list() -> list[Path]:
    """Lista snapshots disponibles ordenados por fecha descendente."""
    # Ordena por fecha de modificación para priorizar el snapshot más reciente.
    if not DATA_DIR.exists():
        return []
    try:
        snapshots = sorted(DATA_DIR.glob("*.json"), key=os.path.getmtime, reverse=True)
    except OSError as exc:
        handle_read_exception("listado de snapshots", DATA_DIR, exc)
        return []
    return [snap for snap in snapshots if snap.is_file()]


def extract_timestamp(snapshot_path: Path, payload: dict) -> datetime | None:
    """Obtiene timestamp del JSON o del nombre."""
    raw = payload.get("timestamp")
    if isinstance(raw, str):
        try:
            return datetime.fromisoformat(raw)
        except ValueError:
            pass
    elif isinstance(raw, datetime):
        return raw
    return parse_timestamp_from_name(snapshot_path.name)


def normalize_votos(payload: dict) -> dict:
    """Normaliza el diccionario de votos."""
    votos = payload.get("votos") or {}
    if isinstance(votos, dict):
        return {str(k): float(v) for k, v in votos.items() if isinstance(v, (int, float))}
    return {}


def load_snapshot_data(snapshot_path: Path, errors: list[str]) -> dict:
    """Carga y normaliza datos de un snapshot.

    Los mensajes de error se agregan a la lista compartida para mostrar en UI.
    """
    payload, error = safe_read_json(snapshot_path, label="snapshot", errors=errors)
    timestamp = extract_timestamp(snapshot_path, payload)
    porcentaje = payload.get("porcentaje_escrutado")
    porcentaje_val = float(porcentaje) if isinstance(porcentaje, (int, float)) else None
    votos = normalize_votos(payload)
    total_votos = payload.get("total_votos")
    if total_votos is None and votos:
        total_votos = sum(votos.values())
    return {
        "path": snapshot_path,
        "payload": payload,
        "timestamp": timestamp,
        "porcentaje_escrutado": porcentaje_val,
        "votos": votos,
        "total_votos": total_votos,
        "departamento": payload.get("departamento"),
    }


def compute_diffs(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega columna de cambio porcentual vs snapshot anterior."""
    df = df.copy()
    if "Porcentaje escrutado" not in df.columns:
        df["Cambio %"] = None
        return df
    df["Cambio %"] = df["Porcentaje escrutado"].diff(-1)
    return df


def display_header() -> None:
    """Renderiza el encabezado principal del dashboard."""
    st.markdown(
        "<h1 style='text-align:center;'>"
        "HND-SENTINEL-2029 – Auditoría Ciudadana Independiente del CNE Honduras – "
        "Solo hechos y números"
        "</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align:center;'>"
        "Panel operativo en tiempo real para auditoría de snapshots electorales"
        "</p>",
        unsafe_allow_html=True,
    )


def display_footer() -> None:
    """Renderiza el pie institucional del dashboard."""
    st.markdown("---")
    st.markdown(
        "Proyecto open-source MIT – Solo datos públicos del CNE – "
        "Preparado para Elecciones 2029 – No alineado políticamente."
    )
    st.markdown("Versión: v0.1-dev (enero 2026)")


def get_alerts(errors: list[str]) -> list[dict]:
    """Carga alertas desde archivo JSON o log, registrando fallos."""
    if ALERTS_JSON.exists():
        data, _ = safe_read_json(ALERTS_JSON, label="alertas", errors=errors)
        if isinstance(data, list):
            return data
    if ALERTS_LOG.exists():
        try:
            lines = ALERTS_LOG.read_text(encoding="utf-8").splitlines()
            return [{"timestamp": "", "descripcion": line} for line in lines if line.strip()]
        except OSError as exc:
            handle_read_exception("alertas/log", ALERTS_LOG, exc, errors)
            return []
    return []


def alerts_to_dataframe(alerts: list[dict]) -> pd.DataFrame:
    """Convierte alertas a DataFrame para exportación."""
    rows = []
    for alert in alerts:
        rows.append(
            {
                "Timestamp": alert.get("timestamp", ""),
                "Descripción": alert.get("descripcion", alert.get("description", "")),
            }
        )
    return pd.DataFrame(rows)


def summarize_alerts(alerts: list[dict]) -> str:
    """Resume alertas en un texto compacto para exportaciones."""
    descriptions = []
    for alert in alerts:
        description = alert.get("descripcion") or alert.get("description") or ""
        timestamp = alert.get("timestamp") or ""
        if description and timestamp:
            descriptions.append(f"{timestamp} - {description}")
        elif description:
            descriptions.append(description)
        elif timestamp:
            descriptions.append(timestamp)
    return "; ".join(descriptions)


def build_snapshot_export(df: pd.DataFrame, alerts: list[dict]) -> pd.DataFrame:
    """Construye el CSV de snapshots con columnas útiles."""
    export_columns = ["timestamp", "hash", "delta", "porcentaje", "alertas"]
    alerts_summary = summarize_alerts(alerts)
    if df.empty:
        if alerts_summary:
            return pd.DataFrame(
                [
                    {
                        "timestamp": "",
                        "hash": "",
                        "delta": None,
                        "porcentaje": None,
                        "alertas": alerts_summary,
                    }
                ],
                columns=export_columns,
            )
        return pd.DataFrame(columns=export_columns)
    export_df = compute_diffs(df.copy())
    export_df = export_df.rename(
        columns={
            "Fecha/Hora": "timestamp",
            "Hash": "hash",
            "Cambio %": "delta",
            "Porcentaje escrutado": "porcentaje",
        }
    )
    for column in ("timestamp", "hash", "delta", "porcentaje"):
        if column not in export_df.columns:
            export_df[column] = None
    export_df["alertas"] = alerts_summary
    return export_df[export_columns]


def display_alerts(errors: list[str], alerts: list[dict] | None = None) -> None:
    """Renderiza alertas o un placeholder."""
    st.subheader("Alertas y anomalías")
    alerts = alerts if alerts is not None else get_alerts(errors)
    if not alerts:
        st.info("No hay alertas recientes.")
        return
    st.dataframe(alerts_to_dataframe(alerts), use_container_width=True)


def display_exports(df: pd.DataFrame, alerts: list[dict]) -> None:
    """Sección de exportación rápida para compartir reportes."""
    st.subheader("Exportar reportes")
    if df.empty and not alerts:
        st.info(NO_DATA_MESSAGE)
        return
    if not df.empty:
        export_df = df.copy()
        export_df = compute_diffs(export_df)
        export_df = export_df[
            [
                "Fecha/Hora",
                "Hash",
                "Cambio %",
                "Porcentaje escrutado",
                "Departamento",
                "Total votos",
            ]
        ].copy()
        st.download_button(
            "Descargar snapshots (CSV)",
            export_df.to_csv(index=False).encode("utf-8"),
            file_name="snapshots.csv",
            mime="text/csv",
        )
    if alerts:
        alerts_df = alerts_to_dataframe(alerts)
        st.download_button(
            "Descargar alertas (CSV)",
            alerts_df.to_csv(index=False).encode("utf-8"),
            file_name="alertas.csv",
            mime="text/csv",
        )


def build_dataframe(snapshot_data: list[dict], errors: list[str]) -> pd.DataFrame:
    """Construye DataFrame para tabla y gráficos."""
    rows = []
    for item in snapshot_data:
        timestamp = item["timestamp"]
        hash_value = ""
        hash_error = None
        if item.get("path"):
            hash_value, hash_error = read_hash_file(item["path"], errors=errors)
        rows.append(
            {
                "Fecha/Hora": timestamp.isoformat(sep=" ") if timestamp else "",
                "Nombre archivo": item["path"].name,
                "Hash": hash_value,
                "Porcentaje escrutado": item["porcentaje_escrutado"],
                "Total votos": item["total_votos"],
                "Departamento": item.get("departamento") or "",
                "Votos": item["votos"],
            }
        )
    return pd.DataFrame(rows)


def display_estado_actual(latest: dict, errors: list[str]) -> None:
    """Renderiza la sección con detalle del último snapshot."""
    with st.expander("Estado actual", expanded=True):
        timestamp = latest.get("timestamp")
        st.write(
            f"**Último snapshot:** {timestamp.isoformat(sep=' ') if timestamp else 'Sin fecha'}"
        )
        snapshot_path = latest.get("path")
        hash_value = ""
        if snapshot_path:
            hash_value, _ = read_hash_file(snapshot_path, errors=errors)
        st.write(f"**Hash SHA-256:** {hash_value or 'No disponible'}")
        st.write(
            f"**Porcentaje escrutado:** "
            f"{latest.get('porcentaje_escrutado') if latest.get('porcentaje_escrutado') is not None else 'N/A'}"
        )
        total_votos = latest.get("total_votos")
        st.write(f"**Total votos acumulados:** {total_votos if total_votos is not None else 'N/A'}")
        st.write(
            f"**Última actualización:** {timestamp.isoformat(sep=' ') if timestamp else 'N/A'}"
        )


def display_table(df: pd.DataFrame) -> None:
    """Renderiza la tabla con los últimos snapshots."""
    st.subheader("Últimos snapshots")
    if df.empty:
        st.info(NO_DATA_MESSAGE)
        return
    # Presentación compacta del hash para facilitar la lectura.
    table_df = df[["Fecha/Hora", "Nombre archivo", "Hash", "Porcentaje escrutado"]].copy()
    table_df = compute_diffs(table_df)
    table_df["Hash"] = table_df["Hash"].apply(
        lambda value: f"{value[:12]}..." if isinstance(value, str) and value else ""
    )
    st.dataframe(table_df.head(10), use_container_width=True)
    export_df = df.copy()
    if "Votos" in export_df.columns:
        export_df["Votos"] = export_df["Votos"].apply(
            lambda value: json.dumps(value, ensure_ascii=False) if isinstance(value, dict) else ""
        )
    csv_data = export_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Descargar snapshots (CSV)",
        data=csv_data,
        file_name="snapshots.csv",
        mime="text/csv",
    )


def display_chart(df: pd.DataFrame) -> None:
    """Renderiza el gráfico temporal del porcentaje escrutado."""
    st.subheader("Evolución del escrutinio")
    if df.empty:
        st.info(NO_DATA_MESSAGE)
        return
    chart_df = df.copy()
    chart_df = chart_df.sort_values("Fecha/Hora")
    chart_df["timestamp"] = pd.to_datetime(chart_df["Fecha/Hora"], errors="coerce")
    chart_df = chart_df.dropna(subset=["timestamp"])
    if chart_df.empty or "Porcentaje escrutado" not in chart_df.columns:
        st.info(NO_DATA_MESSAGE)
        return
    chart_data = chart_df.set_index("timestamp")[["Porcentaje escrutado"]]
    st.line_chart(chart_data)


def render_sidebar() -> dict:
    """Renderiza la barra lateral para filtros y acciones."""
    st.sidebar.header("Filtros y acciones")
    if DEFAULT_PDF_REPORT.exists() and not DEFAULT_PDF_REPORT.is_file():
        error = format_read_error("reporte PDF", DEFAULT_PDF_REPORT, "no es un archivo")
        errors.append(error)
        st.sidebar.warning(error)
    elif DEFAULT_PDF_REPORT.exists():
        try:
            report_bytes = DEFAULT_PDF_REPORT.read_bytes()
            st.sidebar.download_button(
                label="Descargar reporte PDF",
                data=report_bytes,
                file_name=DEFAULT_PDF_REPORT.name,
                mime="application/pdf",
            )
        except FileNotFoundError as exc:
            st.sidebar.warning("No se pudo cargar el PDF de reporte.")
            logger.warning("No se pudo cargar el PDF de reporte: %s", exc)
        except OSError as exc:
            st.sidebar.error("No se pudo cargar el PDF de reporte.")
            logger.error("No se pudo cargar el PDF de reporte: %s", exc)
    else:
        st.sidebar.caption("Genera un reporte PDF para habilitar la descarga.")
    if st.sidebar.button("Actualizar datos ahora"):
        with st.spinner("Ejecutando descarga de snapshots..."):
            result = subprocess.run(
                [sys.executable, "-m", "scripts.download_and_hash"],
                capture_output=True,
                text=True,
                check=False,
            )
        if result.returncode == 0:
            st.sidebar.success("Descarga completada.")
        else:
            st.sidebar.error("Falló la descarga. Revisa logs.")
            if result.stderr:
                st.sidebar.caption(result.stderr.strip())
        st.rerun()
    debug = st.sidebar.checkbox("Modo debug: mostrar JSON crudo del último snapshot")
    st.sidebar.markdown("[Ver repo en GitHub](https://github.com/userf8a2c4/sentinel)")
    return {"debug": debug}


def display_read_errors(errors: list[str]) -> None:
    """Renderiza errores de lectura de forma consistente."""
    if not errors:
        return
    unique_errors = sorted(set(errors))
    st.warning("Se detectaron problemas al leer archivos:")
    for error in unique_errors:
        st.write(f"- {error}")


def apply_departamento_filter(
    df: pd.DataFrame, snapshot_data: list[dict], latest: dict
) -> tuple[pd.DataFrame, list[dict], dict]:
    """Aplica filtro por departamento si la columna está disponible."""
    if "Departamento" not in df.columns or df.empty:
        return df, snapshot_data, latest
    departamentos = ["Todos"] + sorted(
        df["Departamento"].dropna().unique().tolist()
    )
    selected = st.selectbox("Filtrar por departamento", departamentos)
    if selected == "Todos":
        return df, snapshot_data, latest
    filtered_df = df[df["Departamento"] == selected]
    filtered_snapshot_data = [
        item for item in snapshot_data if item.get("departamento") == selected
    ]
    filtered_latest = filtered_snapshot_data[0] if filtered_snapshot_data else {}
    if filtered_df.empty:
        st.warning(NO_DATA_MESSAGE)
        logger.warning("No data found for departamento: %s", selected)
    return filtered_df, filtered_snapshot_data, filtered_latest


def display_estado_general(df: pd.DataFrame, alerts: list[dict]) -> None:
    """Renderiza un resumen general con métricas clave."""
    st.subheader("Estado general")
    total_snapshots = len(df)
    last_snapshot = df["Fecha/Hora"].iloc[0] if not df.empty else "N/A"
    total_alertas = len(alerts)
    porcentaje = df["Porcentaje escrutado"].iloc[0] if not df.empty else None
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Snapshots", total_snapshots)
    col2.metric("Último snapshot", last_snapshot or "N/A")
    col3.metric("Alertas activas", total_alertas)
    col4.metric(
        "Porcentaje escrutado",
        f"{porcentaje:.2f}%" if isinstance(porcentaje, (int, float)) else "N/A",
    )


def trigger_refresh(errors: list[str]) -> None:
    """Lanza el proceso de descarga y hashing sin bloquear la UI."""
    if not st.session_state.get("refresh_requested"):
        return
    st.session_state["refresh_requested"] = False
    script_path = Path("scripts") / "download_and_hash.py"
    if not script_path.exists():
        errors.append(format_read_error("refresh", script_path, "script no encontrado"))
        return
    try:
        subprocess.Popen(
            [sys.executable, str(script_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError as exc:
        errors.append(format_read_error("refresh", script_path, str(exc)))


def main() -> None:
    """Función principal del dashboard."""
    st.set_page_config(page_title="HND-SENTINEL-2029", layout="wide")
    display_header()

    errors: list[str] = []
    trigger_refresh(errors)
    try:
        snapshots = load_snapshots_list()
    except FileNotFoundError as exc:
        handle_read_exception("listado de snapshots", DATA_DIR, exc)
        st.warning(NO_DATA_MESSAGE)
        logger.warning("No data found for dashboard")
        display_footer()
        return
    except Exception as exc:  # noqa: BLE001
        st.error(f"Error al cargar datos: {str(exc)}")
        logger.error("Dashboard data load error: %s", exc)
        display_footer()
        return

    if not snapshots:
        st.warning(NO_DATA_MESSAGE)
        logger.warning("No data found for dashboard")
        display_footer()
        return

    # Normaliza los snapshots disponibles y prepara la vista principal.
    snapshot_data = [load_snapshot_data(path, errors) for path in snapshots]
    latest = snapshot_data[0] if snapshot_data else {}

    filters = render_sidebar()

    df = build_dataframe(snapshot_data, errors)
    try:
        alerts = get_alerts(errors)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Error al cargar datos: {str(exc)}")
        logger.error("Dashboard data load error: %s", exc)
        alerts = []

    df, snapshot_data, latest = apply_departamento_filter(df, snapshot_data, latest)

    display_read_errors(errors)
    display_estado_general(df, alerts)
    display_estado_actual(latest, errors)
    display_table(df)
    display_chart(df)
    display_exports(df, alerts)
    display_alerts(errors, alerts)

    if filters.get("debug") and latest.get("payload"):
        st.subheader("JSON crudo del último snapshot")
        st.json(latest["payload"])

    display_footer()


if __name__ == "__main__":
    main()
