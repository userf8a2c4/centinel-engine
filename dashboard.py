"""Streamlit dashboard para monitoreo de snapshots electorales."""

import json
import os
from datetime import datetime
from hashlib import sha256
from pathlib import Path

import pandas as pd
import streamlit as st


DATA_DIR = Path("data")
HASH_DIR = Path("hashes")
ALERTS_LOG = Path("alerts.log")
ALERTS_JSON = DATA_DIR / "alerts.json"
REPORTS_DIR = Path("reports")
DEFAULT_PDF_REPORT = REPORTS_DIR / "latest_report.pdf"
READ_ERROR_PREFIX = "No se pudo leer"


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


def safe_read_json(path: Path, label: str = "JSON") -> tuple[dict, str | None]:
    """Carga JSON con manejo de errores y mensaje uniforme."""
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle), None
    except FileNotFoundError:
        return {}, format_read_error(label, path, "archivo no encontrado")
    except (OSError, json.JSONDecodeError) as exc:
        return {}, format_read_error(label, path, str(exc))


def read_hash_file(snapshot_path: Path) -> tuple[str, str | None]:
    """Lee el hash SHA256 desde el archivo .sha256 si existe."""
    hash_path = HASH_DIR / f"{snapshot_path.name}.sha256"
    try:
        if hash_path.exists():
            return hash_path.read_text(encoding="utf-8").strip(), None
        if snapshot_path.exists():
            return sha256(snapshot_path.read_bytes()).hexdigest(), None
        return "", format_read_error("snapshot/hash", snapshot_path, "archivo no encontrado")
    except OSError as exc:
        return "", format_read_error("snapshot/hash", hash_path, str(exc))


def load_snapshots_list() -> list[Path]:
    """Lista snapshots disponibles ordenados por fecha descendente."""
    # Ordena por fecha de modificación para priorizar el snapshot más reciente.
    if not DATA_DIR.exists():
        return []
    snapshots = sorted(DATA_DIR.glob("*.json"), key=os.path.getmtime, reverse=True)
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
    payload, error = safe_read_json(snapshot_path, label="snapshot")
    if error:
        errors.append(error)
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
    df["Cambio %"] = df["Porcentaje escrutado"].diff(-1)
    return df


def display_header() -> None:
    """Muestra el encabezado principal."""
    st.markdown(
        "<h1 style='text-align:center;'>"
        "HND-SENTINEL-2029 – Auditoría Ciudadana Independiente del CNE Honduras – "
        "Solo hechos y números"
        "</h1>",
        unsafe_allow_html=True,
    )


def display_footer() -> None:
    """Footer institucional."""
    st.markdown("---")
    st.markdown(
        "Proyecto open-source MIT – Solo datos públicos del CNE – "
        "Preparado para Elecciones 2029 – No alineado políticamente."
    )
    st.markdown("Versión: v0.1-dev (enero 2026)")


def get_alerts(errors: list[str]) -> list[dict]:
    """Carga alertas desde archivo si existe."""
    if ALERTS_JSON.exists():
        data, error = safe_read_json(ALERTS_JSON, label="alertas")
        if error:
            errors.append(error)
        if isinstance(data, list):
            return data
    if ALERTS_LOG.exists():
        try:
            lines = ALERTS_LOG.read_text(encoding="utf-8").splitlines()
            return [{"timestamp": "", "descripcion": line} for line in lines if line.strip()]
        except OSError:
            return []
    return []


def display_alerts(errors: list[str]) -> None:
    """Renderiza alertas o un placeholder."""
    st.subheader("Alertas y anomalías")
    alerts = get_alerts(errors)
    if not alerts:
        st.info("No hay alertas recientes.")
        return
    alert_rows = []
    for alert in alerts:
        alert_rows.append(
            {
                "Timestamp": alert.get("timestamp", ""),
                "Descripción": alert.get("descripcion", alert.get("description", "")),
            }
        )
    alerts_df = pd.DataFrame(alert_rows)
    st.dataframe(alerts_df, use_container_width=True)
    if not alerts_df.empty:
        csv_data = alerts_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Descargar alertas (CSV)",
            data=csv_data,
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
            hash_value, hash_error = read_hash_file(item["path"])
        if hash_error:
            errors.append(hash_error)
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
    """Muestra la sección de estado actual."""
    with st.expander("Estado actual", expanded=True):
        timestamp = latest.get("timestamp")
        st.write(
            f"**Último snapshot:** {timestamp.isoformat(sep=' ') if timestamp else 'Sin fecha'}"
        )
        snapshot_path = latest.get("path")
        hash_value = ""
        if snapshot_path:
            hash_value, error = read_hash_file(snapshot_path)
            if error:
                errors.append(error)
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
    """Tabla de últimos snapshots."""
    st.subheader("Últimos snapshots")
    if df.empty:
        st.info("Aún no hay snapshots. Corre download_and_hash.py primero.")
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
    """Grafico de evolución del escrutinio y votos."""
    st.subheader("Evolución del escrutinio")
    if df.empty:
        st.info("No hay datos para graficar.")
        return
    chart_df = df.copy()
    chart_df = chart_df.sort_values("Fecha/Hora")
    chart_df["timestamp"] = pd.to_datetime(chart_df["Fecha/Hora"], errors="coerce")
    chart_df = chart_df.dropna(subset=["timestamp"])
    chart_data = chart_df.set_index("timestamp")[["Porcentaje escrutado"]]
    votos_cols = {}
    for _, row in df.iterrows():
        votos = row.get("Votos") or {}
        if isinstance(votos, dict):
            for key, value in votos.items():
                col_name = f"votos_{key}"
                votos_cols.setdefault(col_name, []).append(value)
        else:
            for col in votos_cols:
                votos_cols[col].append(None)
    if votos_cols:
        votos_df = pd.DataFrame(votos_cols)
        votos_df.index = chart_df.index
        chart_data = pd.concat([chart_data, votos_df], axis=1)
    st.line_chart(chart_data)


def render_sidebar(snapshot_data: list[dict]) -> dict:
    """Sidebar interactiva para filtros y acciones."""
    st.sidebar.header("Filtros y acciones")
    if DEFAULT_PDF_REPORT.exists():
        report_bytes = DEFAULT_PDF_REPORT.read_bytes()
        st.sidebar.download_button(
            label="Descargar reporte PDF",
            data=report_bytes,
            file_name=DEFAULT_PDF_REPORT.name,
            mime="application/pdf",
        )
    else:
        st.sidebar.caption("Genera un reporte PDF para habilitar la descarga.")
    departamentos = sorted(
        {item.get("departamento") for item in snapshot_data if item.get("departamento")}
    )
    departamento = None
    if departamentos:
        departamento = st.sidebar.selectbox("Filtrar por departamento", ["Todos"] + departamentos)
    if st.sidebar.button("Actualizar datos ahora"):
        st.sidebar.info("Ejecutando downloader... (simulado)")
        st.rerun()
    debug = st.sidebar.checkbox("Modo debug: mostrar JSON crudo del último snapshot")
    st.sidebar.markdown("[Ver repo en GitHub](https://github.com/userf8a2c4/sentinel)")
    return {"departamento": departamento, "debug": debug}


def display_read_errors(errors: list[str]) -> None:
    """Renderiza errores de lectura de forma consistente."""
    if not errors:
        return
    unique_errors = sorted(set(errors))
    st.warning("Se detectaron problemas al leer archivos:")
    for error in unique_errors:
        st.write(f"- {error}")


def main() -> None:
    """Función principal del dashboard."""
    st.set_page_config(page_title="HND-SENTINEL-2029", layout="wide")
    display_header()

    errors: list[str] = []
    snapshots = load_snapshots_list()
    if not snapshots:
        st.info("Aún no hay snapshots. Corre download_and_hash.py primero.")
        display_footer()
        return

    # Normaliza los snapshots disponibles y prepara la vista principal.
    snapshot_data = [load_snapshot_data(path, errors) for path in snapshots]
    latest = snapshot_data[0] if snapshot_data else {}

    filters = render_sidebar(snapshot_data)
    departamento = filters.get("departamento")
    if departamento and departamento != "Todos":
        snapshot_data = [
            item for item in snapshot_data if item.get("departamento") == departamento
        ]
        if snapshot_data:
            latest = snapshot_data[0]

    df = build_dataframe(snapshot_data, errors)

    display_read_errors(errors)
    display_estado_actual(latest, errors)
    display_table(df)
    display_chart(df)
    display_alerts(errors)

    if filters.get("debug") and latest.get("payload"):
        st.subheader("JSON crudo del último snapshot")
        st.json(latest["payload"])

    display_footer()


if __name__ == "__main__":
    main()
