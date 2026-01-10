from sentinel.core.normalyze import normalize_snapshot, snapshot_to_canonical_json


def test_normalization_is_deterministic():
    raw = {
        "total_votes": 100,
        "valid_votes": 95,
        "null_votes": 3,
        "blank_votes": 2,
        "candidates": {
            "1": 40,
            "2": 30,
            "3": 25,
        },
    }

    snap1 = normalize_snapshot(raw, "Francisco Morazán", "2025-12-03T17:00:00Z")
    snap2 = normalize_snapshot(raw, "Francisco Morazán", "2025-12-03T17:00:00Z")

    json1 = snapshot_to_canonical_json(snap1)
    json2 = snapshot_to_canonical_json(snap2)

    assert json1 == json2


def test_normalization_parses_nested_totals_and_candidates():
    raw = {
        "meta": {
            "totals": {
                "padron": "1,200",
                "votos_emitidos": "1,000",
                "votos_validos": "950",
                "votos_nulos": "30",
                "votos_blancos": "20",
            }
        },
        "resultados": {
            "candidatos": [
                {
                    "posicion": 1,
                    "votos": "600",
                    "candidato": "Alice",
                    "partido": "Partido A",
                },
                {
                    "posicion": 2,
                    "votos": "350",
                    "candidato": "Bob",
                    "partido": "Partido B",
                },
            ]
        },
    }
    field_map = {
        "totals": {
            "registered_voters": ["meta.totals.padron"],
            "total_votes": ["meta.totals.votos_emitidos"],
            "valid_votes": ["meta.totals.votos_validos"],
            "null_votes": ["meta.totals.votos_nulos"],
            "blank_votes": ["meta.totals.votos_blancos"],
        },
        "candidate_roots": ["resultados"],
    }

    snapshot = normalize_snapshot(
        raw,
        "Atlántida",
        "2025-12-03T17:00:00Z",
        field_map=field_map,
    )

    assert snapshot.totals.registered_voters == 1200
    assert snapshot.totals.total_votes == 1000
    assert snapshot.candidates[0].name == "Alice"
    assert snapshot.candidates[1].votes == 350
