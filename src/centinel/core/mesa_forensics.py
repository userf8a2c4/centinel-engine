"""
======================== ESPAÑOL ========================
Archivo: `src/centinel/core/mesa_forensics.py`.

Forensia por mesa/acta. Provee funciones puras para:
  - Calcular una huella criptográfica determinista por mesa
    (`mesa_fingerprint`), sobre el sub-objeto canónico de esa mesa.
  - Construir un índice forense por código de mesa (`index_mesas`)
    con huella, votos por candidato y desglose.

El sellado a nivel de snapshot completo ya existe en el pipeline de
captura. Este módulo añade granularidad: permite probar que una mesa
específica no cambió entre fases (preliminar -> escrutinio especial)
sin revelar el resto del padrón. No modifica la captura ni el hash
encadenado del snapshot; es una capa de análisis additiva.

======================== ENGLISH ========================
Per-table (acta) forensics. Pure helpers to compute a deterministic
cryptographic fingerprint per table and to build a per-table index
(fingerprint + candidate votes + breakdown). Additive analysis layer;
does not alter snapshot capture or the snapshot hash chain.
"""

from __future__ import annotations

import hashlib
import json
from typing import Dict, Optional

from centinel.core.rules.common import (
    collect_all_mesas,
    extract_mesa_candidate_votes,
    extract_mesa_code,
    extract_mesa_vote_breakdown,
    safe_int_or_none,
)


def mesa_candidate_votes(mesa: dict) -> Dict[str, int]:
    """Votos por candidato robustos para la estructura real del CNE.

    El payload del CNE entrega `candidatos` como dict nombre->int por
    mesa; el helper compartido `extract_mesa_candidate_votes` solo
    entiende listas o la clave `resultados`. Este extractor cubre el
    dict directo y delega en el helper compartido para el resto, sin
    modificar código común (evita regresiones).

    English:
        Robust per-table candidate votes. Handles the CNE's `candidatos`
        dict (name->int); falls back to the shared helper otherwise.
    """
    candidatos = mesa.get("candidatos") or mesa.get("candidates")
    if isinstance(candidatos, dict):
        votes: Dict[str, int] = {}
        for name, value in candidatos.items():
            parsed = safe_int_or_none(value)
            if parsed is not None:
                votes[str(name)] = parsed
        if votes:
            return votes
    return extract_mesa_candidate_votes(mesa)


def _canonical(mesa: dict) -> bytes:
    """Serializa una mesa de forma canónica y estable.

    Se excluyen claves internas (prefijo `_`, p. ej. `_departamento`)
    para que la huella dependa solo de datos publicados por el CNE.
    Orden de claves determinista y separadores fijos.

    English:
        Canonical, stable serialization. Internal keys (leading `_`)
        are excluded so the fingerprint depends only on CNE-published
        data. Deterministic key order, fixed separators.
    """
    cleaned = {k: v for k, v in mesa.items() if not str(k).startswith("_")}
    return json.dumps(cleaned, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )


def mesa_fingerprint(mesa: dict) -> str:
    """SHA-256 hex del sub-objeto canónico de la mesa.

    English:
        SHA-256 hex digest of the table's canonical sub-object.
    """
    return hashlib.sha256(_canonical(mesa)).hexdigest()


def index_mesas(data: dict) -> Dict[str, dict]:
    """Indexa todas las mesas por código.

    Devuelve `{codigo_mesa: {fingerprint, departamento, candidate_votes,
    breakdown}}`. Degrada con gracia a `{}` si el payload solo trae
    agregados (sin mesas). Mesas sin código se omiten (no se pueden
    reconciliar de forma fiable entre fases).

    English:
        Index every table by code. Gracefully returns `{}` when the
        payload only carries aggregates. Tables without a code are
        skipped (cannot be reconciled reliably across phases).
    """
    index: Dict[str, dict] = {}
    for mesa in collect_all_mesas(data):
        code = extract_mesa_code(mesa)
        if not code:
            continue
        index[code] = {
            "fingerprint": mesa_fingerprint(mesa),
            "departamento": str(mesa.get("_departamento") or ""),
            "candidate_votes": mesa_candidate_votes(mesa),
            "breakdown": extract_mesa_vote_breakdown(mesa),
        }
    return index


def candidate_delta(
    previous_votes: Dict[str, int], current_votes: Dict[str, int]
) -> Dict[str, int]:
    """Delta de votos por candidato entre dos estados de una mesa.

    English:
        Per-candidate vote delta between two states of a table.
    """
    keys = set(previous_votes) | set(current_votes)
    delta: Dict[str, int] = {}
    for key in keys:
        diff = int(current_votes.get(key, 0)) - int(previous_votes.get(key, 0))
        if diff != 0:
            delta[key] = diff
    return delta


def primary_beneficiary(delta: Dict[str, int]) -> Optional[str]:
    """Candidato con mayor ganancia neta en un delta (o None).

    English:
        Candidate with the largest net gain in a delta (or None).
    """
    gains = {k: v for k, v in delta.items() if v > 0}
    if not gains:
        return None
    return max(gains, key=gains.get)
