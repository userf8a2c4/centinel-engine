#!/usr/bin/env python3
"""Utilidad para encriptar secretos sensibles con Fernet.

Utility to encrypt sensitive secrets with Fernet.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Iterable

from cryptography.fernet import Fernet, InvalidToken
from dotenv import load_dotenv

from scripts.logging_utils import configure_logging, log_event

logger = configure_logging("centinel.encrypt", log_file="logs/centinel.log")

DEFAULT_ENV_PATHS = (
    Path(".env"),
    Path(".env.local"),
    Path("command_center") / ".env",
)


def _load_env(paths: Iterable[Path]) -> None:
    """/** Carga variables desde archivos .env. / Load variables from .env files. **/"""
    for path in paths:
        if path.exists():
            # Seguridad: carga sólo desde archivos locales. / Security: only load local files.
            load_dotenv(path, override=False)


def _get_fernet_key() -> bytes:
    """/** Obtiene la llave Fernet desde entorno. / Get Fernet key from environment. **/"""
    key = os.getenv("FERNET_KEY")
    if not key:
        raise ValueError("Missing FERNET_KEY environment variable")
    return key.encode("utf-8")


def encrypt_secrets(
    keys: Iterable[str] | None = None,
    output_path: Path | None = None,
) -> dict[str, str]:
    """/** Encripta secretos del entorno en un JSON. / Encrypt env secrets into a JSON file. **/"""
    _load_env(DEFAULT_ENV_PATHS)
    selected_keys = list(keys or ["ARBITRUM_KEY"])
    output_path = output_path or Path(os.getenv("ENCRYPT_OUTPUT", "secrets.encrypted.json"))

    try:
        fernet = Fernet(_get_fernet_key())
    except (ValueError, InvalidToken) as exc:
        log_event(logger, logging.ERROR, "encrypt_key_invalid")
        raise ValueError("Invalid Fernet key") from exc

    encrypted: dict[str, str] = {}
    for key in selected_keys:
        value = os.getenv(key)
        if not value:
            log_event(logger, logging.WARNING, "encrypt_missing_secret", secret_name=key)
            continue
        try:
            token = fernet.encrypt(value.encode("utf-8")).decode("utf-8")
        except Exception as exc:  # noqa: BLE001
            # Seguridad: fallback seguro si falla la crypto. / Security: safe fallback on crypto errors.
            log_event(logger, logging.ERROR, "encrypt_failed", secret_name=key)
            raise ValueError("Encryption failed") from exc
        encrypted[key] = token

    output_path.write_text(
        json.dumps(encrypted, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    log_event(
        logger,
        logging.INFO,
        "encrypt_complete",
        secrets_encrypted=len(encrypted),
        output=str(output_path),
    )
    return encrypted


if __name__ == "__main__":
    encrypt_secrets()
