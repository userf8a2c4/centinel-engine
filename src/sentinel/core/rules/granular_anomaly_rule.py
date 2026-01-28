"""Regla granular de anomalías para deltas, Benford y outliers.

Granular anomaly rule for deltas, Benford, and outliers.
"""

from __future__ import annotations

from typing import Iterable, List, Optional

import numpy as np
import pandas as pd
from scipy.stats import chisquare

from sentinel.core.rules.common import (
    extract_actas_mesas_counts,
    extract_candidate_votes,
    extract_department,
    extract_department_entries,
    extract_mesa_candidate_votes,
    extract_mesa_vote_breakdown,
    extract_mesas,
    extract_registered_voters,
    extract_total_votes,
    parse_timestamp,
)
from sentinel.core.rules.registry import rule


def _extract_level(data: dict) -> Optional[str]:
    metadata = data.get("metadata") or data.get("meta") or {}
    return (
        data.get("election_level")
        or data.get("nivel")
        or data.get("level")
        or data.get("tipo")
        or metadata.get("election_level")
    )


def _extract_department_from_payload(data: dict) -> str:
    geography = data.get("geography") or {}
    return (
        data.get("department")
        or data.get("departamento")
        or data.get("dep")
        or geography.get("department")
        or geography.get("departamento")
        or extract_department(data)
    )


def _candidate_rows(snapshot: dict) -> List[dict]:
    rows: List[dict] = []
    timestamp = parse_timestamp(snapshot)
    base_department = _extract_department_from_payload(snapshot)
    base_level = _extract_level(snapshot)
    department_entries = extract_department_entries(snapshot)

    entries = department_entries or [snapshot]
    for entry in entries:
        department = _extract_department_from_payload(entry) or base_department
        level = _extract_level(entry) or base_level
        for candidate_id, candidate in extract_candidate_votes(entry).items():
            votes = candidate.get("votes")
            if votes is None:
                continue
            rows.append(
                {
                    "department": department,
                    "election_level": level,
                    "candidate_id": str(candidate_id),
                    "candidate_name": candidate.get("name") or str(candidate_id),
                    "votes": int(votes),
                    "timestamp": timestamp,
                }
            )
    return rows


def _totals_rows(snapshot: dict) -> List[dict]:
    rows: List[dict] = []
    timestamp = parse_timestamp(snapshot)
    base_department = _extract_department_from_payload(snapshot)
    base_level = _extract_level(snapshot)
    department_entries = extract_department_entries(snapshot)

    entries = department_entries or [snapshot]
    for entry in entries:
        department = _extract_department_from_payload(entry) or base_department
        level = _extract_level(entry) or base_level
        totals = extract_total_votes(entry)
        registered = extract_registered_voters(entry)
        actas_mesas = extract_actas_mesas_counts(entry)
        rows.append(
            {
                "department": department,
                "election_level": level,
                "total_votes": totals,
                "registered_voters": registered,
                "actas_procesadas": actas_mesas.get("actas_procesadas"),
                "mesas_procesadas": actas_mesas.get("mesas_procesadas"),
                "timestamp": timestamp,
            }
        )
    return rows


def _mesa_rows(snapshot: dict) -> List[dict]:
    rows: List[dict] = []
    timestamp = parse_timestamp(snapshot)
    base_department = _extract_department_from_payload(snapshot)
    base_level = _extract_level(snapshot)
    for mesa in extract_mesas(snapshot):
        department = _extract_department_from_payload(mesa) or base_department
        level = _extract_level(mesa) or base_level
        breakdown = extract_mesa_vote_breakdown(mesa)
        rows.append(
            {
                "department": department,
                "election_level": level,
                "registered_voters": breakdown.get("registered_voters"),
                "total_votes": breakdown.get("total_votes"),
                "timestamp": timestamp,
                "mesa": mesa,
            }
        )
        for candidate_id, votes in extract_mesa_candidate_votes(mesa).items():
            rows.append(
                {
                    "department": department,
                    "election_level": level,
                    "candidate_id": str(candidate_id),
                    "votes": int(votes),
                    "timestamp": timestamp,
                    "mesa": mesa,
                }
            )
    return rows


def _first_digit(values: Iterable[int]) -> List[int]:
    digits: List[int] = []
    for value in values:
        if value is None:
            continue
        value = abs(int(value))
        if value == 0:
            continue
        digits.append(int(str(value)[0]))
    return digits


def _compute_zscores(series: pd.Series) -> pd.Series:
    if series.empty:
        return series
    mean = series.mean()
    std = series.std(ddof=0)
    if std == 0 or pd.isna(std):
        return pd.Series([0.0] * len(series), index=series.index)
    return (series - mean) / std


@rule(
    name="Anomalías Granulares",
    severity="CRITICAL",
    description="Detecta deltas negativos, Benford por subgrupo, z-score y reversión.",
    config_key="granular_anomaly",
)
def apply(
    current_data: dict, previous_data: Optional[dict], config: dict
) -> List[dict]:
    """
    Detecta anomalías granulares con deltas negativos, cambios bruscos y Benford.

    Esta regla compara snapshots consecutivos para encontrar votos restados,
    cambios porcentuales extremos en ventanas cortas, outliers por z-score
    entre departamentos/niveles, inconsistencias de participación en mesas
    grandes y desviaciones de Benford por subgrupos (departamento+nivel+candidato).

    Args:
        current_data: Snapshot JSON actual del CNE.
        previous_data: Snapshot JSON anterior (None en el primer snapshot).
        config: Configuración específica de la regla.

    Returns:
        Lista de alertas en formato estándar.

    English:
        Detects granular anomalies with negative deltas, abrupt changes and Benford.

        This rule compares consecutive snapshots to detect vote rollbacks,
        extreme percentage changes in short windows, z-score outliers across
        departments/levels, participation inconsistencies in large tables, and
        Benford deviations by subgroup (department+level+candidate).

    Args:
        current_data: Current CNE JSON snapshot.
        previous_data: Previous JSON snapshot (None for the first snapshot).
        config: Rule-specific configuration section.

    Returns:
        List of alerts in the standard format.
    """
    alerts: List[dict] = []
    current_ts = parse_timestamp(current_data)
    previous_ts = parse_timestamp(previous_data) if previous_data else None

    negative_threshold = int(config.get("negative_delta_threshold", 0))
    delta_pct_alert = float(config.get("delta_pct_alert", 3.0))
    delta_pct_window = int(config.get("delta_pct_time_window_minutes", 30))
    z_threshold = float(config.get("zscore_threshold", 3.0))
    z_min_abs = int(config.get("zscore_min_abs_delta", 100))
    z_min_groups = int(config.get("zscore_min_departments", 5))
    benford_p_threshold = float(config.get("benford_pvalue_threshold", 0.05))
    benford_min_samples = int(config.get("benford_min_samples", 50))
    benford_min_vote = int(config.get("benford_min_vote", 10))
    turnout_min_pct = float(config.get("turnout_min_pct", 0.0))
    turnout_max_pct = float(config.get("turnout_max_pct", 100.0))
    mesa_min_registered = int(config.get("mesa_min_registered", 300))
    mesa_min_turnout_pct = float(config.get("mesa_min_turnout_pct", 2.0))
    mesa_max_turnout_pct = float(config.get("mesa_max_turnout_pct", 100.0))
    reversal_lead_margin = int(config.get("reversal_min_lead_margin", 500))
    reversal_window = int(config.get("reversal_time_window_minutes", 30))
    reversal_min_negative = int(config.get("reversal_min_negative_delta", 100))
    actas_negative_delta = int(config.get("actas_negative_delta_threshold", -1))
    mesas_negative_delta = int(config.get("mesas_negative_delta_threshold", -1))

    candidate_rows = _candidate_rows(current_data)
    totals_rows = _totals_rows(current_data)
    mesa_rows = _mesa_rows(current_data)

    candidate_df = pd.DataFrame(candidate_rows)
    totals_df = pd.DataFrame(totals_rows)
    mesa_df = pd.DataFrame(mesa_rows)

    if previous_data:
        previous_candidate_df = pd.DataFrame(_candidate_rows(previous_data))
        if not candidate_df.empty and not previous_candidate_df.empty:
            merged = candidate_df.merge(
                previous_candidate_df,
                on=["department", "election_level", "candidate_id"],
                suffixes=("_current", "_previous"),
            )
            merged["delta_abs"] = merged["votes_current"] - merged["votes_previous"]
            merged["delta_pct"] = merged.apply(
                lambda row: (
                    (row["delta_abs"] / row["votes_previous"]) * 100
                    if row["votes_previous"] > 0
                    else None
                ),
                axis=1,
            )
            negative_rows = merged[merged["delta_abs"] < negative_threshold]
            for _, row in negative_rows.iterrows():
                alerts.append(
                    {
                        "type": "Delta Negativo por Candidato",
                        "severity": "CRITICAL",
                        "department": row["department"],
                        "election_level": row["election_level"],
                        "candidate": row["candidate_name_current"],
                        "timestamp": current_ts.isoformat() if current_ts else None,
                        "previous_value": int(row["votes_previous"]),
                        "current_value": int(row["votes_current"]),
                        "delta_abs": int(row["delta_abs"]),
                        "delta_pct": row["delta_pct"],
                        "justification": (
                            "Se detectó reducción de votos entre snapshots. "
                            f"candidato={row['candidate_name_current']}, "
                            f"anterior={row['votes_previous']}, actual={row['votes_current']}, "
                            f"delta={row['delta_abs']}."
                        ),
                    }
                )

            if current_ts and previous_ts:
                minutes = (current_ts - previous_ts).total_seconds() / 60
                if minutes <= delta_pct_window:
                    change_rows = merged[
                        merged["delta_pct"].abs() >= delta_pct_alert
                    ]
                    for _, row in change_rows.iterrows():
                        alerts.append(
                            {
                                "type": "Cambio Porcentual Brusco",
                                "severity": "High",
                                "department": row["department"],
                                "election_level": row["election_level"],
                                "candidate": row["candidate_name_current"],
                                "timestamp": current_ts.isoformat()
                                if current_ts
                                else None,
                                "previous_value": int(row["votes_previous"]),
                                "current_value": int(row["votes_current"]),
                                "delta_abs": int(row["delta_abs"]),
                                "delta_pct": row["delta_pct"],
                                "justification": (
                                    "Cambio porcentual elevado en ventana corta. "
                                    f"delta_pct={row['delta_pct']:.2f}%, "
                                    f"ventana_minutos={minutes:.1f}, "
                                    f"umbral={delta_pct_alert:.2f}%."
                                ),
                            }
                        )

        previous_totals_df = pd.DataFrame(_totals_rows(previous_data))
        if not totals_df.empty and not previous_totals_df.empty:
            totals_merged = totals_df.merge(
                previous_totals_df,
                on=["department", "election_level"],
                suffixes=("_current", "_previous"),
            )
            totals_merged["delta_abs"] = (
                totals_merged["total_votes_current"].fillna(0)
                - totals_merged["total_votes_previous"].fillna(0)
            )
            totals_merged["delta_pct"] = totals_merged.apply(
                lambda row: (
                    (row["delta_abs"] / row["total_votes_previous"]) * 100
                    if row["total_votes_previous"] and row["total_votes_previous"] > 0
                    else None
                ),
                axis=1,
            )
            if current_ts and previous_ts:
                minutes = (current_ts - previous_ts).total_seconds() / 60
                if minutes <= delta_pct_window:
                    jump_rows = totals_merged[
                        totals_merged["delta_pct"].abs() >= delta_pct_alert
                    ]
                    for _, row in jump_rows.iterrows():
                        alerts.append(
                            {
                                "type": "Salto Percentual por Departamento",
                                "severity": "High",
                                "department": row["department"],
                                "election_level": row["election_level"],
                                "timestamp": current_ts.isoformat()
                                if current_ts
                                else None,
                                "previous_value": int(row["total_votes_previous"] or 0),
                                "current_value": int(row["total_votes_current"] or 0),
                                "delta_abs": int(row["delta_abs"]),
                                "delta_pct": row["delta_pct"],
                                "justification": (
                                    "Cambio porcentual abrupto en total de votos. "
                                    f"delta_pct={row['delta_pct']:.2f}%, "
                                    f"ventana_minutos={minutes:.1f}, "
                                    f"umbral={delta_pct_alert:.2f}%."
                                ),
                            }
                        )

            zscore_candidates = totals_merged.copy()
            zscore_candidates = zscore_candidates.dropna(
                subset=["total_votes_current", "total_votes_previous"]
            )
            if not zscore_candidates.empty:
                zscore_candidates["delta_abs"] = (
                    zscore_candidates["total_votes_current"]
                    - zscore_candidates["total_votes_previous"]
                )
                zscore_candidates = zscore_candidates.groupby("election_level").apply(
                    lambda group: group.assign(
                        zscore=_compute_zscores(group["delta_abs"])
                    )
                    if len(group) >= z_min_groups
                    else group.assign(zscore=0.0)
                )
                zscore_candidates = zscore_candidates.reset_index(drop=True)
                z_outliers = zscore_candidates[
                    (zscore_candidates["delta_abs"].abs() >= z_min_abs)
                    & (zscore_candidates["zscore"].abs() >= z_threshold)
                ]
                for _, row in z_outliers.iterrows():
                    alerts.append(
                        {
                            "type": "Outlier Z-Score",
                            "severity": "High",
                            "department": row["department"],
                            "election_level": row["election_level"],
                            "timestamp": current_ts.isoformat()
                            if current_ts
                            else None,
                            "previous_value": int(row["total_votes_previous"] or 0),
                            "current_value": int(row["total_votes_current"] or 0),
                            "delta_abs": int(row["delta_abs"]),
                            "delta_pct": row["delta_pct"],
                            "justification": (
                                "El delta de votos es un outlier estadístico. "
                                f"z_score={row['zscore']:.2f}, "
                                f"delta_abs={row['delta_abs']}."
                            ),
                        }
                    )

            for _, row in totals_merged.iterrows():
                actas_prev = row.get("actas_procesadas_previous")
                actas_curr = row.get("actas_procesadas_current")
                mesas_prev = row.get("mesas_procesadas_previous")
                mesas_curr = row.get("mesas_procesadas_current")
                if (
                    actas_prev is not None
                    and actas_curr is not None
                    and (actas_curr - actas_prev) <= actas_negative_delta
                ):
                    alerts.append(
                        {
                            "type": "Actas Procesadas en Retroceso",
                            "severity": "High",
                            "department": row["department"],
                            "election_level": row["election_level"],
                            "timestamp": current_ts.isoformat()
                            if current_ts
                            else None,
                            "previous_value": int(actas_prev),
                            "current_value": int(actas_curr),
                            "delta_abs": int(actas_curr - actas_prev),
                            "delta_pct": None,
                            "justification": (
                                "Las actas procesadas disminuyeron entre snapshots. "
                                f"previas={actas_prev}, actuales={actas_curr}."
                            ),
                        }
                    )
                if (
                    mesas_prev is not None
                    and mesas_curr is not None
                    and (mesas_curr - mesas_prev) <= mesas_negative_delta
                ):
                    alerts.append(
                        {
                            "type": "Mesas Procesadas en Retroceso",
                            "severity": "High",
                            "department": row["department"],
                            "election_level": row["election_level"],
                            "timestamp": current_ts.isoformat()
                            if current_ts
                            else None,
                            "previous_value": int(mesas_prev),
                            "current_value": int(mesas_curr),
                            "delta_abs": int(mesas_curr - mesas_prev),
                            "delta_pct": None,
                            "justification": (
                                "Las mesas procesadas disminuyeron entre snapshots. "
                                f"previas={mesas_prev}, actuales={mesas_curr}."
                            ),
                        }
                    )

        if not candidate_df.empty and not previous_candidate_df.empty:
            current_grouped = candidate_df.groupby(
                ["department", "election_level"]
            )
            previous_grouped = previous_candidate_df.groupby(
                ["department", "election_level"]
            )
            for group_key, current_group in current_grouped:
                if group_key not in previous_grouped.groups:
                    continue
                prev_group = previous_grouped.get_group(group_key)
                current_sorted = current_group.sort_values(
                    "votes", ascending=False
                ).reset_index(drop=True)
                prev_sorted = prev_group.sort_values(
                    "votes", ascending=False
                ).reset_index(drop=True)
                if len(current_sorted) < 2 or len(prev_sorted) < 2:
                    continue
                prev_leader = prev_sorted.iloc[0]
                prev_runner = prev_sorted.iloc[1]
                curr_leader = current_sorted.iloc[0]
                prev_lead_margin = int(prev_leader["votes"] - prev_runner["votes"])
                current_votes_by_candidate = current_group.set_index(
                    "candidate_id"
                )["votes"].to_dict()
                prev_votes_by_candidate = prev_group.set_index("candidate_id")[
                    "votes"
                ].to_dict()
                prev_leader_current_votes = current_votes_by_candidate.get(
                    prev_leader["candidate_id"], 0
                )
                prev_leader_delta = (
                    prev_leader_current_votes - prev_leader["votes"]
                )
                if (
                    prev_leader["candidate_id"] != curr_leader["candidate_id"]
                    and prev_lead_margin >= reversal_lead_margin
                    and prev_leader_delta <= -reversal_min_negative
                ):
                    if current_ts and previous_ts:
                        minutes = (current_ts - previous_ts).total_seconds() / 60
                        if minutes > reversal_window:
                            continue
                    alerts.append(
                        {
                            "type": "Reversión de Liderazgo",
                            "severity": "High",
                            "department": group_key[0],
                            "election_level": group_key[1],
                            "candidate": prev_leader["candidate_name"],
                            "timestamp": current_ts.isoformat()
                            if current_ts
                            else None,
                            "previous_value": int(prev_leader["votes"]),
                            "current_value": int(prev_leader_current_votes),
                            "delta_abs": int(prev_leader_delta),
                            "delta_pct": (
                                (prev_leader_delta / prev_leader["votes"]) * 100
                                if prev_leader["votes"] > 0
                                else None
                            ),
                            "justification": (
                                "Cambio brusco en liderazgo con pérdida de votos. "
                                f"lider_prev={prev_leader['candidate_name']}, "
                                f"margen_prev={prev_lead_margin}, "
                                f"delta_lider={prev_leader_delta}."
                            ),
                        }
                    )

    if not totals_df.empty:
        for _, row in totals_df.iterrows():
            total_votes = row.get("total_votes")
            registered = row.get("registered_voters")
            if total_votes is None or not registered:
                continue
            turnout = total_votes / registered
            if turnout > (turnout_max_pct / 100) or turnout < (turnout_min_pct / 100):
                alerts.append(
                    {
                        "type": "Participación Fuera de Rango",
                        "severity": "High",
                        "department": row["department"],
                        "election_level": row["election_level"],
                        "timestamp": current_ts.isoformat()
                        if current_ts
                        else None,
                        "previous_value": None,
                        "current_value": int(total_votes),
                        "delta_abs": None,
                        "delta_pct": turnout * 100,
                        "justification": (
                            "Participación fuera de rango lógico. "
                            f"turnout={turnout:.2%}, inscritos={registered}."
                        ),
                    }
                )

    if not mesa_df.empty:
        mesa_totals = mesa_df[
            mesa_df["registered_voters"].notna()
            & mesa_df["total_votes"].notna()
        ]
        for _, row in mesa_totals.iterrows():
            registered = int(row["registered_voters"])
            total_votes = int(row["total_votes"])
            if registered < mesa_min_registered or registered == 0:
                continue
            turnout = total_votes / registered
            if turnout < (mesa_min_turnout_pct / 100) or turnout > (
                mesa_max_turnout_pct / 100
            ):
                alerts.append(
                    {
                        "type": "Turnout Anómalo en Mesa Grande",
                        "severity": "High",
                        "department": row["department"],
                        "election_level": row["election_level"],
                        "timestamp": current_ts.isoformat()
                        if current_ts
                        else None,
                        "previous_value": None,
                        "current_value": total_votes,
                        "delta_abs": None,
                        "delta_pct": turnout * 100,
                        "justification": (
                            "Participación anómala en mesa grande. "
                            f"turnout={turnout:.2%}, inscritos={registered}."
                        ),
                    }
                )

        benford_rows = mesa_df[
            mesa_df["candidate_id"].notna() & mesa_df["votes"].notna()
        ]
        if not benford_rows.empty:
            benford_rows = benford_rows[benford_rows["votes"] >= benford_min_vote]
            for group_key, group in benford_rows.groupby(
                ["department", "election_level", "candidate_id"]
            ):
                digits = _first_digit(group["votes"].tolist())
                if len(digits) < benford_min_samples:
                    continue
                counts = pd.Series(digits).value_counts().reindex(range(1, 10), fill_value=0)
                expected = [
                    len(digits) * np.log10(1 + 1 / digit) for digit in range(1, 10)
                ]
                chi_result = chisquare(counts.values, f_exp=expected)
                if chi_result.pvalue < benford_p_threshold:
                    alerts.append(
                        {
                            "type": "Benford por Subgrupo",
                            "severity": "High",
                            "department": group_key[0],
                            "election_level": group_key[1],
                            "candidate": str(group_key[2]),
                            "timestamp": current_ts.isoformat()
                            if current_ts
                            else None,
                            "previous_value": None,
                            "current_value": None,
                            "delta_abs": None,
                            "delta_pct": None,
                            "justification": (
                                "Desviación de Benford en subgrupo. "
                                f"p_value={chi_result.pvalue:.4f}, "
                                f"muestras={len(digits)}."
                            ),
                        }
                    )

    return alerts
