from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class CandidateResult:
    slot: int
    votes: int
    candidate_id: Optional[str] = None
    name: Optional[str] = None
    party: Optional[str] = None


@dataclass(frozen=True)
class Totals:
    registered_voters: int
    total_votes: int
    valid_votes: int
    null_votes: int
    blank_votes: int


@dataclass(frozen=True)
class Meta:
    election: str
    year: int
    source: str
    scope: str
    department_code: str
    timestamp_utc: str


@dataclass(frozen=True)
class Snapshot:
    meta: Meta
    totals: Totals
    candidates: List[CandidateResult]
