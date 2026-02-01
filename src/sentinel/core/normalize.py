"""Normaliza datos crudos del CNE y genera snapshots canónicos.

English:
    Normalizes raw CNE data and builds canonical snapshots.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Dict, Any, List, Iterable, Optional

from pydantic import BaseModel, Field, ValidationError, validator

from sentinel.core.models import Meta, Totals, CandidateResult, Snapshot

logger = logging.getLogger(__name__)

DEPARTMENT_CODES = {
    "Atlántida": "01",
    "Choluteca": "02",
    "Colón": "03",
    "Comayagua": "04",
    "Copán": "05",
    "Cortés": "06",
    "El Paraíso": "07",
    "Francisco Morazán": "08",
    "Gracias a Dios": "09",
    "Intibucá": "10",
    "Islas de la Bahía": "11",
    "La Paz": "12",
    "Lempira": "13",
    "Ocotepeque": "14",
    "Olancho": "15",
    "Santa Bárbara": "16",
    "Valle": "17",
    "Yoro": "18",
}


class CNEResult(BaseModel):
    """Función segura para validar resultados / Secure function for validating results."""

    partido: str = Field(..., min_length=1)
    votos: str

    @validator("votos")
    def _validate_votes(cls, value: str) -> str:  # noqa: N805
        normalized = str(value).replace(",", "").replace(".", "")
        if not normalized.isdigit():
            raise ValueError("votos must be numeric")
        return str(value)

    class Config:
        extra = "forbid"


class CNEPayload(BaseModel):
    """Función segura para validar payloads CNE / Secure function for validating CNE payloads."""

    cargo: str = Field(..., min_length=1)
    departamento: str = Field(..., min_length=1)
    resultados: List[CNEResult]

    @validator("cargo")
    def _validate_cargo(cls, value: str) -> str:  # noqa: N805
        if value.lower() != "presidencial":
            raise ValueError("cargo must be presidencial")
        return value

    class Config:
        extra = "forbid"


def _hash_payload(payload: Dict[str, Any]) -> str:
    """Función segura para hashear payloads / Secure function for hashing payloads."""
    serialized = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _validate_cne_payload(raw: Dict[str, Any]) -> bool:
    """Función segura para validar estructura CNE / Secure function for validating CNE structure."""
    try:
        CNEPayload.parse_obj(raw)
    except ValidationError as exc:
        # Seguridad: Evita exposición de datos sensibles / Security: Avoid exposure of sensitive data.
        logger.error(
            "invalid_cne_payload hash=%s errors=%s",
            _hash_payload(raw),
            exc.errors(),
        )
        return False
    return True


def _safe_int(value: Any) -> int:
    """Convierte valores heterogéneos a entero de forma segura.

    Acepta cadenas con separadores y devuelve 0 cuando el valor no es válido.

    English:
        Safely convert heterogeneous values to integers.

        Accepts strings with separators and returns 0 when the value is invalid.
    """
    try:
        if value is None:
            return 0
        return int(str(value).replace(",", "").split(".")[0])
    except (ValueError, TypeError):
        return 0


def _get_nested_value(payload: Dict[str, Any], path: str) -> Any:
    """Obtiene un valor anidado usando una ruta con puntos.

    Recorre claves del diccionario separadas por "." y retorna None si la ruta
    no existe.

    English:
        Get a nested value using a dot-delimited path.

        Traverses dictionary keys separated by "." and returns None if the path
        is missing.
    """
    current: Any = payload
    for part in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _first_value(payload: Dict[str, Any], keys: Iterable[str]) -> Any:
    """Devuelve el primer valor no nulo entre varias claves.

    Soporta claves simples y rutas anidadas en formato dotted-path.

    English:
        Return the first non-null value among multiple keys.

        Supports simple keys and dotted-path nested lookups.
    """
    for key in keys:
        if "." in key:
            value = _get_nested_value(payload, key)
        else:
            value = payload.get(key)
        if value is not None:
            return value
    return None


def _extract_candidates_root(
    raw: Dict[str, Any], candidate_roots: Iterable[str]
) -> Any:
    """Localiza el contenedor de candidatos dentro del JSON crudo.

    Busca en múltiples rutas posibles y normaliza cuando el contenedor incluye
    una clave "candidatos".

    English:
        Locate the candidate container within the raw JSON.

        Searches multiple possible roots and normalizes when the container
        includes a "candidatos" key.
    """
    for key in candidate_roots:
        value = _get_nested_value(raw, key) if "." in key else raw.get(key)
        if isinstance(value, dict) and "candidatos" in value:
            return value["candidatos"]
        if isinstance(value, (list, dict)):
            return value
    return None


def _iter_candidates(
    raw: Dict[str, Any],
    candidate_count: int,
    candidate_roots: Iterable[str],
) -> Iterable[CandidateResult]:
    """Itera candidatos en varias estructuras con fallback robusto.

    Genera objetos `CandidateResult` desde listas, diccionarios o valores
    simples, y rellena con votos cero cuando falten datos.

    English:
        Iterate candidates across multiple structures with robust fallbacks.

        Builds `CandidateResult` objects from lists, dicts, or scalar values and
        fills missing candidates with zero votes.
    """
    raw_candidates = _extract_candidates_root(raw, candidate_roots)

    if isinstance(raw_candidates, list):
        for idx, item in enumerate(raw_candidates, start=1):
            yield CandidateResult(
                slot=_safe_int(item.get("posicion") or item.get("orden") or idx),
                votes=_safe_int(item.get("votos") or item.get("votes")),
                candidate_id=(
                    str(item.get("id")) if item.get("id") is not None else None
                ),
                name=item.get("candidato") or item.get("nombre") or item.get("name"),
                party=item.get("partido") or item.get("party"),
            )
        return

    if isinstance(raw_candidates, dict):
        for idx in range(1, candidate_count + 1):
            key = str(idx)
            value = raw_candidates.get(key)
            if isinstance(value, dict):
                yield CandidateResult(
                    slot=idx,
                    votes=_safe_int(value.get("votos") or value.get("votes")),
                    candidate_id=(
                        str(value.get("id")) if value.get("id") is not None else None
                    ),
                    name=value.get("candidato")
                    or value.get("nombre")
                    or value.get("name"),
                    party=value.get("partido") or value.get("party"),
                )
            else:
                yield CandidateResult(slot=idx, votes=_safe_int(value))
        return

    for idx in range(1, candidate_count + 1):
        yield CandidateResult(slot=idx, votes=0)


def normalize_snapshot(
    raw: Dict[str, Any],
    department_name: str,
    timestamp_utc: str,
    year: int = 2025,
    candidate_count: int = 10,
    scope: str = "DEPARTMENT",
    department_code: str | None = None,
    field_map: Dict[str, List[str]] | None = None,
) -> Optional[Snapshot]:
    """Convierte un JSON crudo del CNE en un Snapshot canónico e inmutable.

    Args:
        raw (Dict[str, Any]): JSON crudo del CNE.
        department_name (str): Nombre del departamento.
        timestamp_utc (str): Timestamp en UTC.
        year (int): Año electoral.
        candidate_count (int): Cantidad esperada de candidatos.
        scope (str): Alcance del snapshot (p. ej., DEPARTMENT).
        department_code (str | None): Código de departamento, si se conoce.
        field_map (Dict[str, List[str]] | None): Mapeos opcionales de campos.

    Returns:
        Snapshot | None: Snapshot canónico con metadatos o None si es inválido.

    English:
        Converts raw CNE JSON into an immutable canonical Snapshot.

    Args:
        raw (Dict[str, Any]): Raw CNE JSON data.
        department_name (str): Department name.
        timestamp_utc (str): UTC timestamp.
        year (int): Election year.
        candidate_count (int): Expected number of candidates.
        scope (str): Snapshot scope (e.g., DEPARTMENT).
        department_code (str | None): Department code, if known.
        field_map (Dict[str, List[str]] | None): Optional field mappings.

    Returns:
        Snapshot | None: Canonical snapshot with metadata or None if invalid.
    """

    if not _validate_cne_payload(raw):
        logger.error(
            "skip_invalid_snapshot department=%s timestamp=%s",
            department_name,
            timestamp_utc,
        )
        return None

    resolved_department_code = department_code or DEPARTMENT_CODES.get(
        department_name, "00"
    )

    meta = Meta(
        election="HN-PRESIDENTIAL",
        year=year,
        source="CNE",
        scope=scope,
        department_code=resolved_department_code,
        timestamp_utc=timestamp_utc,
    )

    field_map = field_map or {}
    totals_map = field_map.get("totals", {})
    candidate_roots = field_map.get(
        "candidate_roots", ["candidatos", "candidates", "resultados", "partidos"]
    )

    registered_voters = _safe_int(
        _first_value(
            raw,
            totals_map.get(
                "registered_voters", ["registered_voters", "inscritos", "padron"]
            ),
        )
    )
    total_votes = _safe_int(
        _first_value(
            raw,
            totals_map.get(
                "total_votes", ["total_votes", "total_votos", "votos_emitidos"]
            ),
        )
    )
    valid_votes = _safe_int(
        _first_value(
            raw,
            totals_map.get("valid_votes", ["valid_votes", "votos_validos", "validos"]),
        )
    )
    null_votes = _safe_int(
        _first_value(
            raw, totals_map.get("null_votes", ["null_votes", "votos_nulos", "nulos"])
        )
    )
    blank_votes = _safe_int(
        _first_value(
            raw,
            totals_map.get("blank_votes", ["blank_votes", "votos_blancos", "blancos"]),
        )
    )

    if total_votes == 0 and any([valid_votes, null_votes, blank_votes]):
        total_votes = valid_votes + null_votes + blank_votes

    totals = Totals(
        registered_voters=registered_voters,
        total_votes=total_votes,
        valid_votes=valid_votes,
        null_votes=null_votes,
        blank_votes=blank_votes,
    )

    raw_candidates = _extract_candidates_root(raw, candidate_roots)
    if isinstance(raw_candidates, list):
        candidate_count = max(candidate_count, len(raw_candidates))
    candidates: List[CandidateResult] = list(
        _iter_candidates(raw, candidate_count, candidate_roots)
    )

    return Snapshot(
        meta=meta,
        totals=totals,
        candidates=candidates,
    )


def snapshot_to_canonical_json(snapshot: Snapshot) -> str:
    """Serializa un Snapshot a JSON canónico (orden fijo, sin espacios).

    Args:
        snapshot (Snapshot): Snapshot a serializar.

    Returns:
        str: JSON canónico del snapshot.

    English:
        Serializes a Snapshot into canonical JSON (stable order, no spaces).

    Args:
        snapshot (Snapshot): Snapshot to serialize.

    Returns:
        str: Canonical JSON string.
    """

    payload = {
        "meta": snapshot.meta.__dict__,
        "totals": snapshot.totals.__dict__,
        "candidates": [c.__dict__ for c in snapshot.candidates],
    }

    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def snapshot_to_dict(snapshot: Snapshot) -> Dict[str, Any]:
    """Convierte un Snapshot en un diccionario simple.

    Args:
        snapshot (Snapshot): Snapshot a convertir.

    Returns:
        Dict[str, Any]: Representación del snapshot en dict.

    English:
        Converts a Snapshot into a plain dictionary.

    Args:
        snapshot (Snapshot): Snapshot to convert.

    Returns:
        Dict[str, Any]: Dictionary representation of the snapshot.
    """
    return {
        "meta": snapshot.meta.__dict__,
        "totals": snapshot.totals.__dict__,
        "candidates": [c.__dict__ for c in snapshot.candidates],
    }
