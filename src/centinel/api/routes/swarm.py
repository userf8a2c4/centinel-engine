"""
Swarm API endpoints for Centinel gossip network.

Provides:
  GET  /api/checkpoint    — This node's signed attestation (for peers to pull)
  POST /api/swarm/attest  — Receive a NodePayload from a peer
  GET  /api/swarm/status  — Swarm connection state and peer table
  POST /api/swarm/connect — Start the GossipEngine (idempotent)
  POST /api/swarm/disconnect — Stop the GossipEngine
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from centinel.federation.gossip import GossipEngine
from centinel.federation.findings_log import FederationAnomalyLog
from centinel.federation.attack_log import FederationAttackLog
from centinel.api.rate_limit import RateLimiter, RateLimitConfig

logger = logging.getLogger("centinel.api.swarm")

router = APIRouter(tags=["swarm"])

_BASE = Path(__file__).resolve().parents[4]
_SETUP_MARKER = _BASE / ".centinel-setup.json"

# Rate limiters for gossip endpoints (independent of the global API limiter)
# Gossip nodes legitimately send 1 attestation/60s — 200/min = 200× headroom
_attest_limiter = RateLimiter(RateLimitConfig(limit=200, window_seconds=60))
# Peers send up to 10 findings/min — 100/min = 10× headroom against abuse
_finding_limiter = RateLimiter(RateLimitConfig(limit=100, window_seconds=60))

_engine: Optional[GossipEngine] = None
_engine_task: Optional[asyncio.Task] = None

# Federation finding logs — instantiated once, shared across engine restarts
_anomaly_log = FederationAnomalyLog(
    max_findings=500,
    log_path=_BASE / "logs" / "federation_anomalies.jsonl",
)
_attack_log = FederationAttackLog(
    max_findings=300,
    log_path=_BASE / "logs" / "federation_attacks.jsonl",
)


def _read_setup() -> dict:
    if not _SETUP_MARKER.exists():
        return {}
    try:
        return json.loads(_SETUP_MARKER.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _get_country() -> str:
    return _read_setup().get("country_code", "HN")


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/api/checkpoint")
async def get_checkpoint() -> dict:
    """Return this node's latest signed attestation.

    Peers call this endpoint to pull our current Merkle root and chain state.
    Works even when the swarm is not running (returns unsigned, chain_length=0).
    """
    if _engine is not None:
        return _engine.build_my_attestation()

    # Minimal unsigned response when engine not started
    from centinel.federation.gossip import (
        _load_or_generate_keypair,
        _current_merkle_root,
        _derive_node_id,
        NodePayload,
    )
    from datetime import datetime, timezone

    try:
        pub_hex, node_id, _ = _load_or_generate_keypair()
    except Exception:
        pub_hex, node_id = "", "unknown"

    merkle_root, chain_length = _current_merkle_root()
    return NodePayload(
        node_id=node_id,
        public_key_hex=pub_hex,
        country_code=_get_country(),
        merkle_root=merkle_root,
        chain_length=chain_length,
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
        my_url=None,
        signature="",
    ).to_dict()


@router.post("/api/swarm/attest")
async def receive_attest(request: Request) -> dict:
    """Accept a NodePayload from a peer and fan it out to 2 random peers."""
    client_ip = request.client.host if request.client else "unknown"
    if not _attest_limiter.allow(client_ip):
        raise HTTPException(status_code=429, detail="Too many attestations from this IP.")

    if _engine is None:
        raise HTTPException(status_code=503, detail="Swarm not running. POST /api/swarm/connect first.")

    try:
        payload_dict = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body.")

    accepted = await _engine.receive_attestation(payload_dict)
    return {"accepted": accepted}


@router.get("/api/swarm/status")
async def swarm_status() -> dict:
    """Return current swarm state: running, peer count, consensus, peer list."""
    if _engine is None:
        # Return minimal offline status — still expose node_id so OPS can display it
        from centinel.federation.gossip import _load_or_generate_keypair, _derive_node_id
        try:
            pub_hex, node_id, _ = _load_or_generate_keypair()
        except Exception:
            pub_hex, node_id = "", "unknown"
        return {
            "running": False,
            "node_id": node_id,
            "public_key_hex": pub_hex,
            "my_url": None,
            "country_code": _get_country(),
            "connected_peers": 0,
            "consensus_root": None,
            "consensus_count": 0,
            "consensus_reached": False,
            "last_broadcast_utc": None,
            "peers": [],
        }
    return _engine.get_status()


@router.post("/api/swarm/connect")
async def swarm_connect(request: Request) -> dict:
    """Start the GossipEngine. Idempotent — safe to call multiple times."""
    global _engine, _engine_task

    if _engine is not None and _engine._running:
        return {"status": "already_running", "node_id": _engine._node_id}

    body: dict = {}
    try:
        body = await request.json()
    except Exception:
        pass

    my_url: Optional[str] = body.get("my_url") or os.getenv("CENTINEL_MY_URL")
    broadcast_interval = float(body.get("broadcast_interval", 60.0))
    country = _get_country()

    _engine = GossipEngine(
        country_code=country,
        my_url=my_url,
        broadcast_interval=broadcast_interval,
        anomaly_log=_anomaly_log,
        attack_log=_attack_log,
    )

    _engine_task = asyncio.create_task(_engine.start())

    # Wait a moment for bootstrap to complete
    try:
        await asyncio.wait_for(asyncio.shield(_engine_task), timeout=0.1)
    except (asyncio.TimeoutError, asyncio.CancelledError):
        pass

    def _sl(v: object) -> str:
        return str(v).replace("\n", "\\n").replace("\r", "\\r")

    logger.info("swarm_connect country=%s my_url=%s", _sl(country), _sl(my_url))
    return {"status": "connecting", "node_id": _engine._node_id, "country_code": country}


@router.post("/api/swarm/disconnect")
async def swarm_disconnect() -> dict:
    """Stop the GossipEngine and clear peer state."""
    global _engine, _engine_task

    if _engine is None:
        return {"status": "not_running"}

    node_id = _engine._node_id
    await _engine.stop()
    _engine = None
    if _engine_task:
        _engine_task.cancel()
        _engine_task = None

    logger.info("swarm_disconnect node_id=%s", node_id)
    return {"status": "disconnected", "node_id": node_id}


@router.post("/api/swarm/broadcast")
async def local_broadcast(request: Request) -> dict:
    """Sign and broadcast a local finding to the swarm.

    Called by the pipeline process to submit anomaly/attack findings.
    The engine fills node_id, signs with its Ed25519 key, and fans out.
    Body: partial FindingPayload dict (finding_type, severity, rule_key,
          summary, snapshot_id required; finding_id optional).
    """
    if _engine is None:
        raise HTTPException(status_code=503, detail="Swarm not running. POST /api/swarm/connect first.")

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body.")

    from centinel.federation.gossip import FindingPayload, _make_finding_id
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat()
    node_id = _engine._node_id
    rule_key = str(body.get("rule_key", "unknown"))[:64]
    finding_id = body.get("finding_id") or _make_finding_id(node_id, now, rule_key)

    finding = FindingPayload(
        finding_id=finding_id,
        node_id=node_id,
        country_code=_get_country(),
        finding_type=str(body.get("finding_type", "anomaly")),
        severity=str(body.get("severity", "HIGH")).upper(),
        rule_key=rule_key,
        summary=str(body.get("summary", ""))[:200],
        snapshot_id=str(body.get("snapshot_id", "")),
        timestamp_utc=now,
        signature="",
    )

    acks = await _engine.broadcast_finding(finding)
    return {"finding_id": finding.finding_id, "acks": acks}


@router.post("/api/swarm/finding")
async def receive_finding(request: Request) -> dict:
    """Accept a FindingPayload from a peer and fan it out to 2 random peers."""
    client_ip = request.client.host if request.client else "unknown"
    if not _finding_limiter.allow(client_ip):
        raise HTTPException(status_code=429, detail="Too many findings from this IP.")

    if _engine is None:
        raise HTTPException(status_code=503, detail="Swarm not running. POST /api/swarm/connect first.")

    try:
        payload_dict = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body.")

    accepted = await _engine.receive_finding(payload_dict)
    return {"accepted": accepted}


@router.get("/api/swarm/anomalies")
async def swarm_anomalies(
    since: Optional[str] = Query(None, description="ISO 8601 lower bound"),
    severity: Optional[str] = Query(None, description="HIGH or CRITICAL"),
    rule_key: Optional[str] = Query(None),
    node_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
) -> dict:
    """Query cross-node electoral anomalies stored in FederationAnomalyLog."""
    items = _anomaly_log.query(
        since_utc=since,
        severity=severity,
        rule_key=rule_key,
        node_id=node_id,
        limit=limit,
    )
    return {"findings": items, "stats": _anomaly_log.stats()}


@router.get("/api/swarm/attacks")
async def swarm_attacks(
    since: Optional[str] = Query(None, description="ISO 8601 lower bound"),
    node_id: Optional[str] = Query(None),
    rule_key: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
) -> dict:
    """Query cross-node swarm-targeted attacks stored in FederationAttackLog."""
    items = _attack_log.query(
        since_utc=since,
        node_id=node_id,
        rule_key=rule_key,
        limit=limit,
    )
    return {"findings": items, "stats": _attack_log.stats()}


@router.post("/api/swarm/report_scrape")
async def report_scrape(request: Request) -> dict:
    """Local pipeline reports a successful scrape. Engine signs and gossips it to peers.

    Body: {"source_id": "06_cortes", "content_hash": "<sha256hex>"}
    When swarm is not running returns accepted=False (non-fatal — pipeline continues).
    """
    if _engine is None:
        return {"accepted": False, "reason": "swarm_not_running"}

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body.")

    source_id = str(body.get("source_id", "")).strip()
    content_hash = str(body.get("content_hash", "")).strip()
    if not source_id:
        raise HTTPException(status_code=400, detail="source_id required.")

    await _engine.report_scrape_done(source_id, content_hash)
    return {"accepted": True, "source_id": source_id}


@router.post("/api/swarm/scrape_result")
async def receive_scrape_result(request: Request) -> dict:
    """Accept a ScrapeResultPayload from a peer and fan it out."""
    if _engine is None:
        raise HTTPException(status_code=503, detail="Swarm not running.")

    try:
        payload_dict = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body.")

    accepted = await _engine.receive_scrape_result(payload_dict)
    return {"accepted": accepted}


@router.get("/api/swarm/last_scraped")
async def last_scraped(
    source_id: str = Query(..., description="Source ID to check (e.g. '06_cortes', 'NACIONAL')"),
) -> dict:
    """Return the most recent scrape timestamp for a source as known to this node.

    Pipeline calls this before scraping to skip if another swarm node did it recently.
    Returns scraped_at_utc=null when swarm is offline or source has never been reported.
    """
    if _engine is None:
        return {"source_id": source_id, "scraped_at_utc": None}

    scraped_at = _engine.last_scraped_at(source_id)
    return {"source_id": source_id, "scraped_at_utc": scraped_at}


async def auto_start(country_code: Optional[str] = None) -> None:
    """Called on startup when CENTINEL_AUTOCONNECT=1."""
    global _engine, _engine_task
    if _engine is not None:
        return
    country = country_code or _get_country()
    my_url = os.getenv("CENTINEL_MY_URL")
    _engine = GossipEngine(
        country_code=country,
        my_url=my_url,
        anomaly_log=_anomaly_log,
        attack_log=_attack_log,
    )
    _engine_task = asyncio.create_task(_engine.start())
    logger.info("swarm_autostart country=%s", country)
