"""Publicación de hashes en blockchain y configuración asociada.

English:
    Hash publication to blockchain with configuration helpers.
"""

from __future__ import annotations

import logging
import os
from typing import Any, TYPE_CHECKING, Dict

import yaml

if TYPE_CHECKING:
    from web3 import Web3

logger = logging.getLogger(__name__)

DEFAULT_NETWORKS = {
    "polygon-mumbai": {
        "chain_id": 80001,
        "default_rpc": "https://rpc-mumbai.maticvigil.com",
        "rpc_env": "POLYGON_MUMBAI_RPC_URL",
    }
}


def load_blockchain_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """Carga configuración blockchain desde YAML.

    Args:
        config_path (str): Ruta del archivo YAML.

    Returns:
        Dict[str, Any]: Configuración blockchain encontrada.

    English:
        Loads blockchain configuration from YAML.

    Args:
        config_path (str): YAML file path.

    Returns:
        Dict[str, Any]: Loaded blockchain configuration.
    """
    if not os.path.exists(config_path):
        return {}
    with open(config_path, "r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}
    return config.get("blockchain", {}) or {}


def resolve_private_key(raw_value: str | None) -> str | None:
    """Resuelve la clave privada desde valor directo o env var.

    Args:
        raw_value (str | None): Valor crudo en config.

    Returns:
        str | None: Clave privada resuelta o None.

    English:
        Resolves the private key from raw config or env var.

    Args:
        raw_value (str | None): Raw value from config.

    Returns:
        str | None: Resolved private key or None.
    """
    if raw_value is None:
        return os.getenv("PRIVATE_KEY")
    value = str(raw_value).strip()
    if value.startswith("${") and value.endswith("}"):
        env_key = value[2:-1]
        return os.getenv(env_key)
    return value or None


def is_blockchain_enabled(config: Dict[str, Any]) -> bool:
    """Indica si la publicación en blockchain está habilitada.

    Args:
        config (Dict[str, Any]): Configuración blockchain.

    Returns:
        bool: True si está habilitado.

    English:
        Indicates whether blockchain publishing is enabled.

    Args:
        config (Dict[str, Any]): Blockchain configuration.

    Returns:
        bool: True when enabled.
    """
    return bool(config.get("enabled", False))


def resolve_rpc_url(config: Dict[str, Any]) -> str:
    """Resuelve la URL RPC para la red configurada.

    Args:
        config (Dict[str, Any]): Configuración blockchain.

    Returns:
        str: URL RPC.

    English:
        Resolves the RPC URL for the configured network.

    Args:
        config (Dict[str, Any]): Blockchain configuration.

    Returns:
        str: RPC URL.
    """
    network_name = str(config.get("network", "polygon-mumbai")).lower()
    network = DEFAULT_NETWORKS.get(network_name, {})
    env_override = os.getenv("WEB3_PROVIDER_URL")
    if env_override:
        return env_override
    rpc_env = network.get("rpc_env")
    if rpc_env and os.getenv(rpc_env):
        return os.getenv(rpc_env) or ""
    return network.get("default_rpc", "")


def _build_web3_client(config: Dict[str, Any]) -> tuple["Web3", int]:
    """Construye un cliente Web3 y devuelve el chain_id.

    Args:
        config (Dict[str, Any]): Configuración blockchain.

    Returns:
        tuple[Web3, int]: Cliente Web3 y chain_id configurado.

    English:
        Builds a Web3 client and returns chain_id.

    Args:
        config (Dict[str, Any]): Blockchain configuration.

    Returns:
        tuple[Web3, int]: Web3 client and configured chain_id.
    """
    rpc_url = resolve_rpc_url(config)
    if not rpc_url:
        raise ValueError("Missing RPC URL for blockchain publishing.")

    network_name = str(config.get("network", "polygon-mumbai")).lower()
    chain_id = DEFAULT_NETWORKS.get(network_name, {}).get("chain_id")
    if chain_id is None:
        raise ValueError(f"Unsupported network: {network_name}")

    from web3 import Web3

    web3 = Web3(Web3.HTTPProvider(rpc_url))
    if not web3.is_connected():
        raise ConnectionError("Unable to connect to blockchain provider.")
    return web3, chain_id


def _send_payload_to_chain(
    web3: "Web3", chain_id: int, private_key: str, payload: bytes
) -> str:
    """Envía un payload en una transacción y devuelve el tx hash.

    Args:
        web3 (Web3): Cliente Web3 conectado.
        chain_id (int): Chain ID de la red.
        private_key (str): Clave privada para firmar.
        payload (bytes): Datos a publicar.

    Returns:
        str: Hash de la transacción.

    English:
        Sends a payload in a transaction and returns the tx hash.

    Args:
        web3 (Web3): Connected Web3 client.
        chain_id (int): Network chain ID.
        private_key (str): Private key to sign.
        payload (bytes): Data to publish.

    Returns:
        str: Transaction hash.
    """
    account = web3.eth.account.from_key(private_key)
    nonce = web3.eth.get_transaction_count(account.address)
    tx = {
        "from": account.address,
        "to": account.address,
        "value": 0,
        "nonce": nonce,
        "chainId": chain_id,
        "data": payload,
    }
    tx["gas"] = web3.eth.estimate_gas(tx)
    tx["gasPrice"] = web3.eth.gas_price
    signed = account.sign_transaction(tx)
    tx_hash = web3.eth.send_raw_transaction(signed.rawTransaction)
    return web3.to_hex(tx_hash)


def publish_hash_to_chain(current_chain_hash: str) -> str:
    """Publica un hash en la blockchain y devuelve el tx hash.

    Args:
        current_chain_hash (str): Hash encadenado actual.

    Returns:
        str: Hash de la transacción en blockchain (vacío si no se publica).

    English:
        Publishes a hash to the blockchain and returns the tx hash.

    Args:
        current_chain_hash (str): Current chained hash.

    Returns:
        str: Blockchain transaction hash (empty if not published).
    """
    config = load_blockchain_config()
    if not is_blockchain_enabled(config):
        logger.debug("blockchain_disabled")
        return ""

    private_key = resolve_private_key(config.get("private_key"))
    if not private_key:
        raise ValueError("Missing private key for blockchain publishing.")

    web3, chain_id = _build_web3_client(config)
    from web3 import Web3

    payload = Web3.to_bytes(hexstr=current_chain_hash)
    return _send_payload_to_chain(web3, chain_id, private_key, payload)


def publish_cid_to_chain(cid: str) -> str:
    """Publica un CID de IPFS en la blockchain y devuelve el tx hash.

    Args:
        cid (str): CID publicado en IPFS.

    Returns:
        str: Hash de la transacción en blockchain (vacío si no se publica).

    English:
        Publishes an IPFS CID to the blockchain and returns the tx hash.

    Args:
        cid (str): IPFS CID.

    Returns:
        str: Blockchain transaction hash (empty if not published).
    """
    config = load_blockchain_config()
    if not is_blockchain_enabled(config):
        logger.debug("blockchain_disabled")
        return ""

    private_key = resolve_private_key(config.get("private_key"))
    if not private_key:
        raise ValueError("Missing private key for blockchain publishing.")

    web3, chain_id = _build_web3_client(config)
    from web3 import Web3

    payload = Web3.to_bytes(text=cid)
    return _send_payload_to_chain(web3, chain_id, private_key, payload)
