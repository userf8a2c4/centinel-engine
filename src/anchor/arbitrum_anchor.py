"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `src/anchor/arbitrum_anchor.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - _keccak256
  - _normalize_hash
  - _build_merkle_root
  - _load_arbitrum_settings
  - _resolve_private_key
  - _obfuscate_identifier
  - _log_anchor_start
  - _log_anchor_sent
  - _build_web3_client
  - _build_anchor_transaction
  - _send_anchor_transaction
  - anchor_root
  - anchor_batch

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `src/anchor/arbitrum_anchor.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - _keccak256
  - _normalize_hash
  - _build_merkle_root
  - _load_arbitrum_settings
  - _resolve_private_key
  - _obfuscate_identifier
  - _log_anchor_start
  - _log_anchor_sent
  - _build_web3_client
  - _build_anchor_transaction
  - _send_anchor_transaction
  - anchor_root
  - anchor_batch

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
"""

# Arbitrum Anchor Module
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



from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import uuid4

from eth_account import Account
from eth_utils import keccak
from web3 import Web3

from centinel.utils.config_loader import load_config

logger = logging.getLogger(__name__)

CENTINEL_ANCHOR_ABI = [
    {
        "inputs": [{"internalType": "bytes32", "name": "root", "type": "bytes32"}],
        "name": "anchor",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "anonymous": False,
        "inputs": [
            {
                "indexed": True,
                "internalType": "bytes32",
                "name": "root",
                "type": "bytes32",
            },
            {
                "indexed": False,
                "internalType": "uint256",
                "name": "timestamp",
                "type": "uint256",
            },
        ],
        "name": "HashRootAnchored",
        "type": "event",
    },
]


def _keccak256(data: bytes) -> bytes:
    """Calcula keccak256 sobre bytes.

    :param data: Bytes de entrada.
    :return: Digest keccak256 en bytes.

    English:
        Computes keccak256 on bytes.

    :param data: Input bytes.
    :return: keccak256 digest bytes.
    """
    return keccak(data)


def _normalize_hash(hex_hash: str) -> bytes:
    """Valida y normaliza un hash hex de 32 bytes.

    :param hex_hash: Hash SHA-256 en formato hex (con o sin 0x).
    :return: Hash en bytes con longitud 32.

    English:
        Validates and normalizes a 32-byte hex hash.

    :param hex_hash: SHA-256 hash in hex format (with or without 0x).
    :return: Hash bytes with length 32.
    """
    cleaned = hex_hash.lower().replace("0x", "")
    if len(cleaned) != 64:
        raise ValueError("Hash inválido: se esperaban 32 bytes en hex.")
    try:
        return bytes.fromhex(cleaned)
    except ValueError as exc:
        raise ValueError("Hash inválido: formato hex incorrecto.") from exc


def _build_merkle_root(hashes: List[str]) -> str:
    """Construye el Merkle Root con keccak256 usando un árbol simple.

    :param hashes: Lista de hashes SHA-256 en hex.
    :return: Merkle Root como hex string con prefijo 0x.

    English:
        Builds a Merkle Root with keccak256 using a simple tree.

    :param hashes: List of SHA-256 hashes in hex.
    :return: Merkle Root as a hex string with 0x prefix.
    """
    if not hashes:
        raise ValueError("La lista de hashes está vacía.")

    leaves = [_keccak256(_normalize_hash(hash_value)) for hash_value in hashes]
    logger.debug("merkle_leaves_count=%s", len(leaves))

    level = leaves
    while len(level) > 1:
        next_level: list[bytes] = []
        for index in range(0, len(level), 2):
            left = level[index]
            right = level[index + 1] if index + 1 < len(level) else left
            next_level.append(_keccak256(left + right))
        level = next_level
        logger.debug("merkle_level_size=%s", len(level))

    return f"0x{level[0].hex()}"


def _load_arbitrum_settings() -> dict[str, Any]:
    """Carga la configuración de Arbitrum desde command_center/config.yaml.

    :return: Diccionario con configuración de Arbitrum.

    English:
        Loads Arbitrum configuration from command_center/config.yaml.

    :return: Dictionary with Arbitrum configuration.
    """
    config = load_config()
    return config.get("arbitrum", {})


def _resolve_private_key(settings: dict[str, Any]) -> str | None:
    """Resolve private key exclusively from environment variables.

    YAML config values are intentionally ignored to prevent accidental
    secret leakage in version-controlled files.

    Resuelve la private key exclusivamente desde variables de entorno.
    Los valores en YAML se ignoran intencionalmente para prevenir fuga
    accidental de secretos en archivos versionados.
    """
    env_key = os.getenv("ARBITRUM_PRIVATE_KEY", "").strip()
    if not env_key:
        yaml_value = settings.get("private_key")
        if yaml_value and yaml_value not in {"", "0x...", "REPLACE_ME"}:
            logger.warning("private_key found in config.yaml but ignored — " "set ARBITRUM_PRIVATE_KEY env var instead")
        return None
    return env_key


def _obfuscate_identifier(value: str) -> str:
    """Return shortened identifier for logs without exposing full values.

    Devuelve identificador acortado para logs sin exponer valores completos.
    """
    if len(value) <= 10:
        return value
    return f"{value[:6]}…{value[-4:]}"


def _log_anchor_start(settings: dict[str, Any], anchor_id: str, root_hex: str) -> None:
    privacy_mode = bool(settings.get("log_redact_identifiers", False))
    if privacy_mode:
        logger.info(
            "anchor_root_start anchor_id=%s root=%s", _obfuscate_identifier(anchor_id), _obfuscate_identifier(root_hex)
        )
        return
    logger.info("anchor_root_start anchor_id=%s root=%s", anchor_id, root_hex)


def _log_anchor_sent(
    settings: dict[str, Any],
    *,
    anchor_id: str,
    tx_hash_hex: str,
    root_hex: str,
    checksum_address: str,
) -> None:
    privacy_mode = bool(settings.get("log_redact_identifiers", False))
    if privacy_mode:
        logger.info(
            "anchor_root_sent anchor_id=%s tx_hash=%s root=%s contract=%s",
            _obfuscate_identifier(anchor_id),
            _obfuscate_identifier(tx_hash_hex),
            _obfuscate_identifier(root_hex),
            _obfuscate_identifier(checksum_address),
        )
        return
    logger.info(
        "anchor_root_sent anchor_id=%s tx_hash=%s root=%s contract=%s",
        anchor_id,
        tx_hash_hex,
        root_hex,
        checksum_address,
    )


def _build_web3_client(rpc_url: str) -> Web3:
    """Construye un cliente Web3 conectado al RPC.

    :param rpc_url: URL RPC de Arbitrum.
    :return: Instancia Web3 conectada.

    English:
        Builds a Web3 client connected to the RPC.

    :param rpc_url: Arbitrum RPC URL.
    :return: Connected Web3 instance.
    """
    web3 = Web3(Web3.HTTPProvider(rpc_url))
    if not web3.is_connected():
        raise ConnectionError("No se pudo conectar al RPC de Arbitrum.")
    return web3


def _build_anchor_transaction(
    web3: Web3,
    contract_address: str,
    private_key: str,
    root_bytes: bytes,
) -> tuple[dict[str, Any], str]:
    """Construye y firma la transacción para anclaje.

    :param web3: Cliente Web3 inicializado.
    :param contract_address: Dirección del contrato.
    :param private_key: Llave privada para firmar.
    :param root_bytes: Hash raíz en bytes (32 bytes).
    :return: Tupla (tx dict, address checksum).

    English:
        Builds and signs the anchoring transaction.

    :param web3: Initialized Web3 client.
    :param contract_address: Contract address.
    :param private_key: Private key used to sign.
    :param root_bytes: Root hash in bytes (32 bytes).
    :return: Tuple (tx dict, checksum address).
    """
    checksum_address = web3.to_checksum_address(contract_address)
    contract = web3.eth.contract(address=checksum_address, abi=CENTINEL_ANCHOR_ABI)

    account = Account.from_key(private_key)
    nonce = web3.eth.get_transaction_count(account.address)

    tx = contract.functions.anchor(root_bytes).build_transaction(
        {
            "from": account.address,
            "nonce": nonce,
            "chainId": web3.eth.chain_id,
            "gasPrice": web3.eth.gas_price,
        }
    )
    tx["gas"] = contract.functions.anchor(root_bytes).estimate_gas({"from": account.address})
    return tx, checksum_address


def _send_anchor_transaction(
    web3: Web3,
    tx: dict[str, Any],
    private_key: str,
) -> str:
    """Firma y envía una transacción de anclaje.

    :param web3: Cliente Web3 inicializado.
    :param tx: Transacción construida.
    :param private_key: Llave privada para firmar.
    :return: Hash de transacción en hex string.

    English:
        Signs and sends an anchor transaction.

    :param web3: Initialized Web3 client.
    :param tx: Built transaction.
    :param private_key: Private key used to sign.
    :return: Transaction hash as hex string.
    """
    signed = Account.sign_transaction(tx, private_key)
    raw_tx = getattr(signed, "rawTransaction", None) or signed.raw_transaction
    tx_hash = web3.eth.send_raw_transaction(raw_tx)
    return web3.to_hex(tx_hash)


def anchor_root(root_hash: str) -> Dict[str, Any]:
    """Ancla un hash raíz directo en Arbitrum One.

    :param root_hash: Hash SHA-256 en formato hex string (32 bytes).
    :return: Dict con 'tx_hash', 'root', 'timestamp', 'anchor_id'.

    English:
        Anchors a root hash directly on Arbitrum One.

    :param root_hash: SHA-256 hash in hex string format (32 bytes).
    :return: Dict with 'tx_hash', 'root', 'timestamp', 'anchor_id'.
    """
    settings = _load_arbitrum_settings()
    if not settings.get("enabled", False):
        raise ValueError("Arbitrum anchoring está deshabilitado en config.")

    rpc_url = settings.get("rpc_url")
    private_key = _resolve_private_key(settings)
    contract_address = settings.get("contract_address")

    if not rpc_url or not contract_address:
        raise ValueError("Configuración incompleta de Arbitrum en command_center/config.yaml.")
    if not private_key:
        raise ValueError("Missing private key for Arbitrum anchoring.")

    anchor_id = uuid4().hex
    timestamp = datetime.now(timezone.utc).isoformat()
    root_bytes = _normalize_hash(root_hash)
    root_hex = f"0x{root_bytes.hex()}"
    _log_anchor_start(settings, anchor_id, root_hex)

    web3 = _build_web3_client(rpc_url)
    tx, checksum_address = _build_anchor_transaction(
        web3=web3,
        contract_address=contract_address,
        private_key=private_key,
        root_bytes=root_bytes,
    )
    tx_hash_hex = _send_anchor_transaction(web3=web3, tx=tx, private_key=private_key)

    _log_anchor_sent(
        settings,
        anchor_id=anchor_id,
        tx_hash_hex=tx_hash_hex,
        root_hex=root_hex,
        checksum_address=checksum_address,
    )

    return {
        "tx_hash": tx_hash_hex,
        "root": root_hex,
        "timestamp": timestamp,
        "anchor_id": anchor_id,
    }


def anchor_batch(hashes: List[str]) -> Dict[str, Any]:
    """Envía un batch de hashes a Arbitrum One usando Merkle root.

    :param hashes: Lista de hashes SHA-256 en formato hex string.
    :return: Dict con 'tx_hash', 'root', 'timestamp', 'batch_id'.

    English:
        Sends a batch of hashes to Arbitrum One using a Merkle root.

    :param hashes: List of SHA-256 hashes in hex string format.
    :return: Dict with 'tx_hash', 'root', 'timestamp', 'batch_id'.
    """
    settings = _load_arbitrum_settings()
    if not settings.get("enabled", False):
        raise ValueError("Arbitrum anchoring está deshabilitado en config.")

    rpc_url = settings.get("rpc_url")
    private_key = _resolve_private_key(settings)
    contract_address = settings.get("contract_address")

    missing_configs = []
    if not rpc_url:
        missing_configs.append("rpc_url")
    if not contract_address:
        missing_configs.append("contract_address")

    if missing_configs:
        raise ValueError(
            f"Configuración incompleta de Arbitrum: falta {', '.join(missing_configs)} en command_center/config.yaml."
        )
    if not private_key:
        raise ValueError("Missing private key for Arbitrum anchoring.")

    batch_id = uuid4().hex
    timestamp = datetime.now(timezone.utc).isoformat()
    root = _build_merkle_root(hashes)
    if settings.get("log_redact_identifiers", False):
        logger.info(
            "anchor_batch_start batch_id=%s root=%s",
            _obfuscate_identifier(batch_id),
            _obfuscate_identifier(root),
        )
    else:
        logger.info("anchor_batch_start batch_id=%s root=%s", batch_id, root)

    web3 = _build_web3_client(rpc_url)
    root_bytes = web3.to_bytes(hexstr=root)
    tx, _ = _build_anchor_transaction(
        web3=web3,
        contract_address=contract_address,
        private_key=private_key,
        root_bytes=root_bytes,
    )
    tx_hash_hex = _send_anchor_transaction(web3=web3, tx=tx, private_key=private_key)

    if settings.get("log_redact_identifiers", False):
        logger.info(
            "anchor_batch_sent batch_id=%s tx_hash=%s root=%s",
            _obfuscate_identifier(batch_id),
            _obfuscate_identifier(tx_hash_hex),
            _obfuscate_identifier(root),
        )
    else:
        logger.info("anchor_batch_sent batch_id=%s tx_hash=%s root=%s", batch_id, tx_hash_hex, root)

    return {
        "tx_hash": tx_hash_hex,
        "root": root,
        "timestamp": timestamp,
        "batch_id": batch_id,
    }
