"""
======================== ESPAÑOL ========================
Archivo: `src/centinel/core/rules/mesa_impossibility_rule.py`.

Centinel audita el JSON publicado por el CNE, no actas. Esta regla
aplica chequeos de coherencia interna a cada registro del JSON por
separado:

  - votos emitidos/total > inscritos declarados en ese registro;
  - suma de votos por candidato > votos válidos del registro;
  - válidos + nulos + blancos != total declarado.

Un registro internamente imposible que no mueve el agregado nacional
es hoy invisible para los detectores agregados (Benford/Z-score).
Esta regla lo hace visible. Cada chequeo se omite si faltan los
campos necesarios (no genera falsos positivos por datos ausentes).

======================== ENGLISH ========================
Per-record internal-consistency rule over the CNE-published JSON
(not tally sheets): turnout > registered, candidate sum > valid,
valid+null+blank != total. Each check is skipped when its inputs are
absent (no false positives from missing data).
"""

from __future__ import annotations

from typing import List, Optional

from centinel.core.mesa_forensics import mesa_candidate_votes
from centinel.core.rules.common import (
    collect_all_mesas,
    extract_mesa_code,
    extract_mesa_vote_breakdown,
    safe_int_or_none,
)
from centinel.core.rules.registry import rule


@rule(
    name="Imposibilidad Aritmética por Registro del JSON",
    severity="CRITICAL",
    description="Chequeos de coherencia interna aplicados a cada registro del JSON publicado.",
    config_key="mesa_impossibility",
)
def apply(current_data: dict, previous_data: Optional[dict], config: dict) -> List[dict]:
    """Aplica chequeos de imposibilidad por mesa.

    English:
        Apply per-table impossibility checks to the current snapshot.
    """
    del previous_data
    max_listed = int((config or {}).get("max_listed", 25))

    violations: List[dict] = []
    for mesa in collect_all_mesas(current_data):
        code = extract_mesa_code(mesa)
        if not code:
            continue
        breakdown = extract_mesa_vote_breakdown(mesa)
        candidate_votes = mesa_candidate_votes(mesa)

        valid = breakdown.get("valid_votes")
        null_v = breakdown.get("null_votes")
        blank = breakdown.get("blank_votes")
        total = breakdown.get("total_votes")
        # `extract_mesa_vote_breakdown` no lee `inscritos`/`padron` a nivel
        # de registro (donde el JSON del CNE los coloca). Se compensa aquí
        # sin tocar el helper compartido para no arriesgar regresiones.
        registered = breakdown.get("registered_voters")
        if registered is None:
            registered = safe_int_or_none(mesa.get("inscritos") or mesa.get("padron"))
        reasons: List[str] = []

        if registered is not None and registered >= 0:
            emitted = total if total is not None else valid
            if emitted is not None and emitted > registered:
                reasons.append(f"votos ({emitted}) > inscritos ({registered})")

        if valid is not None and candidate_votes:
            cand_sum = sum(candidate_votes.values())
            if cand_sum > valid:
                reasons.append(f"suma candidatos ({cand_sum}) > votos válidos ({valid})")

        if valid is not None and null_v is not None and blank is not None and total is not None:
            if valid + null_v + blank != total:
                reasons.append(
                    f"válidos+nulos+blancos ({valid + null_v + blank}) != total ({total})"
                )

        if reasons:
            violations.append(
                {
                    "codigo_mesa": code,
                    "departamento": str(mesa.get("_departamento") or ""),
                    "motivos": reasons,
                }
            )

    if not violations:
        return []

    message = f"{len(violations)} registro(s) del JSON aritméticamente imposibles."
    return [
        {
            "type": "Registro del JSON Aritméticamente Imposible",
            "severity": "CRITICAL",
            "message": message,
            "value": {
                "mesas_imposibles": len(violations),
                "detalle": violations[:max_listed],
            },
            "threshold": {"mesas_imposibles": 0},
            "result": (
                "CRITICAL",
                message,
                {"mesas_imposibles": len(violations)},
                {"mesas_imposibles": 0},
            ),
            "justification": (
                "Centinel audita el JSON publicado, no actas. Un registro del "
                "JSON cuyos números se contradicen aritméticamente a sí mismos "
                "es una incoherencia interna del dato publicado —hecho "
                "verificable, no juicio electoral—. El escrutinio agregado "
                "oculta estos registros si no mueven el total nacional; el "
                "chequeo por registro los expone individualmente."
            ),
        }
    ]
