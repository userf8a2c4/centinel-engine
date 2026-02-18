# Config Module
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

"""Configuración segura y validada de Centinel.

Secure and validated Centinel configuration.
"""

from __future__ import annotations

from importlib.util import find_spec
import json
import os
from pathlib import Path
from typing import Dict, List, Optional

if find_spec("dotenv"):
    from dotenv import load_dotenv
else:

    def load_dotenv(*_args, **_kwargs) -> bool:
        return False


from pydantic import (
    AnyUrl,
    BaseModel,
    Field,
    TypeAdapter,
    ValidationError,
    field_validator,
)

if find_spec("pydantic_settings"):
    from pydantic_settings import BaseSettings, SettingsConfigDict

    _HAS_PYDANTIC_SETTINGS = True
else:
    BaseSettings = BaseModel

    class SettingsConfigDict(dict):
        """Fallback placeholder when pydantic_settings is unavailable."""

    _HAS_PYDANTIC_SETTINGS = False

_ENV_PATH = Path(".env")
_ENV_LOCAL_PATH = Path(".env.local")
# Seguridad: Cargar variables sensibles desde .env y .env.local. / Security: Load sensitive vars from .env/.env.local.
load_dotenv(_ENV_PATH, override=False)
load_dotenv(_ENV_LOCAL_PATH, override=False)


class SourceConfig(BaseModel):
    """Fuente configurable para ingesta.

    English: Configurable ingestion source.
    """

    url: str
    type: str
    interval_seconds: int = Field(ge=60)
    auth_headers: Optional[Dict[str, str]] = None

    @field_validator("url")
    @classmethod
    def _validate_url(cls, value: str) -> str:
        """Validate URLs without changing the stored type."""
        TypeAdapter(AnyUrl).validate_python(value)
        return value


class CentinelSettings(BaseSettings):
    """Variables de entorno y archivo .env para Centinel.

    English: Environment variables and .env file for Centinel.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
    )

    SOURCES: List[SourceConfig]
    STORAGE_PATH: Path
    LOG_LEVEL: str = "INFO"
    BOT_TOKEN_DISCORD: Optional[str] = None
    ARBITRUM_RPC_URL: AnyUrl
    IPFS_GATEWAY_URL: AnyUrl

    def validate_paths(self) -> None:
        """/** Valida que las rutas críticas existan. / Validate that critical paths exist. **/"""
        if not self.STORAGE_PATH.exists():
            raise ValueError(f"STORAGE_PATH does not exist: {self.STORAGE_PATH}")
        if not self.STORAGE_PATH.is_dir():
            raise ValueError(f"STORAGE_PATH is not a directory: {self.STORAGE_PATH}")


def load_config() -> CentinelSettings:
    """/** Carga y valida configuración, fallando con detalle. / Load and validate configuration, failing with details. **/"""
    try:
        if _HAS_PYDANTIC_SETTINGS:
            settings = CentinelSettings()
        else:
            raw_sources = os.getenv("SOURCES")
            sources = json.loads(raw_sources) if raw_sources else None
            storage_path = os.getenv("STORAGE_PATH")
            arbitrum_url = os.getenv("ARBITRUM_RPC_URL")
            ipfs_url = os.getenv("IPFS_GATEWAY_URL")
            settings = CentinelSettings(
                SOURCES=sources,
                STORAGE_PATH=Path(storage_path) if storage_path else None,
                LOG_LEVEL=os.getenv("LOG_LEVEL", "INFO"),
                BOT_TOKEN_DISCORD=os.getenv("BOT_TOKEN_DISCORD"),
                ARBITRUM_RPC_URL=arbitrum_url,
                IPFS_GATEWAY_URL=ipfs_url,
            )
        settings.validate_paths()
        return settings
    except ValidationError as exc:
        raise ValueError(f"Invalid configuration: {exc}") from exc
