"""CLI entry point for snapshot execution."""

from __future__ import annotations

import argparse
import logging
import time

from src.sentinel.core.storage import LocalSnapshotStore

from src.core.blockchain_anchor import ArbitrumAnchor, ArbitrumConfig, NullAnchor
from src.core.integrity_engine import IntegrityEngine
from src.core.snapshot_manager import SnapshotManager
from src.datasources.honduras_json import HondurasJsonDataSource
from src.utils.config import load_config
from src.utils.logging import configure_logging

logger = logging.getLogger(__name__)


def build_anchor(config: dict) -> object:
    blockchain_cfg = config.get("blockchain", {})
    if not blockchain_cfg.get("enabled", False):
        return NullAnchor()

    anchor_config = ArbitrumConfig(
        rpc_url=blockchain_cfg.get("rpc_url"),
        private_key=blockchain_cfg.get("private_key"),
        contract_address=blockchain_cfg.get("contract_address"),
        chain_id=int(blockchain_cfg.get("chain_id", 42161)),
    )
    return ArbitrumAnchor(anchor_config)


def main() -> None:
    parser = argparse.ArgumentParser(description="C.E.N.T.I.N.E.L. Snapshot Runner")
    parser.add_argument("--country", default="HN", help="ISO country code")
    args = parser.parse_args()

    config = load_config(args.country)
    configure_logging(level="INFO")

    datasource_cfg = config.get("datasource", {})
    datasource_type = datasource_cfg.get("type", "honduras_json")
    datasource_registry = {
        "honduras_json": HondurasJsonDataSource,
        "json_api": HondurasJsonDataSource,
    }
    datasource_cls = datasource_registry.get(datasource_type, HondurasJsonDataSource)
    datasource = datasource_cls(datasource_cfg)

    store_path = config["storage"]["sqlite_path"]
    store = LocalSnapshotStore(store_path)
    anchor = build_anchor(config)
    integrity_engine = IntegrityEngine(config.get("integrity_rules", []))

    manager = SnapshotManager(
        datasource=datasource,
        store=store,
        anchor=anchor,
        integrity_engine=integrity_engine,
        field_map=datasource_cfg.get("field_map", {}),
        hash_chain_path=config["storage"].get("hash_chain_path"),
    )

    interval = int(config.get("snapshot_interval_minutes", 10)) * 60
    logger.info("starting snapshot loop interval=%s", interval)

    try:
        while True:
            results = manager.take_snapshot()
            snapshot_hashes = [result.snapshot_hash for result in results]
            root_hash = manager.compute_root_hash(snapshot_hashes)
            tx_hash = manager.anchor_to_blockchain(root_hash)
            manager.store_snapshot(snapshot_hashes, root_hash)
            logger.info(
                "snapshot_batch completed count=%s root_hash=%s tx_hash=%s",
                len(results),
                root_hash,
                tx_hash,
            )
            time.sleep(interval)
    except KeyboardInterrupt:
        logger.info("snapshot loop stopped")
    finally:
        store.close()


if __name__ == "__main__":
    main()
