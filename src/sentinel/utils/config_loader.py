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
SECURITY_PATH = Path("command_center") / "security_config.yaml"
ADVANCED_SECURITY_PATH = Path("command_center") / "advanced_security_config.yaml"
ATTACK_PATH = Path("command_center") / "attack_config.yaml"
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

BOOLEAN_EXACT_KEYS = {
    "enabled",
    "global_enabled",
    "allow_mock",
    "use_playwright",
    "playwright_stealth",
    "critical_only",
    "anonymize",
    "firewall_default_deny",
    "monitor_connections",
    "monitor_unexpected_connections",
    "auto_anchor_snapshots",
    "verify_on_startup",
    "verify_anchors_on_startup",
    "verify_signatures",
    "sign_hash_records",
    "zero_trust",
    "log_hashing",
    "log_encryption",
}


def _iter_non_boolean_flags(node: Any, prefix: str = "") -> list[str]:
    """Collect YAML paths where binary flags are not bool.

    Recolecta rutas YAML donde flags binarios no son bool.
    """
    errors: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            key_text = str(key)
            expects_bool = key_text in BOOLEAN_EXACT_KEYS or key_text.endswith("_enabled")
            if expects_bool and not isinstance(value, bool):
                errors.append(path)
            errors.extend(_iter_non_boolean_flags(value, path))
    elif isinstance(node, list):
        for index, item in enumerate(node):
            errors.extend(_iter_non_boolean_flags(item, f"{prefix}[{index}]"))
    return errors


def _validate_binary_conventions(payload: dict[str, Any], *, source_name: str) -> None:
    """Validate ON/OFF + true/false conventions with actionable errors.

    Valida convenciones ON/OFF + true/false con errores accionables.
    """
    master_switch = payload.get("master_switch")
    if "master_switch" in payload and master_switch not in {"ON", "OFF"}:
        raise ValueError(
            "{source}: master_switch debe ser exactamente \"ON\" o \"OFF\" "
            "(must be exactly \"ON\" or \"OFF\").".format(source=source_name)
        )

    bool_errors = _iter_non_boolean_flags(payload)
    if bool_errors:
        joined = ", ".join(sorted(bool_errors))
        raise ValueError(
            "{source}: los siguientes campos binarios deben usar true/false "
            "(without quotes): {fields}.".format(source=source_name, fields=joined)
        )


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    """Load a YAML mapping or raise a user-facing error.

    Carga un mapa YAML o lanza un error orientado al usuario.
    """
    if not path.exists():
        raise FileNotFoundError(f"Falta {path.as_posix()} (Missing {path.as_posix()}).")
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"{path.name} tiene errores de sintaxis YAML ({path.name} has YAML syntax errors).") from exc
    if not isinstance(raw, dict):
        raise ValueError(f"{path.name} debe ser un mapa YAML ({path.name} must be a YAML mapping).")
    return raw


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
            raise ValueError("rule_name debe ser una cadena no vacía (rule_name must be a non-empty string).")
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
    raw_config = _load_yaml_mapping(RULES_PATH)
    _validate_binary_conventions(raw_config, source_name=RULES_PATH.as_posix())

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
        raise FileNotFoundError("Falta command_center/config.yaml. Centraliza toda la configuración en esa ruta.")

    config = _load_yaml_mapping(CONFIG_PATH)
    _validate_binary_conventions(config, source_name=CONFIG_PATH.as_posix())

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

    # Validate sibling command center config layers so startup fails fast with
    # clear messages when a binary field is misconfigured.
    for sibling_path in (SECURITY_PATH, ADVANCED_SECURITY_PATH, ATTACK_PATH):
        sibling_payload = _load_yaml_mapping(sibling_path)
        _validate_binary_conventions(sibling_payload, source_name=sibling_path.as_posix())

    _archive_config_file(CONFIG_PATH, "config")
    load_rules_config()
    logging.getLogger(__name__).debug("Configuración cargada desde %s", CONFIG_PATH.as_posix())
    return config
