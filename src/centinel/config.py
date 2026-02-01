"""Configuración segura y validada de Centinel.

Secure and validated Centinel configuration.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv
from pydantic import AnyUrl, BaseModel, Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_PATH = Path(".env")
_ENV_LOCAL_PATH = Path(".env.local")
# Seguridad: Cargar variables sensibles desde .env y .env.local. / Security: Load sensitive vars from .env/.env.local.
load_dotenv(_ENV_PATH, override=False)
load_dotenv(_ENV_LOCAL_PATH, override=False)


class SourceConfig(BaseModel):
    """Fuente configurable para ingesta.

    English: Configurable ingestion source.
    """

    url: AnyUrl
    type: str
    interval_seconds: int = Field(ge=60)
    auth_headers: Optional[Dict[str, str]] = None


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
        settings = CentinelSettings()
        settings.validate_paths()
        return settings
    except ValidationError as exc:
        raise ValueError(f"Invalid configuration: {exc}") from exc
