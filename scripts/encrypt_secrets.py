#!/usr/bin/env python3
# Encrypt Secrets Module
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

"""/** Compatibilidad para cifrado de secretos. / Compatibility wrapper for secret encryption. **/"""

from __future__ import annotations

from scripts.security.encrypt_secrets import (
    decrypt_secrets,
    encrypt_secrets,
    generate_key,
)

__all__ = ["decrypt_secrets", "encrypt_secrets", "generate_key"]

if __name__ == "__main__":
    # Ejemplo de uso / Usage example.
    print("Generated key (store securely):", generate_key())
    encrypt_secrets()
