"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `src/centinel/core/rules/common.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - safe_int
  - safe_int_or_none
  - safe_float_or_none
  - extract_department
  - parse_timestamp
  - extract_candidates
  - extract_candidate_votes
  - extract_total_votes
  - extract_vote_breakdown
  - extract_actas_mesas_counts
  - extract_porcentaje_escrutado
  - extract_registered_voters
  - extract_mesas
  - extract_mesa_code
  - extract_mesa_candidate_votes
  - ...

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `src/centinel/core/rules/common.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - safe_int
  - safe_int_or_none
  - safe_float_or_none
  - extract_department
  - parse_timestamp
  - extract_candidates
  - extract_candidate_votes
  - extract_total_votes
  - extract_vote_breakdown
  - extract_actas_mesas_counts
  - extract_porcentaje_escrutado
  - extract_registered_voters
  - extract_mesas
  - extract_mesa_code
  - extract_mesa_candidate_votes
  - ...

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
"""

# Common Module
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



from __future__ import annotations

from typing import Dict, Iterable, List, Optional

from dateutil import parser


def safe_int(value: object, default: int = 0) -> int:
    """Convierte a entero con fallback seguro. (Convert to integer with a safe fallback.)"""
    try:
        if value is None:
            return default
        return int(str(value).replace(",", "").split(".")[0])
    except (ValueError, TypeError):
        return default


def safe_int_or_none(value: object) -> Optional[int]:
    """Convierte a entero o devuelve None si no es posible. (Convert to integer or return None if not possible.)"""
    try:
        if value is None:
            return None
        return int(str(value).replace(",", "").split(".")[0])
    except (ValueError, TypeError):
        return None


def safe_float_or_none(value: object) -> Optional[float]:
    """Convierte a float o devuelve None si no es posible. (Convert to float or return None if not possible.)"""
    try:
        if value is None:
            return None
        return float(str(value).replace(",", "."))
    except (ValueError, TypeError):
        return None


def extract_department(data: dict) -> str:
    """Extrae el departamento o retorna un valor por defecto. (Extract the department or return a default value.)"""
    meta = data.get("meta") or data.get("metadata") or {}
    return data.get("departamento") or data.get("dep") or data.get("department") or meta.get("department") or "NACIONAL"


def parse_timestamp(data: dict) -> Optional[object]:
    """Parsea un timestamp desde varias claves conocidas. (Parse a timestamp from known keys.)"""
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
    """Extrae la lista de candidatos desde variantes de clave. (Extract the candidate list from key variants.)"""
    if isinstance(data.get("candidates"), list):
        return data.get("candidates", [])
    if isinstance(data.get("candidatos"), list):
        return data.get("candidatos", [])
    if isinstance(data.get("votos"), list):
        return data.get("votos", [])
    return []


def extract_candidate_votes(data: dict) -> Dict[str, Dict[str, object]]:
    """Construye un mapa de votos por candidato. (Build a candidate vote map.)"""
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
        candidate_name = entry.get("name") or entry.get("nombre") or entry.get("candidato")
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
    """Extrae el total de votos desde claves conocidas. (Extract total votes from known keys.)"""
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
    """Extrae el desglose de votos válidos/nulos/blancos. (Extract the breakdown of valid/null/blank votes.)"""
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
    """Extrae conteos de actas y mesas. (Extract tally sheet and table counts.)"""
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
            mesas.get("totales") or mesas.get("total") or data.get("mesas_totales") or data.get("mesas_total")
        ),
        "mesas_procesadas": safe_int_or_none(
            mesas.get("procesadas") or mesas.get("divulgadas") or data.get("mesas_procesadas")
        ),
    }


def extract_porcentaje_escrutado(data: dict) -> Optional[float]:
    """Extrae el porcentaje de escrutinio cuando existe. (Extract the scrutiny percentage when available.)"""
    porcentaje = data.get("porcentaje_escrutado") or data.get("porcentaje") or data.get("porcentaje_escrutinio")
    if porcentaje is None:
        meta = data.get("meta") or data.get("metadata") or {}
        porcentaje = meta.get("porcentaje_escrutado") or meta.get("porcentaje")
    return safe_float_or_none(porcentaje)


def extract_registered_voters(data: dict) -> Optional[int]:
    """Extrae el total de electores registrados. (Extract the total registered voters.)"""
    totals = data.get("totals") or {}
    return safe_int_or_none(
        totals.get("registered_voters")
        or totals.get("inscritos")
        or data.get("registered_voters")
        or data.get("inscritos")
        or data.get("padron")
        or data.get("padron_electoral")
    )


def extract_mesas(data: dict) -> List[dict]:
    """Extrae la lista de mesas desde llaves conocidas. (Extract the list of polling tables from known keys.)"""
    mesas = data.get("mesas") or data.get("tables") or data.get("actas") or []
    if isinstance(mesas, dict):
        return [mesa for mesa in mesas.values() if isinstance(mesa, dict)]
    if isinstance(mesas, list):
        return [mesa for mesa in mesas if isinstance(mesa, dict)]
    return []


def extract_mesa_code(mesa: dict) -> Optional[str]:
    """Extrae el código de mesa desde campos conocidos. (Extract the table code from known fields.)"""
    code = mesa.get("codigo") or mesa.get("codigo_mesa") or mesa.get("mesa_id") or mesa.get("id") or mesa.get("code")
    return str(code) if code is not None else None


def extract_mesa_candidate_votes(mesa: dict) -> Dict[str, int]:
    """Extrae votos por candidato desde una mesa. (Extract candidate votes from a table entry.)"""
    candidates = extract_candidate_votes(mesa)
    return {
        key: int(candidate.get("votes") or 0)
        for key, candidate in candidates.items()
        if candidate.get("votes") is not None
    }


def extract_mesa_vote_breakdown(mesa: dict) -> Dict[str, Optional[int]]:
    """Extrae desglose de votos desde una mesa. (Extract vote breakdown from a table entry.)"""
    totals = mesa.get("totals") or {}
    return {
        "valid_votes": safe_int_or_none(
            totals.get("valid_votes") or totals.get("validos") or mesa.get("votos_validos")
        ),
        "blank_votes": safe_int_or_none(
            totals.get("blank_votes") or totals.get("blancos") or mesa.get("votos_blancos")
        ),
        "null_votes": safe_int_or_none(totals.get("null_votes") or totals.get("nulos") or mesa.get("votos_nulos")),
        "total_votes": safe_int_or_none(
            totals.get("total_votes") or totals.get("total") or mesa.get("total_votes") or mesa.get("votos_emitidos")
        ),
        "registered_voters": safe_int_or_none(
            totals.get("registered_voters")
            or totals.get("inscritos")
            or mesa.get("registered_voters")
            or mesa.get("padron")
        ),
    }


def extract_department_entries(data: dict) -> List[dict]:
    """Extrae entradas por departamento desde claves conocidas. (Extract department-level entries from known keys.)"""
    for key in ("departments", "departamentos", "by_department", "por_departamento"):
        entries = data.get(key)
        if isinstance(entries, list):
            return [entry for entry in entries if isinstance(entry, dict)]
        if isinstance(entries, dict):
            return [{"department": dept, **payload} for dept, payload in entries.items() if isinstance(payload, dict)]
    return []


def extract_numeric_list(values: Iterable[object]) -> List[int]:
    """Convierte una colección a una lista de enteros válidos. (Convert a collection to a list of valid integers.)"""
    numbers: List[int] = []
    for value in values:
        number = safe_int_or_none(value)
        if number is None:
            continue
        numbers.append(number)
    return numbers
