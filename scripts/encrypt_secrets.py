#!/usr/bin/env python3
"""Encripta y desencripta secrets sensibles con Fernet.

English:
    Encrypt and decrypt sensitive secrets with Fernet.

Ejemplo seguro / Secure example:
    1) Generar key y guardarla en .env:
       python scripts/encrypt_secrets.py generate-key
       # export SECRET_ENCRYPTION_KEY="base64key"
    2) Encriptar ARBITRUM_PRIVATE_KEY desde el entorno:
       python scripts/encrypt_secrets.py encrypt --env ARBITRUM_PRIVATE_KEY
    3) Desencriptar un valor previamente cifrado:
       python scripts/encrypt_secrets.py decrypt --value "<token>"
"""

from __future__ import annotations

import argparse
import logging
import os
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from scripts.logging_utils import configure_logging, log_event

logger = configure_logging(__name__)

ENV_KEY_NAME = "SECRET_ENCRYPTION_KEY"


def generate_key() -> str:
    """Función segura para generar keys / Secure function for generating keys."""
    return Fernet.generate_key().decode("utf-8")


def _load_key(raw_key: Optional[str]) -> bytes:
    """Función segura para cargar key / Secure function for loading a key."""
    key = raw_key or os.getenv(ENV_KEY_NAME, "")
    if not key:
        raise ValueError(f"Missing encryption key in {ENV_KEY_NAME}.")
    return key.encode("utf-8")


def encrypt_value(value: str, raw_key: Optional[str] = None) -> str:
    """Función segura para encriptar secretos / Secure function for encrypting secrets."""
    key = _load_key(raw_key)
    fernet = Fernet(key)
    token = fernet.encrypt(value.encode("utf-8")).decode("utf-8")
    return token


def decrypt_value(token: str, raw_key: Optional[str] = None) -> str:
    """Función segura para desencriptar secretos / Secure function for decrypting secrets."""
    key = _load_key(raw_key)
    fernet = Fernet(key)
    return fernet.decrypt(token.encode("utf-8")).decode("utf-8")


def _get_env_secret(env_name: str) -> str:
    """Función segura para leer envs / Secure function for reading envs."""
    value = os.getenv(env_name, "")
    if not value:
        raise ValueError(f"Missing environment variable: {env_name}")
    return value


def _build_parser() -> argparse.ArgumentParser:
    """Función segura para construir CLI / Secure function for building CLI."""
    parser = argparse.ArgumentParser(description="Encrypt or decrypt secrets.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("generate-key", help="Generate a new encryption key.")

    encrypt_parser = subparsers.add_parser("encrypt", help="Encrypt a secret value.")
    encrypt_parser.add_argument("--value", help="Plaintext secret to encrypt.")
    encrypt_parser.add_argument(
        "--env", help="Name of env var to read (e.g., ARBITRUM_PRIVATE_KEY)."
    )
    encrypt_parser.add_argument("--key", help="Encryption key override.")

    decrypt_parser = subparsers.add_parser("decrypt", help="Decrypt an encrypted value.")
    decrypt_parser.add_argument("--value", required=True, help="Encrypted token.")
    decrypt_parser.add_argument("--key", help="Encryption key override.")
    return parser


def main() -> int:
    """Función segura para ejecutar el script / Secure function for running the script."""
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "generate-key":
        key = generate_key()
        # Seguridad: Evita exposición de datos sensibles / Security: Avoid exposure of sensitive data.
        log_event(logger, logging.INFO, "generated_encryption_key", key_hash=key)
        print(key)
        return 0

    if args.command == "encrypt":
        if not args.value and not args.env:
            raise ValueError("Provide --value or --env for encryption.")
        secret_value = args.value or _get_env_secret(args.env)
        token = encrypt_value(secret_value, args.key)
        log_event(
            logger,
            logging.INFO,
            "secret_encrypted",
            source=args.env or "manual",
        )
        print(token)
        return 0

    if args.command == "decrypt":
        try:
            plaintext = decrypt_value(args.value, args.key)
        except InvalidToken as exc:
            log_event(logger, logging.ERROR, "decrypt_failed", reason=str(exc))
            return 1
        log_event(logger, logging.INFO, "secret_decrypted")
        print(plaintext)
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
