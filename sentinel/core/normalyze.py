import json
from typing import Dict, Any, List
from sentinel.core.models import Meta, Totals, CandidateResult, Snapshot


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


def normalize_snapshot(
    raw: Dict[str, Any],
    department_name: str,
    timestamp_utc: str,
    year: int = 2025,
) -> Snapshot:
    """
    Convierte un JSON crudo del CNE en un Snapshot canónico e inmutable.
    """

    department_code = DEPARTMENT_CODES[department_name]

    meta = Meta(
        election="HN-PRESIDENTIAL",
        year=year,
        source="CNE",
        scope="DEPARTMENT",
        department_code=department_code,
        timestamp_utc=timestamp_utc,
    )

    totals = Totals(
        registered_voters=int(raw.get("registered_voters", 0)),
        total_votes=int(raw.get("total_votes", 0)),
        valid_votes=int(raw.get("valid_votes", 0)),
        null_votes=int(raw.get("null_votes", 0)),
        blank_votes=int(raw.get("blank_votes", 0)),
    )

    raw_candidates = raw.get("candidates", {})
    candidates: List[CandidateResult] = []

    for slot in range(1, 8):
        votes = int(raw_candidates.get(str(slot), 0))
        candidates.append(CandidateResult(slot=slot, votes=votes))

    return Snapshot(
        meta=meta,
        totals=totals,
        candidates=candidates,
    )


def snapshot_to_canonical_json(snapshot: Snapshot) -> str:
    """
    Serializa un Snapshot a JSON canónico (orden fijo, sin espacios).
    """

    payload = {
        "meta": snapshot.meta.__dict__,
        "totals": snapshot.totals.__dict__,
        "candidates": [c.__dict__ for c in snapshot.candidates],
    }

    return json.dumps(payload, sort_keys=True, separators=(",", ":"))
