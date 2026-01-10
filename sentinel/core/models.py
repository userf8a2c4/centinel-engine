"""Modelos de datos inmutables para snapshots electorales.

English:
    Immutable data models for election snapshots.
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class CandidateResult:
    """Representa el resultado de un candidato en un snapshot.

    Attributes:
        slot (int): Posición del candidato en la papeleta.
        votes (int): Votos registrados para el candidato.
        candidate_id (Optional[str]): Identificador del candidato.
        name (Optional[str]): Nombre del candidato.
        party (Optional[str]): Partido del candidato.

    English:
        Represents a candidate result within a snapshot.

    Attributes:
        slot (int): Ballot position for the candidate.
        votes (int): Votes recorded for the candidate.
        candidate_id (Optional[str]): Candidate identifier.
        name (Optional[str]): Candidate name.
        party (Optional[str]): Candidate party.
    """

    slot: int
    votes: int
    candidate_id: Optional[str] = None
    name: Optional[str] = None
    party: Optional[str] = None


@dataclass(frozen=True)
class Totals:
    """Guarda totales agregados de votos para un snapshot.

    Attributes:
        registered_voters (int): Ciudadanos inscritos.
        total_votes (int): Total de votos emitidos.
        valid_votes (int): Votos válidos.
        null_votes (int): Votos nulos.
        blank_votes (int): Votos en blanco.

    English:
        Stores aggregated vote totals for a snapshot.

    Attributes:
        registered_voters (int): Registered voters.
        total_votes (int): Total votes cast.
        valid_votes (int): Valid votes.
        null_votes (int): Null votes.
        blank_votes (int): Blank votes.
    """

    registered_voters: int
    total_votes: int
    valid_votes: int
    null_votes: int
    blank_votes: int


@dataclass(frozen=True)
class Meta:
    """Metadatos del snapshot electoral.

    Attributes:
        election (str): Nombre o código de la elección.
        year (int): Año de la elección.
        source (str): Fuente de los datos.
        scope (str): Alcance del snapshot.
        department_code (str): Código de departamento.
        timestamp_utc (str): Timestamp en UTC.

    English:
        Snapshot metadata for the election data.

    Attributes:
        election (str): Election name or code.
        year (int): Election year.
        source (str): Data source.
        scope (str): Snapshot scope.
        department_code (str): Department code.
        timestamp_utc (str): UTC timestamp.
    """

    election: str
    year: int
    source: str
    scope: str
    department_code: str
    timestamp_utc: str


@dataclass(frozen=True)
class Snapshot:
    """Snapshot canónico con metadatos, totales y resultados.

    Attributes:
        meta (Meta): Metadatos del snapshot.
        totals (Totals): Totales agregados.
        candidates (List[CandidateResult]): Resultados por candidato.

    English:
        Canonical snapshot with metadata, totals, and results.

    Attributes:
        meta (Meta): Snapshot metadata.
        totals (Totals): Aggregated totals.
        candidates (List[CandidateResult]): Candidate results.
    """

    meta: Meta
    totals: Totals
    candidates: List[CandidateResult]
