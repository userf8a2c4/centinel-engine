#!/usr/bin/env python3
"""/** Utilidad de cifrado de secretos con Fernet. / Secrets encryption utility using Fernet. **/"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Iterable

from cryptography.fernet import Fernet, InvalidToken
from dotenv import load_dotenv

from scripts.logging_utils import configure_logging, log_event

logger = configure_logging("centinel.security", log_file="logs/centinel.log")

DEFAULT_ENV_PATHS = (
    Path(".env"),
    Path(".env.local"),
    Path("command_center") / ".env",
)
DEFAULT_ENCRYPTED_PATH = Path(".env.encrypted")


def _load_env(paths: Iterable[Path]) -> None:
    """/** Carga variables desde archivos .env locales. / Load variables from local .env files. **/"""
    for path in paths:
        if path.exists():
            # Seguridad: carga sólo desde archivos locales. / Security: only load local files.
            load_dotenv(path, override=False)


def generate_key() -> str:
    """/** Genera una key Fernet (32 bytes base64). / Generate a Fernet key (32 bytes base64). **/"""
    return Fernet.generate_key().decode("utf-8")


def _get_fernet_key() -> bytes:
    """/** Obtiene la llave Fernet desde entorno. / Get Fernet key from environment. **/"""
    key = os.getenv("SECRET_ENCRYPTION_KEY") or os.getenv("FERNET_KEY")
    if not key:
        raise ValueError(
            "Missing SECRET_ENCRYPTION_KEY/FERNET_KEY environment variable"
        )
    return key.encode("utf-8")


def encrypt_secrets(
    keys: Iterable[str] | None = None,
    output_path: Path | None = None,
) -> dict[str, str]:
    """/** Encripta secretos del entorno en .env.encrypted. / Encrypt env secrets into .env.encrypted. **/"""
    _load_env(DEFAULT_ENV_PATHS)
    selected_keys = list(keys or ["ARBITRUM_PRIVATE_KEY"])
    output_path = output_path or DEFAULT_ENCRYPTED_PATH

    try:
        fernet = Fernet(_get_fernet_key())
    except (ValueError, InvalidToken) as exc:
        log_event(logger, logging.ERROR, "encrypt_key_invalid")
        raise ValueError("Invalid Fernet key") from exc

    encrypted: dict[str, str] = {}
    for key in selected_keys:
        value = os.getenv(key)
        if not value:
            log_event(
                logger, logging.WARNING, "encrypt_missing_secret", secret_name=key
            )
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


def decrypt_secrets(
    keys: Iterable[str] | None = None,
    encrypted_path: Path | None = None,
) -> dict[str, str]:
    """/** Desencripta secretos en memoria sin persistirlos. / Decrypt secrets in memory without persisting them. **/"""
    selected_keys = set(keys or ["ARBITRUM_PRIVATE_KEY"])
    encrypted_path = encrypted_path or DEFAULT_ENCRYPTED_PATH

    if not encrypted_path.exists():
        log_event(
            logger, logging.WARNING, "decrypt_missing_file", path=str(encrypted_path)
        )
        return {}

    try:
        fernet = Fernet(_get_fernet_key())
    except (ValueError, InvalidToken) as exc:
        log_event(logger, logging.ERROR, "decrypt_key_invalid")
        raise ValueError("Invalid Fernet key") from exc

    try:
        encrypted_payload = json.loads(encrypted_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        log_event(logger, logging.ERROR, "decrypt_payload_invalid")
        raise ValueError("Encrypted payload is invalid") from exc

    decrypted: dict[str, str] = {}
    for key, token in encrypted_payload.items():
        if key not in selected_keys:
            continue
        try:
            decrypted[key] = fernet.decrypt(token.encode("utf-8")).decode("utf-8")
        except (InvalidToken, ValueError) as exc:
            # Seguridad: falla cerrada si la clave no es válida. / Security: fail closed if key/token is invalid.
            log_event(logger, logging.ERROR, "decrypt_failed", secret_name=key)
            raise ValueError("Decryption failed") from exc
    return decrypted


if __name__ == "__main__":
    # Ejemplo de uso / Usage example.
    print("Generated key (store securely):", generate_key())
    encrypt_secrets()
