# Schemas Module
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

"""Esquemas Pydantic para validar y normalizar datos del CNE.

Pydantic schemas to validate and normalize CNE data.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

logger = logging.getLogger(__name__)


class ActaSchema(BaseModel):
    """Esquema de actas del CNE.

    English: CNE acta schema.
    """

    version: str = Field(default="1.0")
    acta_id: str = Field(min_length=1)
    junta_receptora: str = Field(min_length=1)
    departamento: str = Field(min_length=1)
    municipio: str = Field(min_length=1)
    centro_votacion: str = Field(min_length=1)
    timestamp: datetime
    votos_totales: int = Field(ge=0)

    @field_validator("acta_id", "junta_receptora", "departamento", "municipio", "centro_votacion")
    @classmethod
    def strip_text(cls, value: str) -> str:
        """Normaliza texto eliminando espacios y valida no vacío.

        English:
            Normalize text by trimming whitespace and validate non-empty.
        """
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Field cannot be empty")
        return cleaned


class ResultadosSchema(BaseModel):
    """Esquema de resultados del CNE.

    English: CNE results schema.
    """

    version: str = Field(default="1.0")
    acta_id: str = Field(min_length=1)
    partido: str = Field(min_length=1)
    candidato: str = Field(min_length=1)
    votos: int = Field(ge=0)
    total_mesas: int = Field(ge=0)
    mesas_contabilizadas: int = Field(ge=0)

    @field_validator("acta_id", "partido", "candidato")
    @classmethod
    def strip_text(cls, value: str) -> str:
        """Normaliza texto eliminando espacios y valida no vacío.

        English:
            Normalize text by trimming whitespace and validate non-empty.
        """
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Field cannot be empty")
        return cleaned

    @field_validator("mesas_contabilizadas")
    @classmethod
    def mesas_no_mayor_que_total(cls, value: int, info) -> int:
        """Garantiza que mesas contabilizadas no supere el total.

        English:
            Ensure accounted tables do not exceed the total count.
        """
        total = info.data.get("total_mesas", 0)
        if value > total:
            raise ValueError("mesas_contabilizadas cannot exceed total_mesas")
        return value


def _parse_payload(data: dict | bytes) -> Dict[str, Any]:
    """Parsea payload dict o bytes a dict JSON.

    English: Parse dict or bytes payload into JSON dict.
    """
    if isinstance(data, bytes):
        try:
            decoded = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("Payload is not valid UTF-8") from exc
        try:
            return json.loads(decoded)
        except json.JSONDecodeError as exc:
            raise ValueError("Payload is not valid JSON") from exc
    if isinstance(data, dict):
        return data
    raise ValueError("Payload must be a dict or bytes")


def _migrate_acta(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Migra payload de actas desde claves anteriores.

    English: Migrate acta payload from legacy keys.
    """
    if "id_acta" in payload and "acta_id" not in payload:
        payload["acta_id"] = payload.pop("id_acta")
    if "jr" in payload and "junta_receptora" not in payload:
        payload["junta_receptora"] = payload.pop("jr")
    if "cv" in payload and "centro_votacion" not in payload:
        payload["centro_votacion"] = payload.pop("cv")
    if "ts" in payload and "timestamp" not in payload:
        payload["timestamp"] = payload.pop("ts")
    return payload


def _migrate_resultados(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Migra payload de resultados desde claves anteriores.

    English: Migrate results payload from legacy keys.
    """
    if "acta" in payload and "acta_id" not in payload:
        payload["acta_id"] = payload.pop("acta")
    if "party" in payload and "partido" not in payload:
        payload["partido"] = payload.pop("party")
    if "candidate" in payload and "candidato" not in payload:
        payload["candidato"] = payload.pop("candidate")
    if "votes" in payload and "votos" not in payload:
        payload["votos"] = payload.pop("votes")
    return payload


def validate_and_normalize(data: dict | bytes, source_type: str) -> Dict[str, Any]:
    """Valida y normaliza según el tipo de fuente.

    English: Validate and normalize by source type.
    """
    payload = _parse_payload(data)
    normalized_type = source_type.strip().lower()

    if normalized_type == "actas":
        try:
            model = ActaSchema.model_validate(payload)
        except ValidationError:
            migrated = _migrate_acta(payload)
            model = ActaSchema.model_validate(migrated)
        return model.model_dump()

    if normalized_type == "resultados":
        try:
            model = ResultadosSchema.model_validate(payload)
        except ValidationError:
            migrated = _migrate_resultados(payload)
            model = ResultadosSchema.model_validate(migrated)
        return model.model_dump()

    raise ValueError(f"Unknown source_type: {source_type}")


# ---------------------------------------------------------------------------
# Snapshot schemas — validate the JSON structure consumed by the rules engine
# ---------------------------------------------------------------------------


class CandidateSchema(BaseModel):
    """Schema for a single candidate entry inside a snapshot.

    Esquema para una entrada de candidato dentro de un snapshot.
    """

    slot: int = Field(ge=0)
    votes: int = Field(ge=0)
    candidate_id: Optional[str] = None
    name: Optional[str] = None
    party: Optional[str] = None


class TotalsSchema(BaseModel):
    """Schema for aggregated vote totals.

    Esquema para totales agregados de votos.
    """

    registered_voters: int = Field(ge=0)
    total_votes: int = Field(ge=0)
    valid_votes: int = Field(ge=0)
    null_votes: int = Field(ge=0)
    blank_votes: int = Field(ge=0)

    @model_validator(mode="after")
    def votes_do_not_exceed_registered(self) -> "TotalsSchema":
        """total_votes must not exceed registered_voters."""
        if self.total_votes > self.registered_voters:
            raise ValueError(
                f"total_votes ({self.total_votes}) exceeds " f"registered_voters ({self.registered_voters})"
            )
        return self


class MetaSchema(BaseModel):
    """Schema for snapshot metadata.

    Esquema para metadatos del snapshot.
    """

    election: str = Field(min_length=1)
    year: int = Field(ge=2000, le=2100)
    source: str = Field(min_length=1)
    scope: str = Field(min_length=1)
    department_code: str = Field(min_length=1)
    timestamp_utc: str = Field(min_length=1)


class SnapshotSchema(BaseModel):
    """Full schema for a canonical CNE snapshot consumed by the rules engine.

    Esquema completo para un snapshot canónico del CNE consumido por el motor de reglas.
    """

    meta: MetaSchema
    totals: TotalsSchema
    candidates: List[CandidateSchema] = Field(min_length=1)


def validate_snapshot(data: dict | bytes) -> Dict[str, Any]:
    """Validate a raw snapshot dict/bytes against ``SnapshotSchema``.

    Returns the validated dict on success; raises ``ValueError`` on failure.

    Valida un snapshot crudo contra ``SnapshotSchema``.
    Retorna el dict validado en éxito; lanza ``ValueError`` en fallo.
    """
    payload = _parse_payload(data)
    try:
        model = SnapshotSchema.model_validate(payload)
    except ValidationError as exc:
        raise ValueError(f"Snapshot validation failed: {exc}") from exc
    return model.model_dump()
