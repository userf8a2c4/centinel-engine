"""Blockchain anchoring abstraction."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from web3 import Web3

logger = logging.getLogger(__name__)


class BlockchainAnchor(ABC):
    """Abstract base class for blockchain anchoring."""

    @abstractmethod
    def anchor_hash(self, root_hash: str) -> str:
        """Anchor a hash on-chain and return the transaction hash."""

    @abstractmethod
    def verify_anchor(self, tx_hash: str, expected_hash: str) -> bool:
        """Verify that the transaction contains the expected hash."""


@dataclass
class ArbitrumConfig:
    """Configuration for Arbitrum anchoring."""

    rpc_url: str
    private_key: str
    contract_address: str
    chain_id: int = 42161


class ArbitrumAnchor(BlockchainAnchor):
    """Anchor hashes on Arbitrum L2."""

    def __init__(self, config: ArbitrumConfig) -> None:
        self.config = config
        self.web3 = Web3(Web3.HTTPProvider(config.rpc_url))
        if not self.web3.is_connected():
            raise ConnectionError("Unable to connect to Arbitrum RPC")

    def anchor_hash(self, root_hash: str) -> str:
        account = self.web3.eth.account.from_key(self.config.private_key)
        nonce = self.web3.eth.get_transaction_count(account.address)
        payload = Web3.to_bytes(hexstr=root_hash)
        tx = {
            "from": account.address,
            "to": self.config.contract_address or account.address,
            "value": 0,
            "nonce": nonce,
            "chainId": self.config.chain_id,
            "data": payload,
        }
        tx["gas"] = self.web3.eth.estimate_gas(tx)
        tx["gasPrice"] = self.web3.eth.gas_price
        signed = account.sign_transaction(tx)
        tx_hash = self.web3.eth.send_raw_transaction(signed.rawTransaction)
        return self.web3.to_hex(tx_hash)

    def verify_anchor(self, tx_hash: str, expected_hash: str) -> bool:
        receipt = self.web3.eth.get_transaction(tx_hash)
        if receipt is None:
            return False
        input_data = receipt.get("input")
        if not input_data:
            return False
        expected = Web3.to_hex(Web3.to_bytes(hexstr=expected_hash))
        return input_data.lower() == expected.lower()


class NullAnchor(BlockchainAnchor):
    """No-op blockchain anchor when disabled."""

    def anchor_hash(self, root_hash: str) -> str:
        logger.info("blockchain_anchor_disabled")
        return ""

    def verify_anchor(self, tx_hash: str, expected_hash: str) -> bool:
        return False
