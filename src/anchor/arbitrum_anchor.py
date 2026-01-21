"""Anclaje de hashes en Arbitrum One usando Merkle Trees.

English:
    Hash anchoring on Arbitrum One using Merkle Trees.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import uuid4

from Crypto.Hash import keccak
from eth_account import Account
from web3 import Web3

from sentinel.utils.config_loader import load_config

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
    digest = keccak.new(digest_bits=256)
    digest.update(data)
    return digest.digest()


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
    """Carga la configuración de Arbitrum desde config/config.yaml.

    :return: Diccionario con configuración de Arbitrum.

    English:
        Loads Arbitrum configuration from config/config.yaml.

    :return: Dictionary with Arbitrum configuration.
    """
    config = load_config()
    return config.get("arbitrum", {})


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
    private_key = settings.get("private_key")
    contract_address = settings.get("contract_address")

    if not rpc_url or not private_key or not contract_address:
        raise ValueError("Configuración incompleta de Arbitrum en config/config.yaml.")

    batch_id = uuid4().hex
    timestamp = datetime.now(timezone.utc).isoformat()
    root = _build_merkle_root(hashes)
    logger.info("anchor_batch_start batch_id=%s root=%s", batch_id, root)

    web3 = _build_web3_client(rpc_url)
    checksum_address = web3.to_checksum_address(contract_address)
    contract = web3.eth.contract(address=checksum_address, abi=CENTINEL_ANCHOR_ABI)

    account = Account.from_key(private_key)
    nonce = web3.eth.get_transaction_count(account.address)
    root_bytes = web3.to_bytes(hexstr=root)

    tx = contract.functions.anchor(root_bytes).build_transaction(
        {
            "from": account.address,
            "nonce": nonce,
            "chainId": web3.eth.chain_id,
            "gasPrice": web3.eth.gas_price,
        }
    )
    tx["gas"] = contract.functions.anchor(root_bytes).estimate_gas(
        {"from": account.address}
    )

    signed = Account.sign_transaction(tx, private_key)
    raw_tx = getattr(signed, "rawTransaction", None) or signed.raw_transaction
    tx_hash = web3.eth.send_raw_transaction(raw_tx)
    tx_hash_hex = web3.to_hex(tx_hash)

    logger.info(
        "anchor_batch_sent batch_id=%s tx_hash=%s root=%s", batch_id, tx_hash_hex, root
    )

    return {
        "tx_hash": tx_hash_hex,
        "root": root,
        "timestamp": timestamp,
        "batch_id": batch_id,
    }
