"""
Supabase sync — pushes snapshot records and alerts to the external public DB.

Failures are always non-fatal: local SQLite remains the source of truth.
The Supabase DB is used for the public panel and UPNFM sandbox only.
"""

from __future__ import annotations

import base64
import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_client: Optional[Any] = None


def _get_client() -> Optional[Any]:
    global _client
    if _client is not None:
        return _client

    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_KEY", "")
    if not url or not key or url.startswith("https://PROYECTO"):
        return None

    try:
        from supabase import create_client
        _client = create_client(url, key)
        return _client
    except ImportError:
        logger.warning("supabase_sync: supabase-py not installed, skipping sync")
        return None
    except Exception as exc:
        logger.warning("supabase_sync: could not create client", error=str(exc))
        return None


def push_snapshot(
    captured_at: str,
    chain_hash: str,
    merkle_root: str,
    chain_length: int = 0,
    dept_code: Optional[str] = None,
    ots_proof_b64: Optional[str] = None,
    anomaly_flag: bool = False,
    alert_state: str = "normal",
    raw_meta: Optional[Dict] = None,
) -> Optional[int]:
    """
    Insert a snapshot record into snapshots_public.

    Returns the new row id on success, None on failure.
    Always non-fatal.
    """
    client = _get_client()
    if client is None:
        return None

    try:
        row = {
            "captured_at": captured_at,
            "chain_hash": chain_hash,
            "merkle_root": merkle_root,
            "chain_length": chain_length,
            "anomaly_flag": anomaly_flag,
            "alert_state": alert_state,
        }
        if dept_code:
            row["dept_code"] = dept_code
        if ots_proof_b64:
            row["ots_proof"] = ots_proof_b64
        if raw_meta:
            row["raw_meta"] = raw_meta

        result = client.table("snapshots_public").insert(row).execute()
        if result.data:
            inserted_id = result.data[0].get("id")
            logger.info("supabase_snapshot_pushed", id=inserted_id, hash=chain_hash[:16])
            return inserted_id
    except Exception as exc:
        logger.warning("supabase_snapshot_push_failed", error=str(exc))
    return None


def push_alert(
    created_at: str,
    severity: str,
    description: str,
    rule_id: Optional[str] = None,
    kind: Optional[str] = None,
    dept_code: Optional[str] = None,
    snapshot_id: Optional[int] = None,
) -> Optional[int]:
    """
    Insert an alert record into alerts_public.

    Returns the new row id on success, None on failure.
    Always non-fatal.
    """
    client = _get_client()
    if client is None:
        return None

    try:
        row: Dict[str, Any] = {
            "created_at": created_at,
            "severity": severity,
            "description": description,
        }
        if rule_id:
            row["rule_id"] = rule_id
        if kind:
            row["kind"] = kind
        if dept_code:
            row["dept_code"] = dept_code
        if snapshot_id:
            row["snapshot_id"] = snapshot_id

        result = client.table("alerts_public").insert(row).execute()
        if result.data:
            inserted_id = result.data[0].get("id")
            logger.info("supabase_alert_pushed", id=inserted_id, severity=severity)
            return inserted_id
    except Exception as exc:
        logger.warning("supabase_alert_push_failed", error=str(exc))
    return None


def update_ots_proof(snapshot_id: int, ots_proof_b64: str, bitcoin_tx: Optional[str] = None) -> bool:
    """
    Update the OTS proof and optional Bitcoin tx for an existing snapshot.

    Returns True on success, False on failure.
    """
    client = _get_client()
    if client is None:
        return False

    try:
        update = {"ots_proof": ots_proof_b64}
        if bitcoin_tx:
            update["bitcoin_tx"] = bitcoin_tx
        client.table("snapshots_public").update(update).eq("id", snapshot_id).execute()
        logger.info("supabase_ots_updated", snapshot_id=snapshot_id)
        return True
    except Exception as exc:
        logger.warning("supabase_ots_update_failed", error=str(exc))
        return False


def is_configured() -> bool:
    """Return True if Supabase credentials are set and client can connect."""
    return _get_client() is not None
