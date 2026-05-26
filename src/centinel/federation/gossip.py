"""
Gossip protocol engine for Centinel P2P node network.

Each node broadcasts its signed attestation (NodePayload) to known peers
via HTTP POST. When a node receives a new attestation it fans out to 2
random peers (epidemic propagation). Peer discovery uses four zero-cost
bootstrap layers tried in parallel:
  1. GitHub Pages peer list (country-specific JSON)
  2. Raw GitHub fallback (raw.githubusercontent.com)
  3. DNS-over-HTTPS TXT records (Cloudflare)
  4. mDNS UDP multicast on local network
  5. Hardcoded project bootstrap seeds
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import random
import socket
import struct
import threading
import time
from collections import OrderedDict, deque
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger("centinel.federation.gossip")

_REPO_ROOT = Path(__file__).resolve().parents[4]
_KEYS_DIR = _REPO_ROOT / "keys"

_BOOTSTRAP_URL_TEMPLATE = (
    "https://vectisdev.github.io/centinel/peers/{country}.json"
)
_BOOTSTRAP_BACKUP_TEMPLATE = (
    "https://raw.githubusercontent.com/vectisdev/centinel/main/peers/{country}.json"
)
_DNS_BOOTSTRAP_DOMAIN = "peers-{country}.centinel.vectisdev.com"

_HARDCODED_SEEDS: list[str] = [
    # Add well-known bootstrap node URLs here as the network grows, e.g.:
    # "https://node1.centinel.vectisdev.com",
    # "https://node2.centinel.vectisdev.com",
]

_MDNS_ADDR = "224.0.0.251"
_MDNS_PORT = 5353
_MDNS_TIMEOUT = 3.0
_CENTINEL_MDNS_SERVICE = b"_centinel._tcp.local"

_FAN_OUT = 2
_GOSSIP_VERSION = 1
_FINDING_VERSION = 1
_FINDING_RATE_LIMIT = 10       # max findings broadcast per minute per node
_FINDING_RATE_WINDOW = 60.0    # sliding window in seconds
_BROADCAST_SEVERITIES = {"HIGH", "CRITICAL"}
_LRU_PUBKEY_CACHE_SIZE = 10_000


# ── Data structures ───────────────────────────────────────────────────────────


@dataclass
class NodePayload:
    """Signed attestation broadcast by a Centinel node."""

    node_id: str           # sha256(public_key_hex)[:16]
    public_key_hex: str    # Ed25519 public key (64 hex chars)
    country_code: str      # ISO-2 country code, e.g. "HN"
    merkle_root: str       # SHA256 hex of entire snapshot chain
    chain_length: int      # Number of snapshots in chain
    timestamp_utc: str     # ISO 8601
    my_url: Optional[str]  # Public base URL if node is reachable, else None
    signature: str         # Ed25519(sha256(canonical JSON without this field))
    version: int = _GOSSIP_VERSION
    epoch: int = 0  # Incremented when a fork/rollback in chain is detected locally

    def canonical_bytes(self) -> bytes:
        """Serialise deterministically for signing/verification (excludes signature)."""
        d = asdict(self)
        d.pop("signature", None)
        return json.dumps(d, sort_keys=True, separators=(",", ":")).encode()

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "NodePayload":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class FindingPayload:
    """Signed anomaly/attack finding broadcast by a Centinel node.

    finding_type values:
      "rule_violation" — fired by the rules engine (late_mesa, hold_and_release, …)
      "anomaly"        — fired by the anomaly detector (Benford, z-score, …)
      "swarm_attack"   — infrastructure attack directed at Centinel endpoints
    """

    finding_id: str        # sha256(node_id+timestamp+rule_key)[:16] — dedup key
    node_id: str           # sha256(public_key_hex)[:16] of the detecting node
    country_code: str      # ISO-2, e.g. "HN"
    finding_type: str      # "rule_violation" | "anomaly" | "swarm_attack"
    severity: str          # "HIGH" | "CRITICAL" — only these are broadcast
    rule_key: str          # Rule/detector name: "late_mesa", "hold_and_release", "flood", …
    summary: str           # ≤200 chars human description
    snapshot_id: str       # Related snapshot hash, or "" for attack events
    timestamp_utc: str     # ISO 8601
    signature: str         # Ed25519 over canonical JSON (excludes this field)
    version: int = _FINDING_VERSION
    ttl_hops: int = 8  # Decremented on each fan-out hop; 0 = store locally, no forward

    def canonical_bytes(self) -> bytes:
        d = asdict(self)
        d.pop("signature", None)
        d.pop("ttl_hops", None)  # transport field, not part of the signed payload
        return json.dumps(d, sort_keys=True, separators=(",", ":")).encode()

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "FindingPayload":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


def _make_finding_id(node_id: str, timestamp_utc: str, rule_key: str) -> str:
    """Deterministic dedup key for a finding."""
    raw = f"{node_id}:{timestamp_utc}:{rule_key}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


@dataclass
class ScrapeResultPayload:
    """Positive gossip: a node reports a successful scrape so others can skip it.

    Guarantees ≤1 HTTP request per source per TTL window across the whole
    swarm — protecting the CNE endpoint from collective overload regardless
    of how many nodes are running.
    """

    result_id: str       # sha256(node_id + source_id + scraped_at_utc)[:16]
    node_id: str         # sha256(public_key_hex)[:16] of the scraping node
    source_id: str       # e.g. "NACIONAL", "06_cortes"
    content_hash: str    # SHA256 of raw response (proof something was actually fetched)
    scraped_at_utc: str  # ISO 8601
    signature: str       # Ed25519 over canonical JSON (excludes this field)
    version: int = 1

    def canonical_bytes(self) -> bytes:
        d = asdict(self)
        d.pop("signature", None)
        return json.dumps(d, sort_keys=True, separators=(",", ":")).encode()

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "ScrapeResultPayload":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


def _make_result_id(node_id: str, source_id: str, scraped_at_utc: str) -> str:
    """Deterministic dedup key for a scrape result."""
    raw = f"{node_id}:{source_id}:{scraped_at_utc}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ── Helpers ───────────────────────────────────────────────────────────────────


def _derive_node_id(public_key_hex: str) -> str:
    return hashlib.sha256(public_key_hex.encode()).hexdigest()[:16]


def _load_or_generate_keypair() -> tuple[str, str, Path]:
    """Return (public_key_hex, node_id, private_key_path), generating if needed."""
    from centinel.core.custody import (  # local import to avoid circular deps
        generate_operator_keypair,
        _load_operator_public_key,
    )

    private_path = _KEYS_DIR / "operator_private.pem"
    public_path = _KEYS_DIR / "operator_public.pem"

    if not private_path.exists():
        result = generate_operator_keypair(key_dir=_KEYS_DIR)
        pub_hex = result["public_key_hex"]
    else:
        pub_key = _load_operator_public_key(public_path)
        pub_hex = pub_key.public_bytes_raw().hex()

    node_id = _derive_node_id(pub_hex)
    return pub_hex, node_id, private_path


def _sign_payload(payload: NodePayload, key_path: Path) -> str:
    """Return hex Ed25519 signature over canonical bytes of payload."""
    from centinel.core.custody import sign_snapshot

    result = sign_snapshot(payload.canonical_bytes(), key_path=key_path)
    return result.signature_hex


def _verify_payload_sig(payload: NodePayload) -> bool:
    """Return True if the payload's signature is valid."""
    from centinel.core.custody import verify_snapshot_signature

    try:
        return verify_snapshot_signature(
            payload.canonical_bytes(),
            payload.signature,
            public_key_hex=payload.public_key_hex,
        )
    except Exception:
        return False


def _sign_finding(finding: FindingPayload, key_path: Path) -> str:
    """Return hex Ed25519 signature over canonical bytes of a FindingPayload."""
    from centinel.core.custody import sign_snapshot

    result = sign_snapshot(finding.canonical_bytes(), key_path=key_path)
    return result.signature_hex


def _verify_finding_sig(finding: FindingPayload, public_key_hex: str) -> bool:
    """Return True if the finding's signature is valid against the given public key."""
    from centinel.core.custody import verify_snapshot_signature

    try:
        return verify_snapshot_signature(
            finding.canonical_bytes(),
            finding.signature,
            public_key_hex=public_key_hex,
        )
    except Exception:
        return False


def _current_merkle_root() -> tuple[str, int]:
    """Return (merkle_root_hex, chain_length) from the local snapshot DB, or zeros."""
    try:
        import sqlite3

        db = _REPO_ROOT / "data" / "snapshots.db"
        if not db.exists():
            return "0" * 64, 0
        with sqlite3.connect(str(db)) as conn:
            row = conn.execute(
                "SELECT hash, id FROM snapshots ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if not row:
                return "0" * 64, 0
            count = conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0]
            return row[0], count
    except Exception:
        return "0" * 64, 0


# ── Bootstrap helpers ─────────────────────────────────────────────────────────


async def _bootstrap_from_github(country: str) -> list[str]:
    """Fetch peer URLs from GitHub Pages bootstrap JSON. Returns list of base URLs."""
    url = _BOOTSTRAP_URL_TEMPLATE.format(country=country.upper())
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url)
            if r.status_code != 200:
                return []
            data = r.json()
            peers = data.get("peers", [])
            return [p["url"] for p in peers if p.get("url")]
    except Exception as exc:
        logger.debug("github_bootstrap_failed url=%s error=%s", url, exc)
        return []


async def _bootstrap_from_raw_github(country: str) -> list[str]:
    """Fallback: fetch peers from raw.githubusercontent.com when GitHub Pages is down."""
    url = _BOOTSTRAP_BACKUP_TEMPLATE.format(country=country.upper())
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.get(url)
            if r.status_code != 200:
                return []
            data = r.json()
            peers = data.get("peers", [])
            return [p["url"] for p in peers if p.get("url")]
    except Exception as exc:
        logger.debug("raw_github_bootstrap_failed url=%s error=%s", url, exc)
        return []


async def _bootstrap_from_dns_over_https(country: str) -> list[str]:
    """Fetch peer URLs from DNS TXT record via Cloudflare DNS-over-HTTPS.

    Record format: one URL per TXT value at peers-{country}.centinel.vectisdev.com
    """
    domain = _DNS_BOOTSTRAP_DOMAIN.format(country=country.lower())
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            r = await client.get(
                "https://cloudflare-dns.com/dns-query",
                params={"name": domain, "type": "TXT"},
                headers={"Accept": "application/dns-json"},
            )
            if r.status_code != 200:
                return []
            data = r.json()
            peers = []
            for answer in data.get("Answer", []):
                if answer.get("type") == 16:  # TXT
                    txt = answer.get("data", "").strip('"').strip()
                    if txt.startswith(("https://", "http://")):
                        peers.append(txt)
            return peers
    except Exception as exc:
        logger.debug("dns_over_https_bootstrap_failed domain=%s error=%s", domain, exc)
        return []


def _bootstrap_from_mdns() -> list[str]:
    """Discover local Centinel nodes via UDP multicast. Returns list of base URLs."""
    urls: list[str] = []
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(_MDNS_TIMEOUT)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Join multicast group
        group = struct.pack("4sL", socket.inet_aton(_MDNS_ADDR), socket.INADDR_ANY)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, group)
        # mDNS multicast (RFC 6762) requires INADDR_ANY to receive packets from
        # peers on any local interface. Operators on multi-homed hosts can pin
        # to a specific iface via CENTINEL_MDNS_IFACE.
        _mdns_iface = os.environ.get("CENTINEL_MDNS_IFACE", "0.0.0.0")  # nosec B104
        sock.bind((_mdns_iface, _MDNS_PORT))  # nosec B104

        # Send a simple discovery probe: the service name as UTF-8
        sock.sendto(_CENTINEL_MDNS_SERVICE, (_MDNS_ADDR, _MDNS_PORT))

        deadline = time.monotonic() + _MDNS_TIMEOUT
        while time.monotonic() < deadline:
            try:
                data, addr = sock.recvfrom(512)
                if data.startswith(b"centinel://"):
                    url = data.decode(errors="replace").strip()
                    if url not in urls:
                        urls.append(url.replace("centinel://", "http://"))
            except socket.timeout:
                break
        sock.close()
    except Exception as exc:
        logger.debug("mdns_discovery_failed error=%s", exc)
    return urls


# ── LRU pubkey cache ──────────────────────────────────────────────────────────


class _LRUPubkeyCache:
    """Thread-safe LRU cache for node_id → public_key_hex.

    Separate from the peer routing table (max_peers=50). Holds up to
    _LRU_PUBKEY_CACHE_SIZE entries so findings from any previously-seen
    node can be verified even when it's not in the active routing table.
    """

    def __init__(self, maxsize: int) -> None:
        self._store: OrderedDict[str, str] = OrderedDict()
        self._maxsize = maxsize
        self._lock = threading.Lock()

    def put(self, node_id: str, pub_hex: str) -> None:
        with self._lock:
            if node_id in self._store:
                self._store.move_to_end(node_id)
            else:
                self._store[node_id] = pub_hex
                while len(self._store) > self._maxsize:
                    self._store.popitem(last=False)

    def get(self, node_id: str) -> Optional[str]:
        with self._lock:
            if node_id not in self._store:
                return None
            self._store.move_to_end(node_id)
            return self._store[node_id]

    def __len__(self) -> int:
        with self._lock:
            return len(self._store)


# ── Gossip Engine ─────────────────────────────────────────────────────────────


class GossipEngine:
    """Push-pull epidemic gossip engine.

    Each active node periodically broadcasts its own NodePayload to known
    peers. Received payloads are verified and fanned out to _FAN_OUT random
    peers, achieving O(log N) convergence.
    """

    def __init__(
        self,
        country_code: str,
        my_url: Optional[str] = None,
        broadcast_interval: float = 60.0,
        max_peers: int = 50,
        anomaly_log: Optional[object] = None,
        attack_log: Optional[object] = None,
    ) -> None:
        self.country_code = country_code.upper()
        self.my_url = my_url
        # Privacy mode: suppress my_url so this node's address is never broadcast
        # in gossip attestations. The node remains a full gossip participant
        # (receives/forwards payloads) but is not discoverable by URL via peers.
        if my_url and os.getenv("CENTINEL_PRIVACY_MODE", "").strip().lower() in ("1", "true", "yes"):
            logger.info("gossip_privacy_mode_active my_url_suppressed")
            self.my_url = None
        self.broadcast_interval = broadcast_interval
        self.max_peers = max_peers

        # Federation finding logs (optional — gossip still works without them)
        self._anomaly_log = anomaly_log  # FederationAnomalyLog
        self._attack_log = attack_log    # FederationAttackLog

        # ES: Callback opcional para propagar throttles de fuente a otros nodos.
        # EN: Optional callback to propagate source throttles from remote nodes.
        # Signature: (source_id: str, until_utc: str) -> None
        self._throttle_callback: Optional[object] = None

        # ES: Registro cooperativo — un nodo comparte que ya raspó una fuente para
        #     que los demás la salten. Garantiza ≤1 req/fuente/TTL en todo el enjambre.
        # EN: Cooperative registry — a node shares that it scraped a source so others
        #     skip it. Guarantees ≤1 req/source/TTL across the whole swarm.
        self._scrape_registry: dict[str, ScrapeResultPayload] = {}
        self._scrape_lock = threading.Lock()

        self._peers: dict[str, str] = {}   # node_id → base_url
        self._known: dict[str, NodePayload] = {}  # node_id → latest payload
        # Pubkey cache: all nodes ever seen (LRU, max 10k). Independent of routing table.
        self._pubkey_cache = _LRUPubkeyCache(_LRU_PUBKEY_CACHE_SIZE)
        self._pub_hex: str = ""
        self._node_id: str = ""
        self._key_path: Optional[Path] = None
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._last_broadcast: Optional[float] = None

        # Per-sender inbound finding rate tracking (keyed by node_id after sig verify)
        self._inbound_node_rate: dict[str, deque] = {}
        self._inbound_rate_lock = threading.Lock()

    # ── lifecycle ──────────────────────────────────────────────────────────────

    async def start(self) -> None:
        if self._running:
            return
        self._pub_hex, self._node_id, self._key_path = _load_or_generate_keypair()
        logger.info("gossip_start node_id=%s country=%s", self._node_id, self.country_code)

        # Bootstrap peer discovery — try all sources in parallel
        results = await asyncio.gather(
            _bootstrap_from_github(self.country_code),
            _bootstrap_from_raw_github(self.country_code),
            _bootstrap_from_dns_over_https(self.country_code),
            return_exceptions=True,
        )
        peer_urls: list[str] = []
        for r in results:
            if isinstance(r, list):
                peer_urls.extend(r)
        peer_urls.extend(_bootstrap_from_mdns())
        peer_urls.extend(_HARDCODED_SEEDS)
        # Deduplicate while preserving order
        seen: set[str] = set()
        unique_urls = [u for u in peer_urls if not (u in seen or seen.add(u))]  # type: ignore[func-returns-value]

        for url in unique_urls:
            await self._fetch_checkpoint(url)

        self._running = True
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("gossip_stop node_id=%s peers=%d", self._node_id, len(self._peers))

    # ── public API ─────────────────────────────────────────────────────────────

    async def receive_attestation(self, payload_dict: dict) -> bool:
        """Accept an incoming NodePayload from a peer HTTP POST."""
        try:
            payload = NodePayload.from_dict(payload_dict)
        except (TypeError, KeyError) as exc:
            logger.debug("gossip_recv_bad_payload error=%s", exc)
            return False

        if not _verify_payload_sig(payload):
            logger.debug("gossip_recv_invalid_sig node_id=%s", payload_dict.get("node_id"))
            return False

        node_id = payload.node_id
        existing = self._known.get(node_id)
        if existing and existing.timestamp_utc >= payload.timestamp_utc:
            return True  # Already up to date

        self._known[node_id] = payload
        # Cache public key for later finding signature verification
        self._pubkey_cache.put(node_id, payload.public_key_hex)
        if payload.my_url:
            self._peers[node_id] = payload.my_url.rstrip("/")
            if len(self._peers) > self.max_peers:
                oldest = next(iter(self._peers))
                del self._peers[oldest]

        logger.info(
            "gossip_recv_accepted node_id=%s chain=%d merkle=%.8s",
            node_id, payload.chain_length, payload.merkle_root,
        )

        # Fan-out to 2 random peers (exclude sender)
        candidates = [u for nid, u in self._peers.items() if nid != node_id]
        for url in random.sample(candidates, min(_FAN_OUT, len(candidates))):
            asyncio.create_task(self._push_payload(url, payload))

        return True

    async def broadcast_finding(self, finding: FindingPayload) -> int:
        """Sign and broadcast a finding to known peers. Returns number of ACKs.

        Only broadcasts HIGH/CRITICAL findings. Rate-limited per verified node_id.
        """
        if finding.severity not in _BROADCAST_SEVERITIES:
            logger.debug("finding_broadcast_skipped severity=%s below threshold", finding.severity)
            return 0

        # Rate limit check using per-node approach (self._node_id for outbound)
        if not self._check_inbound_finding_rate(self._node_id):
            logger.warning(
                "finding_broadcast_rate_limited node=%s rate=%d/%ds",
                self._node_id, _FINDING_RATE_LIMIT, int(_FINDING_RATE_WINDOW),
            )
            return 0

        # Sign if not yet signed
        if not finding.signature and self._key_path:
            finding.signature = _sign_finding(finding, self._key_path)

        # Store locally
        self._store_finding(finding, source="local")

        # Fan-out to peers
        targets = list(self._peers.values())
        random.shuffle(targets)
        targets = targets[:10]

        acks = 0
        for url in targets:
            ok = await self._push_finding(url, finding)
            if ok:
                acks += 1

        logger.info(
            "finding_broadcast sent=%d acked=%d rule=%s severity=%s",
            len(targets), acks, finding.rule_key, finding.severity,
        )
        return acks

    async def receive_finding(self, payload_dict: dict) -> bool:
        """Accept a FindingPayload from a peer, verify signature, store and fan-out.

        Returns True if the finding was new and accepted.
        """
        try:
            finding = FindingPayload.from_dict(payload_dict)
        except (TypeError, KeyError) as exc:
            logger.debug("finding_recv_bad_payload error=%s", exc)
            return False

        if finding.severity not in _BROADCAST_SEVERITIES:
            logger.debug("finding_recv_low_severity severity=%s", finding.severity)
            return False

        # Verify signature using cached public key for this node_id
        pub_hex = self._pubkey_cache.get(finding.node_id)
        if not pub_hex:
            logger.debug("finding_recv_unknown_node node_id=%s", finding.node_id)
            # Accept without verification only if this is a self-finding (local node)
            if finding.node_id != self._node_id:
                return False
            pub_hex = self._pub_hex

        if finding.signature and not _verify_finding_sig(finding, pub_hex):
            logger.debug("finding_recv_invalid_sig node_id=%s", finding.node_id)
            return False

        # Rate limit per verified node_id (checked after sig verification)
        if not self._check_inbound_finding_rate(finding.node_id):
            logger.warning(
                "finding_recv_rate_limited node_id=%s rule=%s",
                finding.node_id, finding.rule_key,
            )
            return False

        # Dedup + store
        if not self._store_finding(finding, source="remote"):
            return True  # Already known — still valid, just not new

        logger.info(
            "finding_recv_accepted finding_id=%s rule=%s severity=%s from=%s",
            finding.finding_id, finding.rule_key, finding.severity, finding.node_id,
        )

        # ES: Si es un throttle de fuente, notificar al pipeline local para que
        #     pause el scraping de esa fuente durante el período indicado.
        # EN: If this is a source throttle signal, notify the local pipeline so
        #     it pauses scraping that source for the indicated period.
        if finding.finding_type == "source_throttle" and self._throttle_callback is not None:
            try:
                self._throttle_callback(finding.rule_key, finding.timestamp_utc)  # type: ignore[call-arg]
            except Exception as _cb_exc:
                logger.debug("throttle_callback_error source=%s error=%s", finding.rule_key, _cb_exc)

        # Fan-out to 2 random peers (exclude sender) — only if TTL allows
        if finding.ttl_hops > 0:
            fwd = FindingPayload(**{**asdict(finding), "ttl_hops": finding.ttl_hops - 1})
            candidates = [u for nid, u in self._peers.items() if nid != finding.node_id]
            for url in random.sample(candidates, min(_FAN_OUT, len(candidates))):
                asyncio.create_task(self._push_finding(url, fwd))
        else:
            logger.debug("finding_ttl_expired finding_id=%s — stored locally, no fan-out", finding.finding_id)

        return True

    def _store_finding(self, finding: FindingPayload, source: str) -> bool:
        """Route finding to the correct log. Returns True if new."""
        if finding.finding_type == "swarm_attack":
            if self._attack_log is not None:
                return self._attack_log.add(finding, source=source)
            return True  # No log configured — accept but don't store
        else:
            if self._anomaly_log is not None:
                return self._anomaly_log.add(finding, source=source)
            return True

    def _check_inbound_finding_rate(self, node_id: str) -> bool:
        """Return True if node_id is within inbound finding rate limits.

        Checked AFTER signature verification so node_id is authentic.
        Prevents a Sybil with many node_ids from flooding: each identity
        is limited independently, and the check is on verified node_ids only.
        """
        now = time.monotonic()
        with self._inbound_rate_lock:
            ts = self._inbound_node_rate.get(node_id)
            if ts is None:
                ts = deque()
                self._inbound_node_rate[node_id] = ts
            while ts and now - ts[0] > _FINDING_RATE_WINDOW:
                ts.popleft()
            if len(ts) >= _FINDING_RATE_LIMIT:
                return False
            ts.append(now)
            return True

    def get_status(self) -> dict:
        peers = list(self._known.values())
        consensus_root, consensus_count, consensus_epoch = self._compute_consensus(peers)
        local_reached = consensus_count >= max(2, int(len(peers) * 0.75))
        return {
            "running": self._running,
            "node_id": self._node_id,
            "public_key_hex": self._pub_hex,
            "my_url": self.my_url,
            "country_code": self.country_code,
            "connected_peers": len(self._known),
            "pubkey_cache_size": len(self._pubkey_cache),
            # Local consensus (based on up-to-50-peer view — not network-wide)
            "consensus_root": consensus_root,
            "consensus_count": consensus_count,
            "consensus_epoch": consensus_epoch,
            "consensus_reached": local_reached,
            "consensus_scope": "local_50_peer_view",
            "last_broadcast_utc": (
                datetime.fromtimestamp(self._last_broadcast, tz=timezone.utc).isoformat()
                if self._last_broadcast else None
            ),
            "peers": [
                {
                    "node_id": p.node_id,
                    "country_code": p.country_code,
                    "chain_length": p.chain_length,
                    "merkle_root": p.merkle_root,
                    "epoch": getattr(p, "epoch", 0),
                    "timestamp_utc": p.timestamp_utc,
                    "url": p.my_url,
                }
                for p in peers
            ],
        }

    def build_my_attestation(self) -> dict:
        """Build and sign this node's current NodePayload. Used by /api/checkpoint."""
        merkle_root, chain_length = _current_merkle_root()
        payload = NodePayload(
            node_id=self._node_id,
            public_key_hex=self._pub_hex,
            country_code=self.country_code,
            merkle_root=merkle_root,
            chain_length=chain_length,
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
            my_url=self.my_url,
            signature="",
        )
        if self._key_path:
            payload.signature = _sign_payload(payload, self._key_path)
        return payload.to_dict()

    # ── cooperative scraping ───────────────────────────────────────────────────

    def last_scraped_at(self, source_id: str) -> Optional[str]:
        """Return ISO timestamp of the most recent known scrape for source_id, or None."""
        with self._scrape_lock:
            result = self._scrape_registry.get(source_id)
            return result.scraped_at_utc if result else None

    async def report_scrape_done(self, source_id: str, content_hash: str) -> None:
        """Sign and gossip a successful scrape result to all known peers."""
        if not self._node_id or not self._key_path:
            return
        from centinel.core.custody import sign_snapshot

        now = datetime.now(timezone.utc).isoformat()
        result = ScrapeResultPayload(
            result_id=_make_result_id(self._node_id, source_id, now),
            node_id=self._node_id,
            source_id=source_id,
            content_hash=content_hash,
            scraped_at_utc=now,
            signature="",
        )
        result.signature = sign_snapshot(result.canonical_bytes(), key_path=self._key_path).signature_hex

        with self._scrape_lock:
            self._scrape_registry[source_id] = result

        targets = list(self._peers.values())
        random.shuffle(targets)
        for url in targets[:_FAN_OUT * 2]:
            asyncio.create_task(self._push_scrape_result(url, result))

        logger.info("scrape_result_broadcast source=%s peers=%d", source_id, min(len(targets), _FAN_OUT * 2))

    async def receive_scrape_result(self, payload_dict: dict) -> bool:
        """Accept a ScrapeResultPayload from a peer, verify signature, and fan out."""
        try:
            result = ScrapeResultPayload.from_dict(payload_dict)
        except (TypeError, KeyError) as exc:
            logger.debug("scrape_result_recv_bad_payload error=%s", exc)
            return False

        pub_hex = self._pubkey_cache.get(result.node_id)
        if not pub_hex:
            logger.debug("scrape_result_recv_unknown_node node_id=%s", result.node_id)
            return False

        try:
            from centinel.core.custody import verify_snapshot_signature
            if not verify_snapshot_signature(result.canonical_bytes(), result.signature, public_key_hex=pub_hex):
                logger.debug("scrape_result_recv_invalid_sig node_id=%s source=%s", result.node_id, result.source_id)
                return False
        except Exception:
            return False

        with self._scrape_lock:
            existing = self._scrape_registry.get(result.source_id)
            if existing and existing.scraped_at_utc >= result.scraped_at_utc:
                return True  # Already have an equal or more recent result
            self._scrape_registry[result.source_id] = result

        logger.info(
            "scrape_result_accepted source=%s node=%s at=%s",
            result.source_id, result.node_id, result.scraped_at_utc,
        )

        candidates = [u for nid, u in self._peers.items() if nid != result.node_id]
        for url in random.sample(candidates, min(_FAN_OUT, len(candidates))):
            asyncio.create_task(self._push_scrape_result(url, result))

        return True

    # ── internals ──────────────────────────────────────────────────────────────

    async def _loop(self) -> None:
        while self._running:
            try:
                await self.broadcast_my_attestation()
            except Exception as exc:
                logger.warning("gossip_broadcast_error error=%s", exc)
            await asyncio.sleep(self.broadcast_interval)

    async def broadcast_my_attestation(self) -> int:
        if not self._node_id:
            return 0
        attestation = self.build_my_attestation()
        payload = NodePayload.from_dict(attestation)

        targets = list(self._peers.values())
        random.shuffle(targets)
        targets = targets[:10]

        acks = 0
        for url in targets:
            ok = await self._push_payload(url, payload)
            if ok:
                acks += 1

        self._last_broadcast = time.time()
        logger.info(
            "gossip_broadcast sent=%d acked=%d merkle=%.8s",
            len(targets), acks, payload.merkle_root,
        )
        return acks

    async def _push_payload(self, base_url: str, payload: NodePayload) -> bool:
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                r = await client.post(
                    f"{base_url}/api/swarm/attest",
                    json=payload.to_dict(),
                    headers={"Content-Type": "application/json"},
                )
                return r.status_code == 200
        except Exception as exc:
            logger.debug("gossip_push_failed url=%s error=%s", base_url, exc)
            return False

    async def _push_finding(self, base_url: str, finding: FindingPayload) -> bool:
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                r = await client.post(
                    f"{base_url}/api/swarm/finding",
                    json=finding.to_dict(),
                    headers={"Content-Type": "application/json"},
                )
                return r.status_code == 200
        except Exception as exc:
            logger.debug("finding_push_failed url=%s error=%s", base_url, exc)
            return False

    async def _push_scrape_result(self, base_url: str, result: ScrapeResultPayload) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.post(
                    f"{base_url}/api/swarm/scrape_result",
                    json=result.to_dict(),
                    headers={"Content-Type": "application/json"},
                )
                return r.status_code == 200
        except Exception as exc:
            logger.debug("scrape_result_push_failed url=%s error=%s", base_url, exc)
            return False

    async def _fetch_checkpoint(self, base_url: str) -> None:
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                r = await client.get(f"{base_url.rstrip('/')}/api/checkpoint")
                if r.status_code == 200:
                    await self.receive_attestation(r.json())
        except Exception as exc:
            logger.debug("gossip_fetch_checkpoint_failed url=%s error=%s", base_url, exc)

    @staticmethod
    def _compute_consensus(peers: list[NodePayload]) -> tuple[Optional[str], int, int]:
        """Returns (best_merkle_root, vote_count, best_epoch)."""
        if not peers:
            return None, 0, 0
        counts: dict[tuple[int, str], int] = {}
        for p in peers:
            key = (getattr(p, "epoch", 0), p.merkle_root)
            counts[key] = counts.get(key, 0) + 1
        best_key = max(counts, key=lambda k: counts[k])
        return best_key[1], counts[best_key], best_key[0]
