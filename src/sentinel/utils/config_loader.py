"""Loads and validates the centralized C.E.N.T.I.N.E.L. configuration. (Carga y valida la configuración centralizada de C.E.N.T.I.N.E.L.)"""

from __future__ import annotations

import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

CONFIG_PATH = Path("command_center") / "config.yaml"
RULES_PATH = Path("command_center") / "rules.yaml"
CONFIG_HISTORY_DIR = Path("command_center") / "configs" / "history"

REQUIRED_TOP_LEVEL_KEYS = [
    "master_switch",
    "base_url",
    "endpoints",
    "timeout",
    "retries",
    "headers",
    "use_playwright",
    "playwright_stealth",
    "playwright_user_agent",
    "playwright_viewport",
    "playwright_locale",
    "playwright_timezone",
    "backoff_base_seconds",
    "backoff_max_seconds",
    "candidate_count",
    "required_keys",
    "field_map",
    "sources",
    "logging",
    "blockchain",
    "alerts",
    "arbitrum",
    "rules",
]

REQUIRED_NESTED_KEYS = {
    "logging": ["level", "file"],
    "blockchain": ["enabled", "network", "private_key"],
    "alerts": ["critical_anomaly_types"],
    "arbitrum": [
        "enabled",
        "network",
        "rpc_url",
        "private_key",
        "contract_address",
        "interval_minutes",
        "batch_size",
        "auto_anchor_snapshots",
    ],
    "rules": ["global_enabled"],
}


class RuleDefinition(BaseModel):
    """Defines a single rule entry for rules.yaml. (Define una entrada individual de regla para rules.yaml.)"""

    rule_name: str = Field(..., min_length=1)
    threshold: float
    enabled: bool = True
    parameters: dict[str, Any] = Field(default_factory=dict)

    @field_validator("rule_name")
    @classmethod
    def rule_name_must_be_non_empty(cls, value: str) -> str:
        """Ensure rule_name is not blank. (Asegura que rule_name no esté vacío.)"""
        if not value.strip():
            raise ValueError(
                "rule_name debe ser una cadena no vacía (rule_name must be a non-empty string)."
            )
        return value


class RulesConfig(BaseModel):
    """Schema for rules.yaml validation. (Esquema para validar rules.yaml.)"""

    rules: dict[str, RuleDefinition] = Field(default_factory=dict)
    retry_max: int | None = None
    backoff_factor: float | None = None
    chi2_p_critical: float | None = None
    benford_min_samples: int | None = None
    max_json_presidenciales: int | None = None
    security: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_rule_key_matches_name(self) -> "RulesConfig":
        """Ensure rule keys match rule_name. (Asegura que la clave coincida con rule_name.)"""
        for key, rule in self.rules.items():
            if rule.rule_name != key:
                raise ValueError(
                    "rules.{key}.rule_name debe coincidir con la clave "
                    "(rules.{key}.rule_name must match the key).".format(key=key)
                )
        return self

    model_config = {
        "extra": "allow",
    }


def _archive_config_file(source_path: Path, prefix: str) -> None:
    """Archive a config file with a timestamp. (Archiva un archivo de configuración con timestamp.)"""
    if not source_path.exists():
        return
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%fZ")
    history_path = CONFIG_HISTORY_DIR / f"{prefix}_{timestamp}{source_path.suffix}"
    try:
        CONFIG_HISTORY_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, history_path)
    except OSError as exc:
        logging.getLogger(__name__).warning(
            "No se pudo archivar %s en %s (Unable to archive %s to %s): %s",
            source_path,
            history_path,
            source_path,
            history_path,
            exc,
        )


def load_rules_config() -> dict[str, Any]:
    """Load and validate rules.yaml. (Carga y valida rules.yaml.)"""
    if not RULES_PATH.exists():
        raise FileNotFoundError(
            "Falta command_center/rules.yaml (Missing command_center/rules.yaml)."
        )

    try:
        raw_config = yaml.safe_load(RULES_PATH.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ValueError(
            "rules.yaml tiene errores de sintaxis (rules.yaml has syntax errors)."
        ) from exc

    if not isinstance(raw_config, dict):
        raise ValueError(
            "rules.yaml debe ser un mapa YAML (rules.yaml must be a YAML mapping)."
        )

    try:
        RulesConfig.model_validate(raw_config)
    except ValidationError as exc:
        raise ValueError(
            "rules.yaml no cumple el esquema requerido (rules.yaml does not meet the required schema)."
        ) from exc

    _archive_config_file(RULES_PATH, "rules")
    logging.getLogger(__name__).debug(
        "Reglas cargadas desde %s (Rules loaded from %s).",
        RULES_PATH.as_posix(),
        RULES_PATH.as_posix(),
    )
    return raw_config


def load_config() -> dict[str, Any]:
    """Load configuration from command_center/config.yaml and validate required keys. (Carga la configuración desde command_center/config.yaml y valida sus claves.)"""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            "Falta command_center/config.yaml. Centraliza toda la configuración en esa ruta."
        )

    with CONFIG_PATH.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}

    missing_keys: list[str] = []
    for key in REQUIRED_TOP_LEVEL_KEYS:
        if key not in config:
            missing_keys.append(key)

    for section_key, section_keys in REQUIRED_NESTED_KEYS.items():
        section = config
        for part in section_key.split("."):
            if not isinstance(section, dict) or part not in section:
                missing_keys.append(section_key)
                section = None
                break
            section = section[part]
        if section is None:
            continue
        for nested_key in section_keys:
            if not isinstance(section, dict) or nested_key not in section:
                missing_keys.append(f"{section_key}.{nested_key}")

    if missing_keys:
        missing = ", ".join(sorted(set(missing_keys)))
        raise KeyError(
            "Faltan claves requeridas en command_center/config.yaml: "
            f"{missing}. Revisa la configuración centralizada."
        )

    _archive_config_file(CONFIG_PATH, "config")
    load_rules_config()
    logging.getLogger(__name__).debug(
        "Configuración cargada desde %s", CONFIG_PATH.as_posix()
    )
    return config
