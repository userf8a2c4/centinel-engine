#!/usr/bin/env python3
# Auto Anchor Module
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

"""/** Anclaje manual con desencriptación bajo demanda. / Manual anchoring with on-demand decryption. **/"""

from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
from typing import Any

from anchor.arbitrum_anchor import anchor_batch, anchor_root
from centinel_engine.config_loader import load_config
from scripts.logging_utils import configure_logging, log_event
from scripts.security.encrypt_secrets import decrypt_secrets

logger = configure_logging("centinel.auto_anchor", log_file="logs/centinel.log")

def _load_security_settings() -> dict[str, Any]:
    """/** Carga configuración de seguridad desde config/prod/rules.yaml. / Load security settings from config/prod/rules.yaml. **/"""
    try:
        # English: centralized rules config source. / Español: fuente centralizada de reglas.
        payload = load_config("rules.yaml", env="prod")
    except ValueError:
        return {}
    if isinstance(payload, dict):
        return payload.get("security", {}) if isinstance(payload.get("security"), dict) else {}
    return {}


def _ensure_decrypted_private_key() -> None:
    """/** Desencripta private key sólo si falta. / Decrypt private key only when missing. **/"""
    security = _load_security_settings()
    if not security.get("encrypt_enabled", False):
        return
    if os.getenv("ARBITRUM_PRIVATE_KEY"):
        return
    try:
        decrypted = decrypt_secrets(keys=["ARBITRUM_PRIVATE_KEY"])
    except ValueError:
        log_event(logger, logging.ERROR, "auto_anchor_decrypt_failed")
        return
    private_key = decrypted.get("ARBITRUM_PRIVATE_KEY")
    if private_key:
        # Seguridad: mantener secreto en memoria/env sin escribir en disco. / Security: keep secret in memory/env only.
        os.environ["ARBITRUM_PRIVATE_KEY"] = private_key


def main() -> None:
    """/** CLI simple para anclaje manual. / Simple CLI for manual anchoring. **/"""
    parser = argparse.ArgumentParser(description="Auto-anchor manual para C.E.N.T.I.N.E.L.")
    parser.add_argument("--root-hash", help="Hash raíz a anclar (hex)")
    parser.add_argument("--hashes-json", help="Archivo JSON con lista de hashes")
    args = parser.parse_args()

    _ensure_decrypted_private_key()

    if args.root_hash:
        result = anchor_root(args.root_hash)
        log_event(
            logger,
            logging.INFO,
            "auto_anchor_root_complete",
            anchor_id=result.get("anchor_id"),
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    if args.hashes_json:
        hashes = json.loads(Path(args.hashes_json).read_text(encoding="utf-8"))
        if not isinstance(hashes, list):
            raise ValueError("hashes-json must contain a list")
        result = anchor_batch([str(item) for item in hashes])
        log_event(
            logger,
            logging.INFO,
            "auto_anchor_batch_complete",
            batch_id=result.get("batch_id"),
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    parser.error("Provide --root-hash or --hashes-json")


if __name__ == "__main__":
    main()
