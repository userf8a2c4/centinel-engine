"""Regla para detectar cambios irreversibles en liderazgos electorales.

Rule to detect irreversible changes in electoral leads.
"""

from __future__ import annotations

import os
import sqlite3
from typing import Dict, List, Optional, Tuple

from sentinel.core.rules.common import (
    extract_candidate_votes,
    extract_department,
    extract_registered_voters,
    extract_total_votes,
    parse_timestamp,
)


def _ensure_db(path: str) -> None:
    """Crea el archivo SQLite y la tabla de estado si no existen.

    English:
        Create the SQLite file and state table if they do not exist.
    """
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with sqlite3.connect(path) as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS irreversibility_state (
                scope TEXT PRIMARY KEY,
                leader TEXT,
                irreversible INTEGER,
                timestamp TEXT
            )
            """
        )
        connection.commit()


def _load_state(path: str, scope: str) -> Optional[Tuple[str, int, str]]:
    """Carga el estado de irreversibilidad para un alcance específico.

    Devuelve una tupla con líder, flag de irreversibilidad y timestamp o None
    si no hay estado previo.

    English:
        Load irreversibility state for a given scope.

        Returns a tuple with leader, irreversible flag, and timestamp or None
        if no previous state exists.
    """
    if not os.path.exists(path):
        return None
    with sqlite3.connect(path) as connection:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT leader, irreversible, timestamp FROM irreversibility_state WHERE scope=?",
            (scope,),
        )
        row = cursor.fetchone()
        return row if row else None


def _save_state(
    path: str, scope: str, leader: str, irreversible: bool, timestamp: str
) -> None:
    """Persiste el estado de irreversibilidad en SQLite.

    Inserta o actualiza el registro por scope de forma idempotente.

    English:
        Persist the irreversibility state in SQLite.

        Inserts or updates the per-scope record in an idempotent way.
    """
    _ensure_db(path)
    with sqlite3.connect(path) as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO irreversibility_state (scope, leader, irreversible, timestamp)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(scope) DO UPDATE SET
                leader=excluded.leader,
                irreversible=excluded.irreversible,
                timestamp=excluded.timestamp
            """,
            (scope, leader, int(irreversible), timestamp),
        )
        connection.commit()


def _top_two_candidates(
    votes: Dict[str, Dict[str, object]],
) -> Optional[Tuple[str, int, str, int]]:
    """Obtiene el par líder/segundo con sus votos totales.

    Ordena candidatos por votos para devolver identificadores y conteos.

    English:
        Get the leader/runner-up pair with their vote totals.

        Sorts candidates by votes to return identifiers and counts.
    """
    if not votes:
        return None
    sorted_votes = sorted(
        votes.items(), key=lambda item: int(item[1].get("votes") or 0), reverse=True
    )
    if len(sorted_votes) < 2:
        return None
    leader_id, leader_data = sorted_votes[0]
    runner_id, runner_data = sorted_votes[1]
    leader_votes = int(leader_data.get("votes") or 0)
    runner_votes = int(runner_data.get("votes") or 0)
    return leader_id, leader_votes, runner_id, runner_votes


def apply(
    current_data: dict, previous_data: Optional[dict], config: dict
) -> List[dict]:
    """
    Determina si el resultado es estadísticamente irreversible según votos faltantes.

    La regla proyecta los votos faltantes usando un nivel de participación histórica.
    Si la brecha entre líder y segundo supera los votos faltantes, se declara
    irreversibilidad estadística. Si en un snapshot posterior se revierte una
    irreversibilidad previa, se genera una alerta de fraude confirmado.

    Args:
        current_data: Snapshot JSON actual del CNE.
        previous_data: Snapshot JSON anterior (None en el primer snapshot).
        config: Sección de configuración específica de la regla desde config.yaml.

    Returns:
        Lista de alertas en formato estándar (vacía si todo normal).

    English:
        Determines whether results are statistically irreversible based on remaining votes.

        The rule projects remaining votes using a historical participation rate. If the
        leader's gap exceeds remaining votes, the outcome is statistically irreversible.
        If a later snapshot reverses a prior irreversibility, a high-severity fraud
        confirmation alert is generated.

    Args:
        current_data: Current CNE JSON snapshot.
        previous_data: Previous JSON snapshot (None for the first snapshot).
        config: Rule-specific configuration section from config.yaml.

    Returns:
        List of alerts in the standard format (empty if normal).
    """
    alerts: List[dict] = []
    votes = extract_candidate_votes(current_data)
    if not votes:
        return alerts

    top_two = _top_two_candidates(votes)
    if not top_two:
        return alerts

    leader_id, leader_votes, runner_id, runner_votes = top_two
    total_votes = extract_total_votes(current_data)
    registered_voters = extract_registered_voters(current_data)
    if total_votes is None or registered_voters is None:
        return alerts

    participation_rate = float(config.get("historical_participation_rate", 0.60))
    projected_total = int(registered_voters * participation_rate)
    votes_remaining = max(projected_total - total_votes, 0)

    gap = abs(leader_votes - runner_votes)
    needed_to_revert = gap + 1

    scope = extract_department(current_data)
    timestamp_obj = parse_timestamp(current_data)
    timestamp = timestamp_obj.isoformat() if timestamp_obj else ""

    irreversible = needed_to_revert > votes_remaining

    state_path = config.get("sqlite_path", "reports/irreversibility_state.db")
    previous_state = _load_state(state_path, scope)

    if previous_state:
        previous_leader, previous_irreversible, _ = previous_state
        if previous_irreversible and (
            not irreversible or (previous_leader and previous_leader != leader_id)
        ):
            alerts.append(
                {
                    "type": "Fraude Confirmado por Manipulación de Universo de Actas",
                    "severity": "High",
                    "department": scope,
                    "justification": (
                        "Se revirtió una irreversibilidad estadística previa. "
                        f"lider_previo={previous_leader}, lider_actual={leader_id}, "
                        f"irreversible_actual={irreversible}."
                    ),
                }
            )

    if irreversible:
        alerts.append(
            {
                "type": "Resultado Estadísticamente Irreversible",
                "severity": "Medium",
                "department": scope,
                "justification": (
                    "La brecha entre líder y segundo supera votos faltantes. "
                    f"lider={leader_id} ({leader_votes}), segundo={runner_id} ({runner_votes}), "
                    f"brecha={gap}, votos_faltantes={votes_remaining}, "
                    f"participacion_historica={participation_rate:.2f}, "
                    f"padron={registered_voters}, total_actual={total_votes}."
                ),
            }
        )

    _save_state(state_path, scope, leader_id, irreversible, timestamp)
    return alerts
