from __future__ import annotations

from typing import Dict, List, Optional

from dateutil import parser


def safe_int(value: object, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(str(value).replace(",", "").split(".")[0])
    except (ValueError, TypeError):
        return default


def safe_int_or_none(value: object) -> Optional[int]:
    try:
        if value is None:
            return None
        return int(str(value).replace(",", "").split(".")[0])
    except (ValueError, TypeError):
        return None


def safe_float_or_none(value: object) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(str(value).replace(",", "."))
    except (ValueError, TypeError):
        return None


def extract_department(data: dict) -> str:
    meta = data.get("meta") or data.get("metadata") or {}
    return (
        data.get("departamento")
        or data.get("dep")
        or data.get("department")
        or meta.get("department")
        or "NACIONAL"
    )


def parse_timestamp(data: dict) -> Optional[object]:
    raw_ts = data.get("timestamp") or data.get("timestamp_utc") or data.get("fecha")
    meta = data.get("meta") or data.get("metadata") or {}
    raw_ts = raw_ts or meta.get("timestamp_utc")
    if not raw_ts:
        return None
    try:
        return parser.parse(raw_ts)
    except (ValueError, TypeError):
        return None


def extract_candidates(data: dict) -> List[dict]:
    if isinstance(data.get("candidates"), list):
        return data.get("candidates", [])
    if isinstance(data.get("candidatos"), list):
        return data.get("candidatos", [])
    if isinstance(data.get("votos"), list):
        return data.get("votos", [])
    return []


def extract_candidate_votes(data: dict) -> Dict[str, Dict[str, object]]:
    candidates = {}

    if isinstance(data.get("resultados"), dict):
        for key, value in data.get("resultados", {}).items():
            votes = safe_int_or_none(value)
            if votes is None:
                continue
            candidates[str(key)] = {
                "id": str(key),
                "name": str(key),
                "votes": votes,
            }
        return candidates

    for entry in extract_candidates(data):
        if not isinstance(entry, dict):
            continue
        candidate_id = (
            entry.get("candidate_id")
            or entry.get("id")
            or entry.get("nombre")
            or entry.get("name")
            or entry.get("candidato")
        )
        candidate_name = (
            entry.get("name") or entry.get("nombre") or entry.get("candidato")
        )
        votes = safe_int_or_none(entry.get("votes") or entry.get("votos"))
        if votes is None:
            continue
        key = str(candidate_id or candidate_name or "unknown")
        candidates[key] = {
            "id": candidate_id or key,
            "name": candidate_name or key,
            "votes": votes,
        }
    return candidates


def extract_total_votes(data: dict) -> Optional[int]:
    totals = data.get("totals") or {}
    votos_totales = data.get("votos_totales") or {}
    return safe_int_or_none(
        totals.get("total_votes")
        or totals.get("total")
        or data.get("total_votos")
        or data.get("total_votes")
        or votos_totales.get("total")
        or votos_totales.get("total_votes")
        or data.get("votos_emitidos")
    )


def extract_vote_breakdown(data: dict) -> Dict[str, Optional[int]]:
    totals = data.get("totals") or {}
    votos_totales = data.get("votos_totales") or {}
    return {
        "valid_votes": safe_int_or_none(
            totals.get("valid_votes")
            or totals.get("validos")
            or votos_totales.get("validos")
            or votos_totales.get("valid_votes")
            or data.get("votos_validos")
        ),
        "blank_votes": safe_int_or_none(
            totals.get("blank_votes")
            or totals.get("blancos")
            or votos_totales.get("blancos")
            or votos_totales.get("blank_votes")
            or data.get("votos_blancos")
        ),
        "null_votes": safe_int_or_none(
            totals.get("null_votes")
            or totals.get("nulos")
            or votos_totales.get("nulos")
            or votos_totales.get("null_votes")
            or data.get("votos_nulos")
        ),
        "total_votes": extract_total_votes(data),
    }


def extract_actas_mesas_counts(data: dict) -> Dict[str, Optional[int]]:
    actas = data.get("actas") or {}
    mesas = data.get("mesas") or {}
    totals = data.get("totals") or {}
    return {
        "actas_totales": safe_int_or_none(
            actas.get("totales")
            or actas.get("total")
            or data.get("actas_totales")
            or totals.get("actas_totales")
            or totals.get("actas_total")
        ),
        "actas_procesadas": safe_int_or_none(
            actas.get("divulgadas")
            or actas.get("procesadas")
            or actas.get("correctas")
            or data.get("actas_procesadas")
            or totals.get("actas_procesadas")
            or totals.get("actas")
        ),
        "mesas_totales": safe_int_or_none(
            mesas.get("totales")
            or mesas.get("total")
            or data.get("mesas_totales")
            or data.get("mesas_total")
        ),
        "mesas_procesadas": safe_int_or_none(
            mesas.get("procesadas")
            or mesas.get("divulgadas")
            or data.get("mesas_procesadas")
        ),
    }


def extract_porcentaje_escrutado(data: dict) -> Optional[float]:
    porcentaje = (
        data.get("porcentaje_escrutado")
        or data.get("porcentaje")
        or data.get("porcentaje_escrutinio")
    )
    if porcentaje is None:
        meta = data.get("meta") or data.get("metadata") or {}
        porcentaje = meta.get("porcentaje_escrutado") or meta.get("porcentaje")
    return safe_float_or_none(porcentaje)


def extract_registered_voters(data: dict) -> Optional[int]:
    totals = data.get("totals") or {}
    return safe_int_or_none(
        totals.get("registered_voters")
        or totals.get("inscritos")
        or data.get("registered_voters")
        or data.get("inscritos")
        or data.get("padron")
        or data.get("padron_electoral")
    )
