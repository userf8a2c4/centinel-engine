#!/usr/bin/env python3
"""/** Compatibilidad para cifrado de secretos. / Compatibility wrapper for secret encryption. **/"""

from __future__ import annotations

from scripts.security.encrypt_secrets import decrypt_secrets, encrypt_secrets, generate_key

__all__ = ["decrypt_secrets", "encrypt_secrets", "generate_key"]

if __name__ == "__main__":
    # Ejemplo de uso / Usage example.
    print("Generated key (store securely):", generate_key())
    encrypt_secrets()
