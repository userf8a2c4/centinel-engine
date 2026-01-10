"""Dashboard en Streamlit para monitorear snapshots electorales.

English:
    Streamlit dashboard for monitoring election snapshots.
"""

import json
import logging
import os
import subprocess
import sys
from datetime import datetime
from hashlib import sha256
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from sentinel.utils.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
HASH_DIR = BASE_DIR / "hashes"
ALERTS_LOG = BASE_DIR / "alerts.log"
ALERTS_JSON = DATA_DIR / "alerts.json"
ANALYSIS_RESULTS_JSON = BASE_DIR / "analysis_results.json"
READ_ERROR_PREFIX = "No se pudo leer"
NO_DATA_MESSAGE = (
    "No hay datos disponibles aún. Ejecuta primero: python -m scripts.download_and_hash"
)
REQUIRED_PASSWORD = os.getenv("PASSWORD") or st.secrets.get("PASSWORD")
HONDURAS_DEPARTMENT_CENTERS = {
    "Atlántida": (-86.6, 15.7),
    "Choluteca": (-86.7, 13.6),
    "Colón": (-85.7, 15.8),
    "Comayagua": (-87.5, 14.8),
    "Copán": (-89.1, 14.8),
    "Cortés": (-87.9, 15.4),
    "El Paraíso": (-86.0, 14.0),
    "Francisco Morazán": (-86.9, 14.2),
    "Gracias a Dios": (-84.5, 15.5),
    "Intibucá": (-88.2, 14.4),
    "Islas de la Bahía": (-86.9, 16.3),
    "La Paz": (-87.6, 14.4),
    "Lempira": (-88.6, 14.6),
    "Ocotepeque": (-89.2, 14.4),
    "Olancho": (-85.5, 14.7),
    "Santa Bárbara": (-88.2, 14.9),
    "Valle": (-87.7, 13.6),
    "Yoro": (-87.0, 15.1),
}
HONDURAS_GEOJSON = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {"name": name},
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [lon - 0.3, lat - 0.2],
                        [lon - 0.3, lat + 0.2],
                        [lon + 0.3, lat + 0.2],
                        [lon + 0.3, lat - 0.2],
                        [lon - 0.3, lat - 0.2],
                    ]
                ],
            },
        }
        for name, (lon, lat) in HONDURAS_DEPARTMENT_CENTERS.items()
    ],
}


def enforce_basic_access() -> None:
    """Solicita un password si está configurado.

    English:
        Prompts for a password when configured.
    """
    if not REQUIRED_PASSWORD:
        return

    st.sidebar.markdown("### Acceso / Access")
    provided = st.sidebar.text_input("Password", type="password")
    if not provided:
        st.info("Ingresa el password para continuar. / Enter the password to continue.")
        st.stop()
    if provided != REQUIRED_PASSWORD:
        st.error("Password incorrecto. / Incorrect password.")
        st.stop()


def parse_timestamp_from_name(filename: str) -> datetime | None:
    """Extrae el timestamp desde el nombre del archivo si es posible.

    Espera nombres de archivo tipo: snapshot_2026-01-07_14-30-00.json.

    Args:
        filename (str): Nombre del archivo.

    Returns:
        datetime | None: Timestamp parseado o None si no aplica.

    English:
        Extracts a timestamp from the file name when possible.

        Expected file name format: snapshot_2026-01-07_14-30-00.json.

    Args:
        filename (str): File name.

    Returns:
        datetime | None: Parsed timestamp or None if not applicable.
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
    """Genera mensajes consistentes para errores de lectura.

    Args:
        label (str): Etiqueta del recurso leído.
        path (Path): Ruta asociada al recurso.
        detail (str): Detalle del error.

    Returns:
        str: Mensaje de error formateado.

    English:
        Builds consistent messages for read errors.

    Args:
        label (str): Resource label.
        path (Path): Resource path.
        detail (str): Error detail.

    Returns:
        str: Formatted error message.
    """
    return f"{READ_ERROR_PREFIX} {label} en {path}: {detail}"


def handle_read_exception(
    label: str,
    path: Path,
    exc: Exception,
    errors: list[str] | None = None,
) -> str:
    """Registra y muestra errores de lectura con severidad adecuada.

    Args:
        label (str): Etiqueta del recurso leído.
        path (Path): Ruta del recurso.
        exc (Exception): Excepción capturada.
        errors (list[str] | None): Lista compartida para acumular mensajes.

    Returns:
        str: Mensaje de error generado.

    English:
        Logs and displays read errors with the right severity.

    Args:
        label (str): Resource label.
        path (Path): Resource path.
        exc (Exception): Captured exception.
        errors (list[str] | None): Shared list for messages.

    Returns:
        str: Generated error message.
    """
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
    """Carga JSON con manejo de errores y mensaje uniforme.

    Args:
        path (Path): Ruta del archivo JSON.
        label (str): Etiqueta para el recurso.
        errors (list[str] | None): Lista compartida para errores.

    Returns:
        tuple[dict, str | None]: Datos JSON y mensaje de error si ocurrió.

    English:
        Loads JSON with consistent error handling and messaging.

    Args:
        path (Path): JSON file path.
        label (str): Resource label.
        errors (list[str] | None): Shared list for errors.

    Returns:
        tuple[dict, str | None]: JSON data and error message if any.
    """
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle), None
    except FileNotFoundError as exc:
        return {}, handle_read_exception(label, path, exc, errors)
    except (OSError, json.JSONDecodeError) as exc:
        return {}, handle_read_exception(label, path, exc, errors)


def read_hash_file(
    snapshot_path: Path, errors: list[str] | None = None
) -> tuple[str, str | None]:
    """Lee el hash SHA256 desde el archivo .sha256 si existe.

    Args:
        snapshot_path (Path): Ruta del snapshot.
        errors (list[str] | None): Lista compartida para errores.

    Returns:
        tuple[str, str | None]: Hash leído y mensaje de error si aplica.

    English:
        Reads the SHA-256 hash from the .sha256 file if available.

    Args:
        snapshot_path (Path): Snapshot path.
        errors (list[str] | None): Shared list for errors.

    Returns:
        tuple[str, str | None]: Hash value and error message if any.
    """
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
    """Lista snapshots disponibles ordenados por fecha descendente.

    Returns:
        list[Path]: Lista de rutas de snapshots.

    English:
        Lists available snapshots ordered by most recent.

    Returns:
        list[Path]: Snapshot paths.
    """
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
    """Obtiene timestamp del JSON o del nombre.

    Args:
        snapshot_path (Path): Ruta del snapshot.
        payload (dict): Payload del snapshot.

    Returns:
        datetime | None: Timestamp encontrado o None.

    English:
        Gets a timestamp from JSON content or the file name.

    Args:
        snapshot_path (Path): Snapshot path.
        payload (dict): Snapshot payload.

    Returns:
        datetime | None: Timestamp if found, otherwise None.
    """
    raw = payload.get("timestamp")
    if isinstance(raw, str):
        try:
            return datetime.fromisoformat(raw)
        except ValueError:
            pass
    elif isinstance(raw, datetime):
        return raw
    return parse_timestamp_from_name(snapshot_path.name)


def format_timestamp(timestamp: datetime | None) -> str:
    """Convierte timestamps a texto seguro para UI.

    Args:
        timestamp (datetime | None): Timestamp a formatear.

    Returns:
        str: Texto listo para mostrar.

    English:
        Converts timestamps into UI-safe text.

    Args:
        timestamp (datetime | None): Timestamp to format.

    Returns:
        str: Display-ready text.
    """
    return timestamp.isoformat(sep=" ") if timestamp else ""


def normalize_votos(payload: dict) -> dict:
    """Normaliza el diccionario de votos.

    Args:
        payload (dict): Payload con votos.

    Returns:
        dict: Votos normalizados con números seguros.

    English:
        Normalizes the vote dictionary into safe numeric values.

    Args:
        payload (dict): Payload containing votes.

    Returns:
        dict: Normalized votes with numeric values.
    """
    votos = payload.get("votos") or {}
    if isinstance(votos, dict):
        return {
            str(k): float(v) for k, v in votos.items() if isinstance(v, (int, float))
        }
    return {}


def load_snapshot_data(snapshot_path: Path, errors: list[str]) -> dict:
    """Carga y normaliza datos de un snapshot.

    Los mensajes de error se agregan a la lista compartida para mostrar en UI.

    Args:
        snapshot_path (Path): Ruta del snapshot.
        errors (list[str]): Lista compartida de errores.

    Returns:
        dict: Datos normalizados del snapshot.

    English:
        Loads and normalizes snapshot data.

        Error messages are appended to the shared list for UI display.

    Args:
        snapshot_path (Path): Snapshot path.
        errors (list[str]): Shared error list.

    Returns:
        dict: Normalized snapshot data.
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
    """Agrega columna de cambio porcentual vs snapshot anterior.

    Args:
        df (pd.DataFrame): DataFrame con snapshots.

    Returns:
        pd.DataFrame: DataFrame con columna de cambios.

    English:
        Adds a percent-change column versus the previous snapshot.

    Args:
        df (pd.DataFrame): Snapshot DataFrame.

    Returns:
        pd.DataFrame: DataFrame with change column.
    """
    df = df.copy()
    if "Porcentaje escrutado" not in df.columns:
        df["Cambio %"] = None
        return df
    df["Cambio %"] = df["Porcentaje escrutado"].diff(-1)
    return df


def display_header() -> None:
    """Renderiza el encabezado principal del dashboard.

    English:
        Renders the dashboard header.
    """
    st.markdown(
        "<h1 style='text-align:center;'>"
        "Proyecto C.E.N.T.I.N.E.L. – Auditoría Ciudadana Independiente del CNE Honduras – "
        "Solo hechos y números"
        "</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align:center;'>"
        "Centinela Electrónico Neutral Transparente Íntegro Nacional Electoral Libre"
        "</p>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align:center;'>"
        "Panel operativo en tiempo real para auditoría de snapshots electorales"
        "</p>",
        unsafe_allow_html=True,
    )


def display_footer() -> None:
    """Renderiza el pie institucional del dashboard.

    English:
        Renders the dashboard footer.
    """
    st.markdown("---")
    st.markdown(
        "Proyecto C.E.N.T.I.N.E.L. open-source MIT – Solo datos públicos del CNE – "
        "Preparado para Elecciones 2029 – No alineado políticamente."
    )
    st.markdown("Versión: v0.1-dev (enero 2026)")


def normalize_alerts_payload(alerts: list[dict]) -> list[dict]:
    """Normaliza alertas para el dashboard.

    Args:
        alerts (list[dict]): Alertas crudas desde JSON.

    Returns:
        list[dict]: Alertas con descripción y timestamp uniformes.

    English:
        Normalizes alerts for the dashboard.

    Args:
        alerts (list[dict]): Raw alerts loaded from JSON.

    Returns:
        list[dict]: Alerts with uniform description and timestamp.
    """
    normalized = []
    for entry in alerts:
        if isinstance(entry, dict) and "alerts" in entry:
            for alert in entry.get("alerts", []):
                if not isinstance(alert, dict):
                    continue
                description = alert.get("description") or alert.get("descripcion")
                rule = alert.get("rule")
                if not description and rule:
                    description = f"Regla activada: {rule}"
                normalized.append(
                    {
                        "timestamp": entry.get("to") or entry.get("timestamp", ""),
                        "descripcion": description or "",
                    }
                )
        else:
            normalized.append(entry)
    return normalized


def get_alerts(errors: list[str]) -> list[dict]:
    """Carga alertas desde archivo JSON o log, registrando fallos.

    Args:
        errors (list[str]): Lista compartida para mensajes de error.

    Returns:
        list[dict]: Lista de alertas disponibles.

    English:
        Loads alerts from JSON or log files and logs failures.

    Args:
        errors (list[str]): Shared list for error messages.

    Returns:
        list[dict]: Available alerts.
    """
    if ALERTS_JSON.exists():
        data, _ = safe_read_json(ALERTS_JSON, label="alertas", errors=errors)
        if isinstance(data, list):
            return normalize_alerts_payload(data)
    if ALERTS_LOG.exists():
        try:
            lines = ALERTS_LOG.read_text(encoding="utf-8").splitlines()
            return [
                {"timestamp": "", "descripcion": line} for line in lines if line.strip()
            ]
        except OSError as exc:
            handle_read_exception("alertas/log", ALERTS_LOG, exc, errors)
            return []
    return []


def alerts_to_dataframe(alerts: list[dict]) -> pd.DataFrame:
    """Convierte alertas a DataFrame para exportación.

    Args:
        alerts (list[dict]): Lista de alertas.

    Returns:
        pd.DataFrame: DataFrame listo para exportar.

    English:
        Converts alerts into a DataFrame for export.

    Args:
        alerts (list[dict]): Alert list.

    Returns:
        pd.DataFrame: Export-ready DataFrame.
    """
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
    """Resume alertas en un texto compacto para exportaciones.

    Args:
        alerts (list[dict]): Lista de alertas.

    Returns:
        str: Resumen en una sola línea.

    English:
        Summarizes alerts into a compact string for exports.

    Args:
        alerts (list[dict]): Alert list.

    Returns:
        str: Single-line summary.
    """
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


def load_analysis_results(errors: list[str]) -> dict:
    """Carga resultados de análisis avanzado desde JSON.

    Args:
        errors (list[str]): Lista compartida de errores.

    Returns:
        dict: Resultados de análisis o dict vacío.

    English:
        Loads advanced analysis results from JSON.

    Args:
        errors (list[str]): Shared list for errors.

    Returns:
        dict: Analysis results or empty dict.
    """
    if not ANALYSIS_RESULTS_JSON.exists():
        return {}
    data, _ = safe_read_json(
        ANALYSIS_RESULTS_JSON, label="analysis_results", errors=errors
    )
    return data if isinstance(data, dict) else {}


def display_advanced_analysis(analysis: dict) -> None:
    """Renderiza visualizaciones avanzadas con Plotly.

    Args:
        analysis (dict): Resultados de análisis avanzado.

    English:
        Renders advanced Plotly visualizations.

    Args:
        analysis (dict): Advanced analysis results.
    """
    st.subheader("Advanced Analysis")
    if not analysis:
        st.info("No hay resultados avanzados disponibles.")
        return

    tab_benford, tab_outliers, tab_map = st.tabs(
        ["Benford", "Outliers", "Mapa"]
    )

    with tab_benford:
        benford_rows = []
        for entry in analysis.get("benford", []):
            dept = entry.get("department") or "NACIONAL"
            for candidate, stats in (entry.get("candidates") or {}).items():
                benford_rows.append(
                    {
                        "department": dept,
                        "candidate": candidate,
                        "stats": stats,
                    }
                )
        if not benford_rows:
            st.info("Sin datos de Benford en este momento.")
        else:
            departments = sorted({row["department"] for row in benford_rows})
            selected_dept = st.selectbox(
                "Departamento (Benford)", departments, key="benford_dept"
            )
            candidates = sorted(
                {
                    row["candidate"]
                    for row in benford_rows
                    if row["department"] == selected_dept
                }
            )
            selected_candidate = st.selectbox(
                "Candidato (Benford)", candidates, key="benford_candidate"
            )
            selected = next(
                row
                for row in benford_rows
                if row["department"] == selected_dept
                and row["candidate"] == selected_candidate
            )
            stats = selected["stats"]
            digits = list(range(1, 10))
            observed = [stats["observed_pct"].get(digit, 0) for digit in digits]
            expected = [stats["expected_pct"].get(digit, 0) for digit in digits]
            fig = go.Figure()
            fig.add_bar(x=digits, y=expected, name="Esperado")
            fig.add_bar(x=digits, y=observed, name="Observado")
            fig.update_layout(
                barmode="group",
                xaxis_title="Primer dígito",
                yaxis_title="Porcentaje",
                height=360,
            )
            st.plotly_chart(fig, use_container_width=True)
            st.caption(
                f"Chi-cuadrado: {stats.get('chi2', 0):.2f} | "
                f"p-value: {stats.get('pvalue', 0):.3f} | "
                f"Desviación máx: {stats.get('deviation_pct', 0):.1f}%"
            )

    with tab_outliers:
        series_data = analysis.get("series") or {}
        if not series_data:
            st.info("Sin series temporales para analizar outliers.")
        else:
            departments = sorted(series_data.keys())
            selected_dept = st.selectbox(
                "Departamento (Outliers)", departments, key="outliers_dept"
            )
            series_df = pd.DataFrame(series_data.get(selected_dept, []))
            if series_df.empty:
                st.info("No hay datos para este departamento.")
            else:
                series_df["timestamp"] = pd.to_datetime(
                    series_df["timestamp"], errors="coerce"
                )
                series_df = series_df.dropna(subset=["timestamp"])
                fig = go.Figure()
                fig.add_trace(
                    go.Scatter(
                        x=series_df["timestamp"],
                        y=series_df["total_votes"],
                        mode="lines+markers",
                        name="Votos",
                    )
                )
                if "ml_outlier" in series_df.columns:
                    outliers_df = series_df[series_df["ml_outlier"]]
                    if not outliers_df.empty:
                        fig.add_trace(
                            go.Scatter(
                                x=outliers_df["timestamp"],
                                y=outliers_df["total_votes"],
                                mode="markers",
                                marker={"color": "red", "size": 10},
                                name="Outliers",
                            )
                        )
                fig.update_layout(
                    xaxis_title="Tiempo",
                    yaxis_title="Votos acumulados",
                    height=360,
                )
                st.plotly_chart(fig, use_container_width=True)

    with tab_map:
        series_data = analysis.get("series") or {}
        if not series_data:
            st.info("Sin datos para mapa.")
        else:
            rows = []
            for dept, records in series_data.items():
                if not records:
                    continue
                last = records[-1]
                rows.append(
                    {
                        "Departamento": dept,
                        "Total votos": last.get("total_votes", 0),
                    }
                )
            if not rows:
                st.info("No hay datos suficientes para el mapa.")
            else:
                map_df = pd.DataFrame(rows)
                fig = px.choropleth(
                    map_df,
                    geojson=HONDURAS_GEOJSON,
                    locations="Departamento",
                    featureidkey="properties.name",
                    color="Total votos",
                    color_continuous_scale="Blues",
                    hover_name="Departamento",
                )
                fig.update_geos(fitbounds="locations", visible=False)
                fig.update_layout(height=420)
                st.plotly_chart(fig, use_container_width=True)


def build_snapshot_export(df: pd.DataFrame, alerts: list[dict]) -> pd.DataFrame:
    """Construye el CSV de snapshots con columnas útiles.

    Args:
        df (pd.DataFrame): DataFrame con snapshots.
        alerts (list[dict]): Alertas registradas.

    Returns:
        pd.DataFrame: DataFrame listo para exportar.

    English:
        Builds a snapshot CSV with useful columns.

    Args:
        df (pd.DataFrame): Snapshot DataFrame.
        alerts (list[dict]): Recorded alerts.

    Returns:
        pd.DataFrame: Export-ready DataFrame.
    """
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
    """Renderiza alertas o un placeholder.

    Args:
        errors (list[str]): Lista compartida de errores.
        alerts (list[dict] | None): Alertas ya cargadas (opcional).

    English:
        Renders alerts or a placeholder message.

    Args:
        errors (list[str]): Shared error list.
        alerts (list[dict] | None): Preloaded alerts (optional).
    """
    st.subheader("Alertas y anomalías")
    alerts = alerts if alerts is not None else get_alerts(errors)
    if not alerts:
        st.info("No hay alertas recientes.")
        return
    st.dataframe(alerts_to_dataframe(alerts), use_container_width=True)


def display_exports(df: pd.DataFrame, alerts: list[dict]) -> None:
    """Sección de exportación rápida para compartir reportes.

    Args:
        df (pd.DataFrame): DataFrame con snapshots.
        alerts (list[dict]): Alertas registradas.

    English:
        Quick export section for sharing reports.

    Args:
        df (pd.DataFrame): Snapshot DataFrame.
        alerts (list[dict]): Recorded alerts.
    """
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
    """Construye DataFrame para tabla y gráficos.

    Args:
        snapshot_data (list[dict]): Lista de datos de snapshots.
        errors (list[str]): Lista compartida de errores.

    Returns:
        pd.DataFrame: DataFrame con columnas para UI.

    English:
        Builds a DataFrame for tables and charts.

    Args:
        snapshot_data (list[dict]): Snapshot data list.
        errors (list[str]): Shared error list.

    Returns:
        pd.DataFrame: DataFrame with UI columns.
    """
    rows = []
    for item in snapshot_data:
        timestamp = item["timestamp"]
        hash_value = ""
        hash_error = None
        if item.get("path"):
            hash_value, hash_error = read_hash_file(item["path"], errors=errors)
        rows.append(
            {
                "Fecha/Hora": format_timestamp(timestamp),
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
    """Renderiza la sección con detalle del último snapshot.

    Args:
        latest (dict): Datos del snapshot más reciente.
        errors (list[str]): Lista compartida de errores.

    English:
        Renders the section with details of the latest snapshot.

    Args:
        latest (dict): Latest snapshot data.
        errors (list[str]): Shared error list.
    """
    with st.expander("Estado actual", expanded=True):
        timestamp = latest.get("timestamp")
        timestamp_text = format_timestamp(timestamp)
        st.write(f"**Último snapshot:** {timestamp_text or 'Sin fecha'}")
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
        st.write(
            f"**Total votos acumulados:** {total_votos if total_votos is not None else 'N/A'}"
        )
        st.write(f"**Última actualización:** {timestamp_text or 'N/A'}")


def display_table(df: pd.DataFrame) -> None:
    """Renderiza la tabla con los últimos snapshots.

    Args:
        df (pd.DataFrame): DataFrame con snapshots.

    English:
        Renders the table with the latest snapshots.

    Args:
        df (pd.DataFrame): Snapshot DataFrame.
    """
    st.subheader("Últimos snapshots")
    if df.empty:
        st.info(NO_DATA_MESSAGE)
        return
    # Presentación compacta del hash para facilitar la lectura.
    table_df = df[
        ["Fecha/Hora", "Nombre archivo", "Hash", "Porcentaje escrutado"]
    ].copy()
    table_df = compute_diffs(table_df)
    table_df["Hash"] = table_df["Hash"].apply(
        lambda value: f"{value[:12]}..." if isinstance(value, str) and value else ""
    )
    st.dataframe(table_df.head(10), use_container_width=True)
    export_df = df.copy()
    if "Votos" in export_df.columns:
        export_df["Votos"] = export_df["Votos"].apply(
            lambda value: (
                json.dumps(value, ensure_ascii=False) if isinstance(value, dict) else ""
            )
        )
    csv_data = export_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Descargar snapshots (CSV)",
        data=csv_data,
        file_name="snapshots.csv",
        mime="text/csv",
    )


def display_chart(df: pd.DataFrame) -> None:
    """Renderiza el gráfico temporal del porcentaje escrutado.

    Args:
        df (pd.DataFrame): DataFrame con snapshots.

    English:
        Renders the time chart for the scrutiny percentage.

    Args:
        df (pd.DataFrame): Snapshot DataFrame.
    """
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


def render_sidebar(errors: list[str]) -> dict:
    """Renderiza la barra lateral para filtros y acciones.

    Args:
        errors (list[str]): Lista compartida de errores.

    Returns:
        dict: Estado de filtros y toggles activos.

    English:
        Renders the sidebar for filters and actions.

    Args:
        errors (list[str]): Shared error list.

    Returns:
        dict: Current filter/toggle state.
    """
    st.sidebar.header("Filtros y acciones")
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
    """Renderiza errores de lectura de forma consistente.

    Args:
        errors (list[str]): Lista de errores detectados.

    English:
        Renders read errors in a consistent format.

    Args:
        errors (list[str]): Detected error list.
    """
    if not errors:
        return
    unique_errors = sorted(set(errors))
    st.warning("Se detectaron problemas al leer archivos:")
    for error in unique_errors:
        st.write(f"- {error}")


def apply_departamento_filter(
    df: pd.DataFrame, snapshot_data: list[dict], latest: dict
) -> tuple[pd.DataFrame, list[dict], dict]:
    """Aplica filtro por departamento si la columna está disponible.

    Args:
        df (pd.DataFrame): DataFrame con snapshots.
        snapshot_data (list[dict]): Lista original de snapshots.
        latest (dict): Snapshot más reciente.

    Returns:
        tuple[pd.DataFrame, list[dict], dict]: Datos filtrados y latest ajustado.

    English:
        Applies a department filter when the column exists.

    Args:
        df (pd.DataFrame): Snapshot DataFrame.
        snapshot_data (list[dict]): Original snapshot list.
        latest (dict): Latest snapshot.

    Returns:
        tuple[pd.DataFrame, list[dict], dict]: Filtered data and updated latest.
    """
    if "Departamento" not in df.columns or df.empty:
        return df, snapshot_data, latest
    departamentos = ["Todos"] + sorted(df["Departamento"].dropna().unique().tolist())
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
    """Renderiza un resumen general con métricas clave.

    Args:
        df (pd.DataFrame): DataFrame con snapshots.
        alerts (list[dict]): Lista de alertas.

    English:
        Renders a general summary with key metrics.

    Args:
        df (pd.DataFrame): Snapshot DataFrame.
        alerts (list[dict]): Alert list.
    """
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
    """Lanza el proceso de descarga y hashing sin bloquear la UI.

    Args:
        errors (list[str]): Lista compartida de errores.

    English:
        Triggers snapshot download and hashing without blocking the UI.

    Args:
        errors (list[str]): Shared error list.
    """
    if not st.session_state.get("refresh_requested"):
        return
    st.session_state["refresh_requested"] = False
    script_path = BASE_DIR / "scripts" / "download_and_hash.py"
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
    """Función principal del dashboard.

    English:
        Main entry point for the dashboard.
    """
    st.set_page_config(page_title="Proyecto C.E.N.T.I.N.E.L.", layout="wide")
    enforce_basic_access()
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

    filters = render_sidebar(errors)

    df = build_dataframe(snapshot_data, errors)
    try:
        alerts = get_alerts(errors)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Error al cargar datos: {str(exc)}")
        logger.error("Dashboard data load error: %s", exc)
        alerts = []

    analysis = load_analysis_results(errors)
    df, snapshot_data, latest = apply_departamento_filter(df, snapshot_data, latest)

    display_read_errors(errors)
    display_estado_general(df, alerts)
    display_estado_actual(latest, errors)
    display_table(df)
    display_chart(df)
    display_advanced_analysis(analysis)
    display_exports(df, alerts)
    display_alerts(errors, alerts)

    if filters.get("debug") and latest.get("payload"):
        st.subheader("JSON crudo del último snapshot")
        st.json(latest["payload"])

    display_footer()


if __name__ == "__main__":
    main()
