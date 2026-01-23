"""Snapshot manager for capturing, hashing, and anchoring data."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.sentinel.core.normalize import normalize_snapshot, snapshot_to_dict
from src.sentinel.core.storage import LocalSnapshotStore

from ..datasources.base import DataSource, SourceData
from ..utils.hashing import compute_hash
from .blockchain_anchor import BlockchainAnchor
from .integrity_engine import IntegrityEngine, IntegrityReport

logger = logging.getLogger(__name__)


@dataclass
class SnapshotResult:
    """Snapshot processing result for a single source."""

    source: SourceData
    snapshot_hash: str
    chain_hash: str
    integrity: IntegrityReport


class SnapshotManager:
    """Orchestrates snapshot capture, hashing, and anchoring."""

    def __init__(
        self,
        datasource: DataSource,
        store: LocalSnapshotStore,
        anchor: BlockchainAnchor,
        integrity_engine: IntegrityEngine,
        field_map: Dict[str, Any],
        hash_chain_path: Optional[str] = None,
    ) -> None:
        self.datasource = datasource
        self.store = store
        self.anchor = anchor
        self.integrity_engine = integrity_engine
        self.field_map = field_map
        self.hash_chain_path = hash_chain_path

    def take_snapshot(self) -> List[SnapshotResult]:
        payloads = self.datasource.fetch_current_data()
        results: List[SnapshotResult] = []
        for payload in payloads:
            snapshot = normalize_snapshot(
                raw=payload.raw_data,
                department_name=payload.name,
                timestamp_utc=payload.fetched_at_utc,
                scope=payload.scope,
                department_code=payload.department_code,
                field_map=self.field_map,
            )
            previous_hash = self._latest_hash(payload.department_code)
            snapshot_hash = self.store.store_snapshot(snapshot, previous_hash)
            chain_hash = compute_hash(snapshot_hash, previous_hash=previous_hash)
            integrity = self.integrity_engine.evaluate(
                current_data=snapshot_to_dict(snapshot),
                previous_data=self._load_previous_snapshot(payload.department_code),
            )
            results.append(
                SnapshotResult(
                    source=payload,
                    snapshot_hash=snapshot_hash,
                    chain_hash=chain_hash,
                    integrity=integrity,
                )
            )

        return results

    def compute_root_hash(self, snapshot_hashes: List[str]) -> str:
        """Compute a root hash from a list of snapshot hashes."""
        payload = json.dumps(snapshot_hashes, sort_keys=True)
        return compute_hash(payload)

    def anchor_to_blockchain(self, root_hash: str) -> str:
        """Anchor the root hash on-chain."""
        return self.anchor.anchor_hash(root_hash)

    def store_snapshot(self, snapshot_hashes: List[str], root_hash: str) -> None:
        """Persist root hash tracking to disk."""
        if not self.hash_chain_path:
            return
        path = Path(self.hash_chain_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "root_hash": root_hash,
            "snapshot_hashes": snapshot_hashes,
        }
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry) + "\n")

    def _latest_hash(self, department_code: str) -> Optional[str]:
        entries = self.store.get_index_entries(department_code)
        if not entries:
            return None
        return entries[-1].get("hash")

    def _load_previous_snapshot(self, department_code: str) -> Optional[Dict[str, Any]]:
        rows = self.store._fetch_department_rows(department_code)
        if not rows:
            return None
        last = rows[-1]
        canonical_json = last["canonical_json"]
        if not canonical_json:
            return None
        try:
            return json.loads(canonical_json)
        except json.JSONDecodeError:
            return None
