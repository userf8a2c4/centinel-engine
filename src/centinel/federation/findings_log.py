"""
FederationAnomalyLog — SQLite-backed persistent store for cross-node electoral findings.

Replaces the in-memory OrderedDict ring buffer with a WAL-mode SQLite database so
no evidence is lost due to capacity eviction, even at 100k-node scale.
"""
from __future__ import annotations

import json
import logging
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from centinel.federation.gossip import FindingPayload

logger = logging.getLogger("centinel.federation.findings_log")

_BROADCAST_SEVERITIES = {"HIGH", "CRITICAL"}

# Default SQLite path relative to the log_path parent
_DB_FILENAME = "federation_anomalies.db"


class FederationAnomalyLog:
    """SQLite-backed persistent store for cross-node electoral findings.

    Replaces the in-memory ring buffer. Capacity is enforced via SQL eviction
    (DELETE oldest rows when over max_findings). WAL mode allows concurrent reads
    while a write is in progress.

    Accepts finding_type "rule_violation" and "anomaly" at severity HIGH or CRITICAL.
    """

    ACCEPTED_TYPES = {"rule_violation", "anomaly"}

    def __init__(
        self,
        max_findings: int = 500,
        log_path: Optional[Path] = None,
    ) -> None:
        self._max = max_findings
        self._log_path = log_path  # legacy JSONL audit trail (kept for compat)
        self._lock = threading.Lock()

        # Derive SQLite path from log_path parent, or use in-memory if no path.
        # For :memory: we keep a single persistent connection so the schema
        # (and data) survives across _connect() calls.
        if log_path:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            self._db_path: Optional[str] = str(log_path.parent / _DB_FILENAME)
            self._mem_conn: Optional[sqlite3.Connection] = None
        else:
            self._db_path = None  # in-memory fallback
            self._mem_conn = sqlite3.connect(":memory:", check_same_thread=False)

        self._init_db()

    # ── DB helpers ────────────────────────────────────────────────────────────

    def _connect(self) -> sqlite3.Connection:
        if self._mem_conn is not None:
            return self._mem_conn  # reuse single in-memory connection
        conn = sqlite3.connect(self._db_path, check_same_thread=False)  # type: ignore[arg-type]
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._lock:
            conn = self._connect()
            # For in-memory connections we never close them; wrap only file DBs
            owned = self._mem_conn is None
            try:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA synchronous=NORMAL")
                conn.row_factory = sqlite3.Row
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS findings (
                        finding_id   TEXT PRIMARY KEY,
                        node_id      TEXT,
                        country_code TEXT,
                        finding_type TEXT,
                        severity     TEXT,
                        rule_key     TEXT,
                        summary      TEXT,
                        snapshot_id  TEXT,
                        timestamp_utc TEXT,
                        source       TEXT,
                        received_utc TEXT,
                        payload_json TEXT
                    )
                """)
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_ts ON findings(timestamp_utc DESC)"
                )
                conn.commit()
            finally:
                if owned:
                    conn.close()

    def _close(self, conn: sqlite3.Connection) -> None:
        """Close connection only if it is not the shared in-memory connection."""
        if conn is not self._mem_conn:
            conn.close()

    def _evict(self, conn: sqlite3.Connection) -> None:
        """Delete oldest rows when over capacity. Called inside a write lock."""
        count = conn.execute("SELECT COUNT(*) FROM findings").fetchone()[0]
        if count > self._max:
            excess = count - self._max
            conn.execute("""
                DELETE FROM findings WHERE finding_id IN (
                    SELECT finding_id FROM findings
                    ORDER BY timestamp_utc ASC
                    LIMIT ?
                )
            """, (excess,))

    # ── Public API ────────────────────────────────────────────────────────────

    def add(self, finding: "FindingPayload", source: str = "remote") -> bool:
        """Add finding to the store. Returns True if new (not a duplicate)."""
        if finding.finding_type not in self.ACCEPTED_TYPES:
            return False
        if finding.severity not in _BROADCAST_SEVERITIES:
            return False

        received_utc = datetime.now(timezone.utc).isoformat()
        payload_json = json.dumps(finding.to_dict(), ensure_ascii=False)

        with self._lock:
            conn = self._connect()
            try:
                cur = conn.execute(
                    "SELECT 1 FROM findings WHERE finding_id = ?",
                    (finding.finding_id,),
                )
                if cur.fetchone():
                    return False  # duplicate

                conn.execute("""
                    INSERT INTO findings (
                        finding_id, node_id, country_code, finding_type,
                        severity, rule_key, summary, snapshot_id,
                        timestamp_utc, source, received_utc, payload_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    finding.finding_id, finding.node_id, finding.country_code,
                    finding.finding_type, finding.severity, finding.rule_key,
                    finding.summary, finding.snapshot_id, finding.timestamp_utc,
                    source, received_utc, payload_json,
                ))
                self._evict(conn)
                conn.commit()

                if self._log_path:
                    self._append_jsonl({
                        **finding.to_dict(),
                        "_source": source,
                        "_received_utc": received_utc,
                    })
            finally:
                self._close(conn)

        logger.info(
            "federation_anomaly_added finding_id=%s rule=%s severity=%s source=%s",
            finding.finding_id, finding.rule_key, finding.severity, source,
        )
        return True

    def query(
        self,
        since_utc: Optional[str] = None,
        severity: Optional[str] = None,
        rule_key: Optional[str] = None,
        node_id: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        """Query findings with optional filters, most recent first."""
        sql = "SELECT payload_json, source, received_utc FROM findings WHERE 1=1"
        params: list = []
        if since_utc:
            sql += " AND timestamp_utc >= ?"
            params.append(since_utc)
        if severity:
            sql += " AND severity = ?"
            params.append(severity.upper())
        if rule_key:
            sql += " AND rule_key = ?"
            params.append(rule_key)
        if node_id:
            sql += " AND node_id = ?"
            params.append(node_id)
        sql += " ORDER BY timestamp_utc DESC LIMIT ?"
        params.append(limit)

        conn = self._connect()
        try:
            rows = conn.execute(sql, params).fetchall()
        finally:
            self._close(conn)

        result = []
        for row in rows:
            try:
                entry = json.loads(row[0])
                entry["_source"] = row[1]
                entry["_received_utc"] = row[2]
                result.append(entry)
            except Exception:
                pass
        return result

    def stats(self) -> dict:
        """Summary of stored findings."""
        conn = self._connect()
        try:
            total = conn.execute("SELECT COUNT(*) FROM findings").fetchone()[0]
            by_severity = {
                r[0]: r[1]
                for r in conn.execute(
                    "SELECT severity, COUNT(*) FROM findings GROUP BY severity"
                ).fetchall()
            }
            by_rule = {
                r[0]: r[1]
                for r in conn.execute(
                    "SELECT rule_key, COUNT(*) FROM findings GROUP BY rule_key"
                ).fetchall()
            }
            by_node = {
                r[0]: r[1]
                for r in conn.execute(
                    "SELECT node_id, COUNT(*) FROM findings GROUP BY node_id"
                ).fetchall()
            }
        finally:
            self._close(conn)
        return {
            "total": total,
            "by_severity": by_severity,
            "by_rule": by_rule,
            "by_node": by_node,
        }

    def get_consensus_summary(self, min_nodes: int = 2, limit: int = 20) -> list[dict]:
        """Return findings corroborated by >= min_nodes distinct nodes.

        Groups findings by (rule_key, snapshot_id) and counts distinct node_ids.
        Useful for building a "X nodes confirmed [rule] in snapshot Y" view.

        English:
            Returns cross-node consensus: findings seen by multiple distinct nodes.
        """
        conn = self._connect()
        try:
            rows = conn.execute(
                """
                SELECT rule_key, snapshot_id,
                       COUNT(DISTINCT node_id) AS node_count,
                       GROUP_CONCAT(DISTINCT node_id) AS nodes,
                       MAX(severity) AS severity,
                       MAX(timestamp_utc) AS last_seen
                FROM findings
                GROUP BY rule_key, snapshot_id
                HAVING node_count >= ?
                ORDER BY node_count DESC, last_seen DESC
                LIMIT ?
                """,
                (min_nodes, limit),
            ).fetchall()
        finally:
            self._close(conn)
        return [dict(r) for r in rows]

    def _append_jsonl(self, entry: dict) -> None:
        try:
            with self._log_path.open("a", encoding="utf-8") as fh:  # type: ignore[union-attr]
                fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError as exc:
            logger.warning("federation_anomaly_log_write_error error=%s", exc)
