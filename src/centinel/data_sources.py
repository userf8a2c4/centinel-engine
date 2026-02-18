"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `src/centinel/data_sources.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - DataSourceError
  - DataSourceConfigError
  - DataSourceExhaustedError
  - DataSourceKind
  - DataSourceDefinition
  - DataSourceSettings
  - load_data_source_settings
  - DataSourceCheckpoint
  - DataSourceManager

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `src/centinel/data_sources.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - DataSourceError
  - DataSourceConfigError
  - DataSourceExhaustedError
  - DataSourceKind
  - DataSourceDefinition
  - DataSourceSettings
  - load_data_source_settings
  - DataSourceCheckpoint
  - DataSourceManager

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
"""

# Data Sources Module
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



from __future__ import annotations

import asyncio
import json
import time
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import httpx
import yaml
from pydantic import AnyUrl, BaseModel, Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from .download import write_atomic

Acta = Dict[str, Any]


class DataSourceError(Exception):
    """Error general de una fuente de datos.

    English: General data source error.
    """


class DataSourceConfigError(DataSourceError):
    """Error de configuración de fuentes.

    English: Data source configuration error.
    """


class DataSourceExhaustedError(DataSourceError):
    """Todas las fuentes fallaron.

    English: All sources failed.
    """


class DataSourceKind(str, Enum):
    """Tipos de fuente soportados."""

    CNE_API = "cne_api"
    MIRROR_BUCKET = "mirror_bucket"
    CITIZEN_MIRROR = "citizen_mirror"
    TELEGRAM_CHANNEL = "telegram_channel"
    FALLBACK_SCRAPE = "fallback_scrape"


class DataSourceDefinition(BaseModel):
    """Definición de una fuente de datos."""

    source_id: str = Field(min_length=1)
    kind: DataSourceKind
    enabled: bool = True
    base_url: Optional[AnyUrl] = None
    batch_path: Optional[str] = None
    data_key: Optional[str] = None
    headers: Dict[str, str] = Field(default_factory=dict)
    params: Dict[str, str] = Field(default_factory=dict)
    timeout_seconds: Optional[int] = Field(default=None, ge=1)
    retries: Optional[int] = Field(default=None, ge=1)


class DataSourceSettings(BaseSettings):
    """Configuración para DataSourceManager vía .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
    )

    DATA_SOURCES: List[DataSourceDefinition] = Field(default_factory=list)
    STORAGE_PATH: Path = Path("data")
    CHECKPOINT_FILENAME: str = "datasource_state.json"

    @property
    def storage_path(self) -> Path:
        """Español: Función storage_path del módulo src/centinel/data_sources.py.

        English: Function storage_path defined in src/centinel/data_sources.py.
        """
        return self.STORAGE_PATH

    @property
    def checkpoint_path(self) -> Path:
        """Español: Función checkpoint_path del módulo src/centinel/data_sources.py.

        English: Function checkpoint_path defined in src/centinel/data_sources.py.
        """
        return self.STORAGE_PATH / "checkpoints" / self.CHECKPOINT_FILENAME


def load_data_source_settings(config_path: Optional[Path] = None) -> DataSourceSettings:
    """Carga configuración desde YAML o .env.

    English: Load configuration from YAML or .env.
    """
    if config_path:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        payload = {
            "DATA_SOURCES": raw.get("data_sources", []),
            "STORAGE_PATH": raw.get("storage_path", "data"),
            "CHECKPOINT_FILENAME": raw.get("checkpoint_filename", "datasource_state.json"),
        }
        try:
            return DataSourceSettings.model_validate(payload)
        except ValidationError as exc:
            raise DataSourceConfigError(f"Invalid YAML config: {exc}") from exc

    try:
        return DataSourceSettings()
    except ValidationError as exc:
        raise DataSourceConfigError(f"Invalid .env config: {exc}") from exc


@dataclass(frozen=True)
class DataSourceCheckpoint:
    """Estado persistente de la fuente."""

    last_successful_source_id: str
    updated_at: str


class DataSourceManager:
    """Administra la selección de fuentes con fallback automático."""

    def __init__(
        self,
        settings: DataSourceSettings,
        *,
        logger: Optional[logging.Logger] = None,
        alert_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None,
    ) -> None:
        """Español: Función __init__ del módulo src/centinel/data_sources.py.

        English: Function __init__ defined in src/centinel/data_sources.py.
        """
        self.settings = settings
        self.logger = logger or logging.getLogger(__name__)
        self.alert_callback = alert_callback
        self.sources = [source for source in settings.DATA_SOURCES if source.enabled]
        if not self.sources:
            raise DataSourceConfigError("No active data sources configured.")

        self._client = httpx.AsyncClient(timeout=httpx.Timeout(10.0))
        self._last_successful_source_id = self._load_checkpoint()

    async def __aenter__(self) -> "DataSourceManager":
        """Español: Función asíncrona __aenter__ del módulo src/centinel/data_sources.py.

        English: Async function __aenter__ defined in src/centinel/data_sources.py.
        """
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        """Español: Función asíncrona __aexit__ del módulo src/centinel/data_sources.py.

        English: Async function __aexit__ defined in src/centinel/data_sources.py.
        """
        await self._client.aclose()

    async def get_next_batch(self) -> Optional[List[Acta]]:
        """Obtiene el siguiente batch de actas con fallback automático."""
        start_index = self._starting_index()
        last_error: Optional[Exception] = None
        self.logger.info(
            "datasource_cycle_start",
            sources=len(self.sources),
            start_index=start_index,
            last_successful_source_id=self._last_successful_source_id,
        )

        for offset in range(len(self.sources)):
            source = self.sources[(start_index + offset) % len(self.sources)]
            try:
                batch = await self._fetch_with_retries(source)
            except DataSourceError as exc:
                last_error = exc
                self.logger.warning(
                    "datasource_fallback",
                    source_id=source.source_id,
                    kind=source.kind.value,
                    reason=str(exc),
                )
                continue

            self.logger.info(
                "datasource_success",
                source_id=source.source_id,
                kind=source.kind.value,
                batch_size=len(batch) if batch else 0,
            )
            self._save_checkpoint(source.source_id)
            return batch or None

        reason = str(last_error) if last_error else "No sources available."
        self.logger.critical("datasource_exhausted", reason=reason)
        if self.alert_callback:
            self.alert_callback("datasource_exhausted", {"reason": reason})
        raise DataSourceExhaustedError("All data sources failed; pausing pipeline and alerting.")

    def _starting_index(self) -> int:
        """Español: Función _starting_index del módulo src/centinel/data_sources.py.

        English: Function _starting_index defined in src/centinel/data_sources.py.
        """
        if not self._last_successful_source_id:
            return 0
        for idx, source in enumerate(self.sources):
            if source.source_id == self._last_successful_source_id:
                return idx
        return 0

    async def _fetch_with_retries(self, source: DataSourceDefinition) -> List[Acta]:
        """Español: Función asíncrona _fetch_with_retries del módulo src/centinel/data_sources.py.

        English: Async function _fetch_with_retries defined in src/centinel/data_sources.py.
        """
        retries = source.retries or 3
        timeout_seconds = source.timeout_seconds or 10
        last_error: Optional[Exception] = None

        for attempt in range(1, retries + 1):
            try:
                return await asyncio.wait_for(
                    self._fetch_from_source(source),
                    timeout=timeout_seconds,
                )
            except (asyncio.TimeoutError, httpx.RequestError, DataSourceError) as exc:
                last_error = exc
                self.logger.warning(
                    "datasource_retry",
                    source_id=source.source_id,
                    kind=source.kind.value,
                    attempt=attempt,
                    reason=str(exc),
                )
                if attempt < retries:
                    await asyncio.sleep(min(2**attempt, 6))

        raise DataSourceError(f"Source {source.source_id} failed after {retries} retries: {last_error}")

    async def _fetch_from_source(self, source: DataSourceDefinition) -> List[Acta]:
        """Español: Función asíncrona _fetch_from_source del módulo src/centinel/data_sources.py.

        English: Async function _fetch_from_source defined in src/centinel/data_sources.py.
        """
        if source.kind in {
            DataSourceKind.CNE_API,
            DataSourceKind.MIRROR_BUCKET,
            DataSourceKind.CITIZEN_MIRROR,
        }:
            return await self._fetch_http_json(source)

        if source.kind is DataSourceKind.TELEGRAM_CHANNEL:
            raise DataSourceError("telegram_channel source not implemented yet.")

        if source.kind is DataSourceKind.FALLBACK_SCRAPE:
            raise DataSourceError("fallback_scrape source not implemented yet.")

        raise DataSourceError(f"Unsupported source kind: {source.kind}")

    async def _fetch_http_json(self, source: DataSourceDefinition) -> List[Acta]:
        """Español: Función asíncrona _fetch_http_json del módulo src/centinel/data_sources.py.

        English: Async function _fetch_http_json defined in src/centinel/data_sources.py.
        """
        if not source.base_url:
            raise DataSourceError(f"Source {source.source_id} requires base_url for HTTP fetch.")
        url = str(source.base_url)
        if source.batch_path:
            url = f"{url.rstrip('/')}/{source.batch_path.lstrip('/')}"

        start = time.monotonic()
        response = await self._client.get(
            url,
            headers=source.headers,
            params=source.params,
            timeout=httpx.Timeout(source.timeout_seconds or 10),
        )
        elapsed = time.monotonic() - start
        self.logger.info(
            "datasource_response",
            source_id=source.source_id,
            kind=source.kind.value,
            url=url,
            status_code=response.status_code,
            elapsed_seconds=round(elapsed, 3),
        )
        if response.status_code >= 400:
            raise DataSourceError(f"HTTP {response.status_code} from {source.source_id} ({url})")

        payload = response.json()
        payload_type = type(payload).__name__
        payload_size: Optional[int] = None
        if isinstance(payload, list):
            payload_size = len(payload)
        elif isinstance(payload, dict):
            if source.data_key and source.data_key in payload:
                raw_batch = payload.get(source.data_key)
            else:
                raw_batch = payload.get("actas") or payload.get("data")
            if isinstance(raw_batch, list):
                payload_size = len(raw_batch)
        self.logger.debug(
            "datasource_payload_loaded",
            source_id=source.source_id,
            kind=source.kind.value,
            payload_type=payload_type,
            payload_size=payload_size,
        )
        return self._extract_batch(payload, source)

    def _extract_batch(self, payload: Any, source: DataSourceDefinition) -> List[Acta]:
        """Español: Función _extract_batch del módulo src/centinel/data_sources.py.

        English: Function _extract_batch defined in src/centinel/data_sources.py.
        """
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            if source.data_key and source.data_key in payload:
                batch = payload[source.data_key]
            elif "actas" in payload:
                batch = payload["actas"]
            elif "data" in payload:
                batch = payload["data"]
            else:
                raise DataSourceError(f"Unable to locate batch list in payload for {source.source_id}.")
            if not isinstance(batch, list):
                raise DataSourceError(f"Batch payload for {source.source_id} must be a list.")
            return batch
        raise DataSourceError(f"Unexpected payload type from {source.source_id}: {type(payload)}")

    def _load_checkpoint(self) -> Optional[str]:
        """Español: Función _load_checkpoint del módulo src/centinel/data_sources.py.

        English: Function _load_checkpoint defined in src/centinel/data_sources.py.
        """
        path = self.settings.checkpoint_path
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            self.logger.warning("datasource_checkpoint_corrupt", path=str(path))
            return None
        return data.get("last_successful_source_id")

    def _save_checkpoint(self, source_id: str) -> None:
        """Español: Función _save_checkpoint del módulo src/centinel/data_sources.py.

        English: Function _save_checkpoint defined in src/centinel/data_sources.py.
        """
        payload = DataSourceCheckpoint(
            last_successful_source_id=source_id,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        data = json.dumps(payload.__dict__, ensure_ascii=False, indent=2).encode("utf-8")
        write_atomic(self.settings.checkpoint_path, data)
        self._last_successful_source_id = source_id
