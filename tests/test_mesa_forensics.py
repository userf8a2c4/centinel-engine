"""
======================== ESPAÑOL ========================
Pruebas de la forensia por mesa/acta (cierre del gap de escrutinio
especial). Vectores:
  - índice y huella por mesa (estructura real anidada del CNE);
  - reconciliación entre fases (mesa alterada post-publicación);
  - imposibilidad aritmética por mesa individual;
  - aparición tardía / lote grande con escrutinio casi cerrado;
  - degradación con gracia ante payload solo-agregado.

======================== ENGLISH ========================
Per-table forensics tests covering indexing/fingerprint, cross-phase
reconciliation, per-table impossibility, late appearance, and graceful
degradation on aggregate-only payloads.
"""

from __future__ import annotations

import copy

import pytest

from centinel.core.mesa_forensics import (
    candidate_delta,
    index_mesas,
    mesa_candidate_votes,
    mesa_fingerprint,
    primary_beneficiary,
)
from centinel.core.rules import (
    late_mesa_rule,
    mesa_impossibility_rule,
    mesa_reconciliation_rule,
)
from centinel.core.rules.common import collect_all_mesas


@pytest.fixture()
def cne_payload() -> dict:
    """Payload realista del CNE: nacional -> departamentos -> mesas."""
    return {
        "timestamp": "2026-01-07T08:30:00Z",
        "source": "TEST-CNE",
        "actas_escrutadas": 3,
        "actas_total": 4,
        "porcentaje_escrutado": 75.0,
        "departamentos": [
            {
                "nombre": "Cortés",
                "mesas": [
                    {
                        "codigo_mesa": "CO-N01",
                        "votos_validos": 200,
                        "votos_nulos": 5,
                        "votos_blancos": 3,
                        "total_votes": 208,
                        "inscritos": 300,
                        "candidatos": {"A": 120, "B": 80},
                    },
                    {
                        "codigo_mesa": "CO-N02",
                        "votos_validos": 190,
                        "votos_nulos": 4,
                        "votos_blancos": 2,
                        "total_votes": 196,
                        "inscritos": 300,
                        "candidatos": {"A": 100, "B": 90},
                    },
                ],
            },
            {
                "nombre": "Olancho",
                "mesas": [
                    {
                        "codigo_mesa": "OL-N01",
                        "votos_validos": 150,
                        "votos_nulos": 3,
                        "votos_blancos": 1,
                        "total_votes": 154,
                        "inscritos": 250,
                        "candidatos": {"A": 70, "B": 80},
                    }
                ],
            },
        ],
    }


def test_collect_all_mesas_traverses_departments(cne_payload):
    """Recolecta mesas anidadas en departamentos (causa raíz del gap)."""
    mesas = collect_all_mesas(cne_payload)
    assert len(mesas) == 3
    codes = {m.get("codigo_mesa") for m in mesas}
    assert codes == {"CO-N01", "CO-N02", "OL-N01"}
    # El departamento de origen queda anotado para trazabilidad.
    co = next(m for m in mesas if m["codigo_mesa"] == "CO-N01")
    assert co["_departamento"] == "Cortés"


def test_index_and_fingerprint_stable(cne_payload):
    """La huella es determinista y excluye claves internas."""
    idx = index_mesas(cne_payload)
    assert set(idx) == {"CO-N01", "CO-N02", "OL-N01"}
    assert idx["CO-N01"]["candidate_votes"] == {"A": 120, "B": 80}
    assert idx["CO-N01"]["departamento"] == "Cortés"
    # Re-indexar el mismo payload da la misma huella.
    assert index_mesas(cne_payload)["CO-N01"]["fingerprint"] == idx["CO-N01"]["fingerprint"]
    # `_departamento` no debe alterar la huella.
    bare = {"codigo_mesa": "X", "candidatos": {"A": 1}}
    assert mesa_fingerprint(bare) == mesa_fingerprint({**bare, "_departamento": "Z"})


def test_mesa_candidate_votes_handles_dict_and_list():
    """Vota tanto con `candidatos` dict como lista."""
    assert mesa_candidate_votes({"candidatos": {"A": 10, "B": 5}}) == {"A": 10, "B": 5}
    listed = mesa_candidate_votes(
        {"candidatos": [{"nombre": "A", "votos": 7}, {"nombre": "B", "votos": 3}]}
    )
    assert listed.get("A") == 7 and listed.get("B") == 3


def test_candidate_delta_and_beneficiary():
    delta = candidate_delta({"A": 100, "B": 100}, {"A": 600, "B": 90})
    assert delta == {"A": 500, "B": -10}
    assert primary_beneficiary(delta) == "A"
    assert primary_beneficiary({"A": -5}) is None


def test_reconciliation_flags_altered_mesa(cne_payload):
    """Mesa ya publicada que cambia de valor -> CRITICAL con delta."""
    altered = copy.deepcopy(cne_payload)
    altered["departamentos"][0]["mesas"][0]["candidatos"]["A"] += 500

    alerts = mesa_reconciliation_rule.apply(altered, cne_payload, {})
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert["severity"] == "CRITICAL"
    detalle = alert["value"]["detalle"][0]
    assert detalle["codigo_mesa"] == "CO-N01"
    assert detalle["delta_por_candidato"] == {"A": 500}
    assert detalle["beneficiado"] == "A"


def test_reconciliation_silent_without_changes(cne_payload):
    assert mesa_reconciliation_rule.apply(cne_payload, cne_payload, {}) == []


def test_reconciliation_silent_without_previous(cne_payload):
    assert mesa_reconciliation_rule.apply(cne_payload, None, {}) == []


def test_impossibility_detects_turnout_over_registered(cne_payload):
    """Votos > inscritos en una mesa individual -> CRITICAL."""
    bad = copy.deepcopy(cne_payload)
    bad["departamentos"][0]["mesas"][0]["total_votes"] = 9999

    alerts = mesa_impossibility_rule.apply(bad, None, {})
    assert len(alerts) == 1
    assert alerts[0]["severity"] == "CRITICAL"
    motivos = alerts[0]["value"]["detalle"][0]["motivos"]
    assert any("inscritos" in m for m in motivos)


def test_impossibility_detects_candidate_sum_over_valid(cne_payload):
    bad = copy.deepcopy(cne_payload)
    bad["departamentos"][0]["mesas"][0]["candidatos"]["A"] = 100000

    alerts = mesa_impossibility_rule.apply(bad, None, {})
    motivos = alerts[0]["value"]["detalle"][0]["motivos"]
    assert any("suma candidatos" in m for m in motivos)


def test_impossibility_silent_on_clean_payload(cne_payload):
    assert mesa_impossibility_rule.apply(cne_payload, None, {}) == []


def test_late_mesa_flags_large_batch_near_close(cne_payload):
    """Lote grande de mesas nuevas con escrutinio casi cerrado -> CRITICAL."""
    previous = copy.deepcopy(cne_payload)
    previous["porcentaje_escrutado"] = 95.0
    # Previo: solo CO-N01. Actual: + muchas mesas nuevas.
    previous["departamentos"] = [
        {"nombre": "Cortés", "mesas": [previous["departamentos"][0]["mesas"][0]]}
    ]
    current = copy.deepcopy(cne_payload)
    current["porcentaje_escrutado"] = 99.0
    big = [{"codigo_mesa": f"LT-{i:03d}", "candidatos": {"A": 200, "B": 5}} for i in range(60)]
    current["departamentos"] = [
        {"nombre": "Cortés", "mesas": [current["departamentos"][0]["mesas"][0]] + big}
    ]

    alerts = late_mesa_rule.apply(current, previous, {})
    assert len(alerts) == 1
    assert alerts[0]["severity"] == "CRITICAL"
    assert alerts[0]["value"]["mesas_nuevas"] >= 60


def test_late_mesa_silent_when_no_new_tables(cne_payload):
    assert late_mesa_rule.apply(cne_payload, cne_payload, {}) == []


def test_all_rules_degrade_on_aggregate_only_payload():
    """Payload solo-agregado (sin mesas) -> ninguna regla emite ni rompe."""
    aggregate = {
        "timestamp": "2026-01-07T08:30:00Z",
        "actas_escrutadas": 1450,
        "actas_total": 1600,
        "total_votos": 1054320,
        "candidatos": {"A": 600000, "B": 454320},
    }
    assert index_mesas(aggregate) == {}
    assert mesa_reconciliation_rule.apply(aggregate, aggregate, {}) == []
    assert mesa_impossibility_rule.apply(aggregate, None, {}) == []
    assert late_mesa_rule.apply(aggregate, aggregate, {}) == []
