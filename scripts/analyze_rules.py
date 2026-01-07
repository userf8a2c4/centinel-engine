import json
import os
import glob
import math
import collections
import logging
import sqlite3
from datetime import datetime

import pandas as pd
from dateutil import parser

from logging_utils import configure_logging, log_event
# PROTOCOLO HND-SENTINEL-2029 // AUDITORÍA RESILIENTE
# Versión optimizada para datos históricos 2025 y futuros 2029

logger = configure_logging("sentinel.analyze")

def load_json(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        log_event(logger, logging.ERROR, "load_error", file_path=file_path, error=str(e))
        return None

def safe_int(value, default=0):
    """Convierte a entero de forma segura, manejando strings y nulos."""
    try:
        if value is None: return default
        return int(str(value).replace(',', '').split('.')[0])
    except (ValueError, TypeError):
        return default

def parse_timestamp(data, file_name):
    raw_ts = data.get('timestamp') or data.get('timestamp_utc') or data.get('fecha')
    meta = data.get("meta") or data.get("metadata") or {}
    raw_ts = raw_ts or meta.get("timestamp_utc")
    if raw_ts:
        try:
            return parser.parse(raw_ts)
        except (ValueError, TypeError):
            pass

    stem = os.path.splitext(file_name)[0]
    stem = stem.replace('snapshot_', '').replace('_', ' ').replace('-', '-')
    try:
        return parser.parse(stem)
    except (ValueError, TypeError):
        return None

def extract_department_records(data, file_name):
    timestamp = parse_timestamp(data, file_name)
    if not timestamp:
        return []

    records = []
    meta = data.get("meta") or data.get("metadata") or {}
    if isinstance(data.get('resultados'), dict):
        departamento = (
            meta.get("department")
            or data.get('departamento')
            or data.get('departamento_nombre')
            or 'NACIONAL'
        )
        total_votes = sum(safe_int(v) for v in data['resultados'].values())
        actas = data.get('actas', {})
        actas_procesadas = safe_int(
            actas.get('correctas')
            or actas.get('divulgadas')
            or actas.get('totales')
        )
        records.append({
            "timestamp": timestamp,
            "departamento": departamento,
            "total_votes": total_votes,
            "actas_procesadas": actas_procesadas,
        })
        return records

    totals = data.get("totals") or {}
    candidatos = data.get("candidates")
    if isinstance(candidatos, list):
        departamento = meta.get("department") or "NACIONAL"
        total_votes = safe_int(totals.get("total_votes"))
        actas = totals.get("actas_procesadas") or totals.get("actas") or data.get("actas")
        actas_procesadas = safe_int(actas)
        records.append({
            "timestamp": timestamp,
            "departamento": departamento,
            "total_votes": total_votes,
            "actas_procesadas": actas_procesadas,
        })
        return records

    votos_actuales = data.get('votos') or data.get('candidates') or []
    if isinstance(votos_actuales, list):
        dept_totals = collections.defaultdict(int)
        for c in votos_actuales:
            departamento = c.get('departamento') or c.get('dep') or 'NACIONAL'
            dept_totals[departamento] += safe_int(c.get('votos'))
        for departamento, total_votes in dept_totals.items():
            records.append({
                "timestamp": timestamp,
                "departamento": departamento,
                "total_votes": total_votes,
                "actas_procesadas": safe_int(
                    data.get('actas_procesadas')
                    or data.get('actas')
                    or 0
                ),
            })
    return records

def apply_benford_law(votos_lista):
    """Analiza la distribución del primer dígito (Ley de Benford)."""
    # Solo procesamos si hay suficientes datos para evitar falsos positivos
    if len(votos_lista) < 10: 
        return None

    first_digits = []
    for c in votos_lista:
        votos_str = str(c.get('votos') or c.get("votes") or '').strip()
        if votos_str and votos_str not in ['0', 'None']:
            first_digits.append(int(votos_str[0]))
    
    if not first_digits: return None
    
    counts = collections.Counter(first_digits)
    total = len(first_digits)
    
    # Análisis de anomalía: el '1' debe ser ~30%. Si es < 20%, se marca como sospecha.
    dist_1 = (counts[1] / total) * 100
    is_anomaly = dist_1 < 20.0
    
    return {"is_anomaly": is_anomaly, "prop_1": dist_1}

def check_arithmetic_consistency(data, file_name):
    totals = data.get("totals") or {}
    candidates = data.get("candidates")
    if not totals or not isinstance(candidates, list):
        return None

    total_votes = safe_int(totals.get("total_votes") or totals.get("valid_votes"))
    candidates_total = sum(safe_int(c.get("votes") or c.get("votos")) for c in candidates)
    if total_votes and candidates_total != total_votes:
        return {
            "file": file_name,
            "type": "ARITHMETIC_MISMATCH",
            "expected_total": total_votes,
            "observed_total": candidates_total,
        }
    return None

def compute_trend_metrics(series_df):
    if series_df.shape[0] < 2:
        return {
            "slope_votes": None,
            "acceleration_votes": None,
            "ratio_votos_actas": None,
        }

    base_time = series_df["timestamp"].iloc[0]
    x = (series_df["timestamp"] - base_time).dt.total_seconds() / 3600
    y = series_df["total_votes"]
    slope = pd.Series(x).cov(y) / pd.Series(x).var() if pd.Series(x).var() else 0.0
    intercept = y.mean() - slope * x.mean()

    delta_votes = series_df["delta_votes"].dropna()
    acc = None
    if len(delta_votes) > 1:
        x_delta = x.iloc[1:]
        acc = pd.Series(x_delta).cov(delta_votes) / pd.Series(x_delta).var() if pd.Series(x_delta).var() else 0.0

    ratio = None
    last_actas = series_df["actas_procesadas"].iloc[-1]
    if last_actas:
        ratio = series_df["total_votes"].iloc[-1] / last_actas

    return {
        "slope_votes": slope,
        "intercept_votes": intercept,
        "acceleration_votes": acc,
        "ratio_votos_actas": ratio,
    }

def build_prediction(series_df, trend_metrics):
    if series_df.shape[0] < 3:
        return None

    base_time = series_df["timestamp"].iloc[0]
    x = (series_df["timestamp"] - base_time).dt.total_seconds() / 3600
    y = series_df["total_votes"].astype(float)
    slope = trend_metrics.get("slope_votes")
    intercept = trend_metrics.get("intercept_votes")
    if slope is None or intercept is None:
        return None

    residuals = y - (slope * x + intercept)
    std_resid = residuals.std(ddof=1) if len(residuals) > 1 else None
    median_delta = series_df["timestamp"].diff().median()
    if pd.isna(median_delta):
        return None
    next_time = series_df["timestamp"].iloc[-1] + median_delta
    next_x = (next_time - base_time).total_seconds() / 3600
    prediction = slope * next_x + intercept

    interval = None
    if std_resid is not None and not math.isnan(std_resid):
        interval = {
            "lower": prediction - 1.96 * std_resid,
            "upper": prediction + 1.96 * std_resid,
        }

    return {
        "timestamp": next_time.isoformat(),
        "prediction": prediction,
        "interval_95": interval,
    }

def run_audit(target_directory='data/normalized'):
    peak_votos = {}
    anomalies_log = []
    records = []

    file_list = sorted(glob.glob(os.path.join(target_directory, '*.json')))
    if not file_list:
        log_event(logger, logging.WARNING, "no_files_found", target_directory=target_directory)
        return

    log_event(logger, logging.INFO, "processing_snapshots", count=len(file_list), target_directory=target_directory)

    for file_path in file_list:
        data = load_json(file_path)
        if not data:
            continue

        file_name = os.path.basename(file_path)
        votos_actuales = data.get('votos') or data.get('candidates') or []
        records.extend(extract_department_records(data, file_name))

        arithmetic_issue = check_arithmetic_consistency(data, file_name)
        if arithmetic_issue:
            anomalies_log.append(arithmetic_issue)

        for c in votos_actuales:
            c_id = str(c.get('id') or c.get('candidate_id') or c.get('nombre') or c.get("name") or 'unknown')
            v_actual = safe_int(c.get('votos') or c.get("votes"))

            if c_id in peak_votos:
                if v_actual < peak_votos[c_id]['valor']:
                    diff = v_actual - peak_votos[c_id]['valor']
                    log_event(logger, logging.WARNING, "negative_delta", candidate_id=c_id, loss=diff, file=file_name)
                    anomalies_log.append({
                        "file": file_name,
                        "type": "NEGATIVE_DELTA",
                        "entity": c_id,
                        "loss": diff
                    })

            if c_id not in peak_votos or v_actual > peak_votos[c_id]['valor']:
                peak_votos[c_id] = {'valor': v_actual, 'file': file_name}

        benford = apply_benford_law(votos_actuales)
        if benford and benford['is_anomaly']:
            log_event(
                logger,
                logging.WARNING,
                "benford_anomaly",
                file=file_name,
                prop_1=f"{benford['prop_1']:.1f}",
            )

    if not records:
        log_event(logger, logging.WARNING, "no_department_records")
        return

    df = pd.DataFrame(records)
    df = df.sort_values(["departamento", "timestamp"]).reset_index(drop=True)
    df["delta_votes"] = df.groupby("departamento")["total_votes"].diff()
    df["delta_actas"] = df.groupby("departamento")["actas_procesadas"].diff()

    anomalies = []
    metrics_by_dept = {}
    predictions = {}

    for departamento, group in df.groupby("departamento"):
        group = group.copy()
        delta_votes = group["delta_votes"].dropna()
        if not delta_votes.empty:
            mean_delta = delta_votes.mean()
            std_delta = delta_votes.std(ddof=1) if len(delta_votes) > 1 else 0.0
            q1 = delta_votes.quantile(0.25)
            q3 = delta_votes.quantile(0.75)
            iqr = q3 - q1

            group["zscore_delta"] = (group["delta_votes"] - mean_delta) / std_delta if std_delta else 0.0
            group["outlier_zscore"] = group["zscore_delta"].abs() > 3
            group["outlier_iqr"] = (group["delta_votes"] < q1 - 1.5 * iqr) | (group["delta_votes"] > q3 + 1.5 * iqr)
            group["change_point"] = group["delta_votes"].abs() > mean_delta + 3 * std_delta if std_delta else False
        else:
            group["zscore_delta"] = None
            group["outlier_zscore"] = False
            group["outlier_iqr"] = False
            group["change_point"] = False

        for _, row in group.iterrows():
            if row["change_point"]:
                anomalies.append({
                    "departamento": departamento,
                    "type": "CHANGE_POINT",
                    "timestamp": row["timestamp"].isoformat(),
                    "delta_votes": row["delta_votes"],
                })
            if row["outlier_zscore"] or row["outlier_iqr"]:
                anomalies.append({
                    "departamento": departamento,
                    "type": "OUTLIER",
                    "timestamp": row["timestamp"].isoformat(),
                    "delta_votes": row["delta_votes"],
                    "method": "zscore" if row["outlier_zscore"] else "iqr",
                })
            if (row["delta_votes"] or 0) > 0 and (row["delta_actas"] or 0) <= 0:
                anomalies.append({
                    "departamento": departamento,
                    "type": "ACTAS_DESVIO",
                    "timestamp": row["timestamp"].isoformat(),
                    "delta_votes": row["delta_votes"],
                    "delta_actas": row["delta_actas"],
                })

        trend_metrics = compute_trend_metrics(group)
        metrics_by_dept[departamento] = trend_metrics
        prediction = build_prediction(group, trend_metrics)
        if prediction:
            predictions[departamento] = prediction

        df.loc[group.index, "zscore_delta"] = group["zscore_delta"].values
        df.loc[group.index, "outlier_zscore"] = group["outlier_zscore"].values
        df.loc[group.index, "outlier_iqr"] = group["outlier_iqr"].values
        df.loc[group.index, "change_point"] = group["change_point"].values

    series_payload = {}
    for dept, group in df.groupby("departamento"):
        payload = group.drop(
            columns=["zscore_delta", "outlier_zscore", "outlier_iqr", "change_point"]
        ).copy()
        payload["timestamp"] = payload["timestamp"].astype(str)
        series_payload[dept] = payload.to_dict(orient="records")

    output = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "departments": metrics_by_dept,
        "predictions": predictions,
        "anomalies": anomalies_log + anomalies,
        "series": series_payload,
    }

    with open('analysis_results.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=4, ensure_ascii=False)

    try:
        df.to_parquet('analysis_results.parquet', index=False)
    except Exception as e:
        log_event(logger, logging.WARNING, "parquet_write_failed", error=str(e))

    with open('anomalies_report.json', 'w') as f:
        json.dump(anomalies_log + anomalies, f, indent=4)

    reports_dir = "reports"
    os.makedirs(reports_dir, exist_ok=True)
    with open(os.path.join(reports_dir, "summary_es.txt"), "w", encoding="utf-8") as f:
        f.write(build_plain_summary(output, language="es"))
    with open(os.path.join(reports_dir, "summary_en.txt"), "w", encoding="utf-8") as f:
        f.write(build_plain_summary(output, language="en"))

    persist_to_sqlite(output, os.path.join(reports_dir, "sentinel.db"))
    log_event(logger, logging.INFO, "audit_completed", reports_dir=reports_dir)


def persist_to_sqlite(output, sqlite_path):
    connection = sqlite3.connect(sqlite_path)
    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS anomalies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            generated_at TEXT,
            payload TEXT
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS department_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            generated_at TEXT,
            department TEXT,
            payload TEXT
        )
        """
    )

    generated_at = output.get("generated_at")
    anomalies = output.get("anomalies", [])
    cursor.execute(
        "INSERT INTO anomalies (generated_at, payload) VALUES (?, ?)",
        (generated_at, json.dumps(anomalies, ensure_ascii=False)),
    )

    for dept, metrics in output.get("departments", {}).items():
        cursor.execute(
            "INSERT INTO department_metrics (generated_at, department, payload) VALUES (?, ?, ?)",
            (generated_at, dept, json.dumps(metrics, ensure_ascii=False)),
        )

    connection.commit()
    connection.close()


def build_plain_summary(output, language="es"):
    generated_at = output.get("generated_at")
    anomalies = output.get("anomalies", [])
    departments = output.get("departments", {})
    total_anomalies = len(anomalies)
    lines = []

    if language == "en":
        lines.append("HND-SENTINEL-2029 | Plain-language summary")
        lines.append(f"Generated at (UTC): {generated_at}")
        lines.append(f"Total events detected: {total_anomalies}")
        lines.append("")
        lines.append("What this means:")
        lines.append("- The system checks for sudden changes, regressions, and arithmetic mismatches.")
        lines.append("- Events indicate unusual data behavior, not intent or responsibility.")
        lines.append("")
        lines.append("Department overview:")
        for dept, metrics in departments.items():
            slope = metrics.get("slope_votes")
            ratio = metrics.get("ratio_votos_actas")
            lines.append(f"- {dept}: trend slope={format_metric(slope)}, votes/actas={format_metric(ratio)}")
    else:
        lines.append("HND-SENTINEL-2029 | Resumen en lenguaje común")
        lines.append(f"Generado (UTC): {generated_at}")
        lines.append(f"Eventos detectados: {total_anomalies}")
        lines.append("")
        lines.append("Qué significa:")
        lines.append("- El sistema revisa cambios abruptos, regresiones y desajustes aritméticos.")
        lines.append("- Los eventos indican comportamientos inusuales en los datos, no intención ni responsabilidad.")
        lines.append("")
        lines.append("Resumen por departamento:")
        for dept, metrics in departments.items():
            slope = metrics.get("slope_votes")
            ratio = metrics.get("ratio_votos_actas")
            lines.append(f"- {dept}: tendencia={format_metric(slope)}, votos/actas={format_metric(ratio)}")

    return "\n".join(lines)


def format_metric(value):
    if value is None:
        return "N/D"
    return f"{value:.2f}"

if __name__ == "__main__":
    run_audit()
