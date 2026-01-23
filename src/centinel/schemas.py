"""Esquemas Pydantic para validar y normalizar datos de la autoridad electoral.

Pydantic schemas to validate and normalize electoral authority data.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict

from pydantic import BaseModel, Field, ValidationError, field_validator


class ActaSchema(BaseModel):
    """Esquema de actas de la autoridad electoral.

    English: Electoral authority acta schema.
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
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Field cannot be empty")
        return cleaned


class ResultadosSchema(BaseModel):
    """Esquema de resultados de la autoridad electoral.

    English: Electoral authority results schema.
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
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Field cannot be empty")
        return cleaned

    @field_validator("mesas_contabilizadas")
    @classmethod
    def mesas_no_mayor_que_total(cls, value: int, info) -> int:
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
