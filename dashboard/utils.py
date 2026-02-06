"""Utilidades para el dashboard electoral C.E.N.T.I.N.E.L.

Español: Funciones de carga, normalización y cálculo de métricas.
English: Loading, normalization, and metrics utilities.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm

from rules.benford import BenfordResult, evaluate_benford


DEPARTMENTS = [
    "Atlántida",
    "Choluteca",
    "Colón",
    "Comayagua",
    "Copán",
    "Cortés",
    "El Paraíso",
    "Francisco Morazán",
    "Gracias a Dios",
    "Intibucá",
    "Islas de la Bahía",
    "La Paz",
    "Lempira",
    "Ocotepeque",
    "Olancho",
    "Santa Bárbara",
    "Valle",
    "Yoro",
]

DEPARTMENT_SLUGS = {
    "Atlántida": "atlantida",
    "Choluteca": "choluteca",
    "Colón": "colon",
    "Comayagua": "comayagua",
    "Copán": "copan",
    "Cortés": "cortes",
    "El Paraíso": "el-paraiso",
    "Francisco Morazán": "francisco-morazan",
    "Gracias a Dios": "gracias-a-dios",
    "Intibucá": "intibuca",
    "Islas de la Bahía": "islas-bahia",
    "La Paz": "la-paz",
    "Lempira": "lempira",
    "Ocotepeque": "ocotepeque",
    "Olancho": "olancho",
    "Santa Bárbara": "santa-barbara",
    "Valle": "valle",
    "Yoro": "yoro",
}

DEPARTMENT_COORDS = {
    "Atlántida": (15.76, -86.77),
    "Choluteca": (13.30, -87.15),
    "Colón": (15.65, -85.58),
    "Comayagua": (14.55, -87.65),
    "Copán": (14.83, -89.15),
    "Cortés": (15.50, -88.03),
    "El Paraíso": (14.10, -86.35),
    "Francisco Morazán": (14.20, -87.20),
    "Gracias a Dios": (15.10, -84.65),
    "Intibucá": (14.30, -88.15),
    "Islas de la Bahía": (16.30, -86.50),
    "La Paz": (14.30, -87.70),
    "Lempira": (14.55, -88.58),
    "Ocotepeque": (14.50, -89.20),
    "Olancho": (14.65, -86.20),
    "Santa Bárbara": (15.10, -88.30),
    "Valle": (13.50, -87.62),
    "Yoro": (15.13, -87.13),
}


@dataclass
class ParsedResult:
    """Resultado normalizado por departamento.

    Español: Contiene votos por candidato y totales clave.
    English: Holds candidate votes and key totals.
    """

    department: str
    candidates: pd.DataFrame
    total_valid: int
    null_votes: int
    invalid_votes: int
    registered: int
    timestamp: Optional[datetime]


@dataclass
class AuditAlert:
    """Alerta de auditoría.

    Español: Estructura básica para reglas de auditoría.
    English: Basic structure for audit rules.
    """

    rule: str
    severity: str
    message: str
    department: Optional[str] = None


@dataclass
class MetricsBundle:
    """Métricas agregadas para el tablero.

    Español: Almacena datos de métricas y alertas para exportación.
    English: Stores metrics and alerts for export.
    """

    national: ParsedResult
    departments: List[ParsedResult]
    turnout_df: pd.DataFrame
    consistency_df: pd.DataFrame
    benford_results: Dict[str, BenfordResult]
    null_turnout_df: pd.DataFrame
    correlation_df: pd.DataFrame
    alerts: List[AuditAlert]


def _extract_timestamp(payload: Mapping[str, Any]) -> Optional[datetime]:
    """Extrae timestamp desde un JSON CNE.

    Español: Busca claves comunes de fecha/hora y devuelve datetime.
    English: Looks for common timestamp keys and returns datetime.
    """

    for key in ("timestamp", "fecha", "fecha_corte", "updated_at", "ultima_actualizacion"):
        if key in payload:
            try:
                return datetime.fromisoformat(str(payload[key]))
            except ValueError:
                continue
    return None


def _coerce_int(value: Any) -> int:
    """Convierte un valor a entero de forma segura.

    Español: Retorna 0 si no puede convertir.
    English: Returns 0 if conversion fails.
    """

    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def parse_cne_payload(payload: Mapping[str, Any], department: str) -> ParsedResult:
    """Normaliza un JSON del CNE.

    Español: Intenta mapear diferentes estructuras a un formato uniforme.
    English: Attempts to map multiple structures into a uniform format.
    """

    candidates_raw = (
        payload.get("candidatos")
        or payload.get("candidates")
        or payload.get("resultados", {}).get("candidatos")
        or payload.get("results", {}).get("candidates")
        or []
    )
    rows = []
    for cand in candidates_raw:
        name = cand.get("nombre") or cand.get("name") or cand.get("candidato") or "Sin nombre"
        votes = cand.get("votos") or cand.get("votes") or cand.get("total") or 0
        rows.append({"candidato": name, "votos": _coerce_int(votes)})

    candidates_df = pd.DataFrame(rows)
    if candidates_df.empty:
        candidates_df = pd.DataFrame(columns=["candidato", "votos"])

    totals = payload.get("totales") or payload.get("totals") or {}
    total_valid = _coerce_int(
        payload.get("votos_validos")
        or totals.get("validos")
        or totals.get("valid_votes")
        or candidates_df["votos"].sum()
    )
    null_votes = _coerce_int(payload.get("nulos") or totals.get("nulos") or totals.get("null"))
    invalid_votes = _coerce_int(
        payload.get("invalidos") or totals.get("invalidos") or totals.get("invalid")
    )
    registered = _coerce_int(
        payload.get("registrados")
        or payload.get("electores")
        or totals.get("registrados")
        or totals.get("registered")
    )

    return ParsedResult(
        department=department,
        candidates=candidates_df,
        total_valid=total_valid,
        null_votes=null_votes,
        invalid_votes=invalid_votes,
        registered=registered,
        timestamp=_extract_timestamp(payload),
    )


def _load_json_from_path(path: Path) -> Mapping[str, Any]:
    """Carga un JSON desde ruta local.

    Español: Retorna diccionario o lanza excepción si falla.
    English: Returns dict or raises on failure.
    """

    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _load_json_from_url(url: str) -> Mapping[str, Any]:
    """Carga un JSON desde URL.

    Español: Usa pandas para tolerancia básica a errores de conexión.
    English: Uses pandas for basic connection tolerance.
    """

    return pd.read_json(url, typ="series").to_dict()


def load_payload(source: str, location: str) -> Tuple[Optional[Mapping[str, Any]], Optional[str]]:
    """Carga un JSON desde URL o carpeta local.

    Español: Devuelve payload y mensaje de error (si existe).
    English: Returns payload and error message (if any).
    """

    try:
        if source == "url":
            return _load_json_from_url(location), None
        return _load_json_from_path(Path(location)), None
    except Exception as exc:  # noqa: BLE001 - requiere robustez al cargar datos externos.
        return None, str(exc)


def build_locations(source: str, base: str) -> Dict[str, str]:
    """Construye rutas/URLs para los 19 archivos.

    Español: Incluye 18 departamentos más el total nacional.
    English: Includes 18 departments plus national total.
    """

    locations = {}
    if source == "url":
        base = base.rstrip("/")
        for dept, slug in DEPARTMENT_SLUGS.items():
            locations[dept] = f"{base}/{slug}.json"
        locations["Nacional"] = f"{base}/nacional.json"
    else:
        base_path = Path(base)
        for dept, slug in DEPARTMENT_SLUGS.items():
            locations[dept] = str(base_path / f"{slug}.json")
        locations["Nacional"] = str(base_path / "nacional.json")
    return locations


def compute_turnout(parsed: ParsedResult) -> float:
    """Calcula el turnout.

    Español: turnout = (valid + nulos + inválidos) / registrados.
    English: turnout = (valid + null + invalid) / registered.
    """

    total_votes = parsed.total_valid + parsed.null_votes + parsed.invalid_votes
    if parsed.registered == 0:
        return 0.0
    return total_votes / parsed.registered


def build_metrics(national: ParsedResult, departments: List[ParsedResult]) -> MetricsBundle:
    """Construye métricas principales y reglas de auditoría.

    Español: Calcula turnout, consistencia, Benford, correlaciones y alertas.
    English: Calculates turnout, consistency, Benford, correlations, and alerts.
    """

    alerts: List[AuditAlert] = []

    turnout_rows = []
    for dept in departments:
        turnout = compute_turnout(dept)
        turnout_rows.append(
            {
                "departamento": dept.department,
                "turnout": turnout,
                "nulos": dept.null_votes,
                "invalidos": dept.invalid_votes,
                "registrados": dept.registered,
            }
        )
    turnout_df = pd.DataFrame(turnout_rows)

    if not turnout_df.empty:
        turnout_df["zscore"] = stats.zscore(turnout_df["turnout"], nan_policy="omit")
        for _, row in turnout_df.iterrows():
            if row["turnout"] < 0.30 or row["turnout"] > 0.95 or abs(row["zscore"]) > 2.58:
                alerts.append(
                    AuditAlert(
                        rule="Turnout",
                        severity="alta",
                        message=(
                            f"Turnout anómalo ({row['turnout']:.1%}, z={row['zscore']:.2f})."
                        ),
                        department=row["departamento"],
                    )
                )
            null_rate = (row["nulos"] + row["invalidos"]) / max(row["registrados"], 1)
            if null_rate > 0.10:
                alerts.append(
                    AuditAlert(
                        rule="Nulos/Inválidos",
                        severity="media",
                        message=f"% Nulos/Inválidos alto ({null_rate:.1%}).",
                        department=row["departamento"],
                    )
                )

    consistency_df = build_consistency(national, departments)
    for _, row in consistency_df.iterrows():
        if row["diferencia"] != 0:
            alerts.append(
                AuditAlert(
                    rule="Consistencia agregada",
                    severity="alta",
                    message="Suma departamental difiere de nacional.",
                    department=row["candidato"],
                )
            )

    benford_results = build_benford(departments)
    for candidato, result in benford_results.items():
        if result.p_value == result.p_value and result.p_value < 0.05:
            alerts.append(
                AuditAlert(
                    rule="Ley de Benford",
                    severity="media",
                    message=f"Distribución Benford anómala (p={result.p_value:.3f}).",
                    department=candidato,
                )
            )

    null_turnout_df = build_null_turnout(turnout_df)
    if not null_turnout_df.empty:
        for _, row in null_turnout_df.iterrows():
            if row["outlier"]:
                alerts.append(
                    AuditAlert(
                        rule="Outliers nulos-turnout",
                        severity="media",
                        message="Residuo > 2σ en regresión nulos vs turnout.",
                        department=row["departamento"],
                    )
                )

    correlation_df = build_correlations(departments)
    if not correlation_df.empty:
        low_corr = correlation_df.stack()
        for (dept_a, dept_b), value in low_corr.items():
            if dept_a == dept_b:
                continue
            if value < 0.5:
                alerts.append(
                    AuditAlert(
                        rule="Correlación",
                        severity="baja" if value > 0 else "media",
                        message=f"Correlación baja/negativa ({value:.2f}) entre {dept_a} y {dept_b}.",
                        department=dept_a,
                    )
                )
                break

    return MetricsBundle(
        national=national,
        departments=departments,
        turnout_df=turnout_df,
        consistency_df=consistency_df,
        benford_results=benford_results,
        null_turnout_df=null_turnout_df,
        correlation_df=correlation_df,
        alerts=alerts,
    )


def build_consistency(national: ParsedResult, departments: List[ParsedResult]) -> pd.DataFrame:
    """Compara suma departamental vs nacional.

    Español: Calcula diferencias por candidato y total.
    English: Computes differences per candidate and total.
    """

    dept_votes = pd.concat(
        [dept.candidates.assign(departamento=dept.department) for dept in departments],
        ignore_index=True,
    )
    if dept_votes.empty:
        return pd.DataFrame(columns=["candidato", "departamental", "nacional", "diferencia"])
    dept_sum = dept_votes.groupby("candidato")["votos"].sum()
    nat_sum = national.candidates.set_index("candidato")["votos"]
    combined = pd.concat([dept_sum, nat_sum], axis=1).fillna(0)
    combined.columns = ["departamental", "nacional"]
    combined["diferencia"] = combined["departamental"] - combined["nacional"]
    combined = combined.reset_index().rename(columns={"index": "candidato"})
    return combined


def build_benford(departments: List[ParsedResult]) -> Dict[str, BenfordResult]:
    """Construye resultados Benford por candidato.

    Español: Agrupa votos departamentales por candidato.
    English: Groups department votes per candidate.
    """

    votes_by_candidate: Dict[str, List[int]] = {}
    for dept in departments:
        for _, row in dept.candidates.iterrows():
            votes_by_candidate.setdefault(row["candidato"], []).append(int(row["votos"]))

    return {candidate: evaluate_benford(votes) for candidate, votes in votes_by_candidate.items()}


def build_null_turnout(turnout_df: pd.DataFrame) -> pd.DataFrame:
    """Analiza nulos vs turnout con regresión lineal.

    Español: Retorna dataframe con residuales y outliers.
    English: Returns dataframe with residuals and outliers.
    """

    if turnout_df.empty:
        return pd.DataFrame()
    df = turnout_df.copy()
    df["null_rate"] = (df["nulos"] + df["invalidos"]) / df["registrados"].replace(0, np.nan)
    df = df.dropna(subset=["null_rate", "turnout"])
    if df.empty:
        return df
    x = sm.add_constant(df["turnout"])
    model = sm.OLS(df["null_rate"], x).fit()
    df["resid"] = model.resid
    sigma = df["resid"].std() if df["resid"].std() else 0
    df["outlier"] = df["resid"].abs() > 2 * sigma if sigma else False
    return df


def build_correlations(departments: List[ParsedResult]) -> pd.DataFrame:
    """Calcula correlación entre departamentos.

    Español: Usa porcentajes por candidato para comparar departamentos.
    English: Uses candidate shares to compare departments.
    """

    frames = []
    for dept in departments:
        total = dept.candidates["votos"].sum()
        if total == 0:
            continue
        share = dept.candidates.copy()
        share["share"] = share["votos"] / total
        share = share.set_index("candidato")["share"]
        frames.append(share.rename(dept.department))
    if not frames:
        return pd.DataFrame()
    data = pd.concat(frames, axis=1).fillna(0)
    return data.corr()


def build_export_bundle(metrics: MetricsBundle) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Genera tablas para exportar.

    Español: Crea dataframes para métricas y alertas.
    English: Creates dataframes for metrics and alerts.
    """

    metrics_df = metrics.consistency_df.copy()
    alerts_df = pd.DataFrame([alert.__dict__ for alert in metrics.alerts])
    return metrics_df, alerts_df
