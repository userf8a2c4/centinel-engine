"""
Endpoint Integrity Monitor for Centinel Engine.

ES: Monitor de Integridad de Endpoints para Centinel Engine.

Detecta cambios en estructura de API (schema) y disponibilidad de endpoints.
Si CNE cambia URLs o estructura JSON, quedará registrado como evidencia forense.

EN: Detects changes in API structure (schema) and endpoint availability.
If CNE changes URLs or JSON structure, it will be recorded as forensic evidence.

Design:
- Non-fatal: anomalies logged but don't block snapshots
- Schema-focused: monitors structure, not data values
- Forensic: all changes logged to attack_log.jsonl
- Mergeable: schema hash included in checkpoint for audit consensus
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, asdict
from typing import Any, Optional

import httpx

logger = logging.getLogger("centinel.endpoint_monitor")


@dataclass
class EndpointSchema:
    """Fingerprint of endpoint response structure.

    ES: Huella de la estructura de respuesta del endpoint.
    """
    timestamp: float
    url: str
    status_code: int
    content_type: Optional[str]
    keys: list[str]  # Top-level keys in JSON response
    schema_hash: str  # SHA256 of sorted keys + types
    is_error: bool = False
    error_detail: Optional[str] = None


@dataclass
class SchemaChange:
    """Detection of endpoint schema divergence.

    ES: Detección de divergencia de schema de endpoint.
    """
    timestamp: float
    url: str
    change_type: str  # "schema_mismatch", "endpoint_down", "status_code_change"
    severity: str  # "low", "medium", "high"
    baseline_hash: Optional[str]
    observed_hash: Optional[str]
    detail: str


class EndpointMonitor:
    """Monitors endpoint availability and schema integrity.

    ES: Monitorea disponibilidad del endpoint e integridad de schema.

    Design:
    - Maintains baseline schemas for known endpoints
    - Periodically scans endpoints for changes
    - Logs divergences to forensic record
    - Computes schema Merkle root for checkpoints
    """

    def __init__(
        self,
        timeout: float = 10.0,
        schema_hash_tolerance: int = 0,
    ) -> None:
        """Initialize monitor.

        Args:
            timeout: HTTP request timeout (seconds). Overridable via env
                     var CENTINEL_ENDPOINT_TIMEOUT (D11.1) — useful for
                     high-latency election nights where 10s is too tight.
            schema_hash_tolerance: Allow N hash mismatches before flagging
                                  (0 = strict, any change flagged)
        """
        env_timeout = os.environ.get("CENTINEL_ENDPOINT_TIMEOUT")
        if env_timeout:
            try:
                timeout = float(env_timeout)
                logger.info("endpoint_timeout_from_env value=%.1f", timeout)
            except ValueError:
                logger.warning(
                    "endpoint_timeout_env_invalid value=%s using_default=%.1f",
                    env_timeout,
                    timeout,
                )
        self.timeout = timeout
        self.schema_hash_tolerance = schema_hash_tolerance
        self.baselines: dict[str, EndpointSchema] = {}
        self.changes: list[SchemaChange] = []

    def register_baseline(self, url: str, schema: EndpointSchema) -> None:
        """Register known-good endpoint schema.

        Args:
            url: Endpoint URL
            schema: Baseline schema fingerprint
        """
        self.baselines[url] = schema
        logger.info("endpoint_baseline_registered url=%s hash=%s", url, schema.schema_hash)

    def scan_endpoint(self, url: str) -> Optional[EndpointSchema]:
        """Scan endpoint and extract schema.

        Args:
            url: Endpoint to scan

        Returns:
            EndpointSchema with fingerprint, or None on fatal error
        """
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(url, follow_redirects=True)
                status = resp.status_code

                # D11.3: track redirect chain. A malicious authority could
                # install a redirect to a fake endpoint; >1 hop is suspicious.
                if len(resp.history) > 1:
                    chain = " → ".join(
                        f"{r.status_code} {r.url}" for r in resp.history
                    )
                    logger.warning(
                        "endpoint_multiple_redirects url=%s hops=%d chain=%s",
                        url,
                        len(resp.history),
                        chain,
                    )

                # Determine content type
                content_type = resp.headers.get("content-type", "").split(";")[0]

                # Parse JSON if available
                keys = []
                schema_hash = ""
                error_detail = None

                if 200 <= status < 300 and "application/json" in content_type:
                    try:
                        data = resp.json()
                        if isinstance(data, dict):
                            keys = sorted(data.keys())
                        elif isinstance(data, list) and data:
                            # If array of objects, extract keys from first
                            if isinstance(data[0], dict):
                                keys = sorted(data[0].keys())
                        schema_hash = self._compute_schema_hash(keys)
                    except (json.JSONDecodeError, ValueError) as e:
                        error_detail = f"json_parse_error: {str(e)}"
                        logger.warning("endpoint_json_parse_error url=%s error=%s", url, error_detail)
                elif status != 200:
                    error_detail = f"http_{status}"
                    logger.warning("endpoint_http_error url=%s status=%d", url, status)
                else:
                    error_detail = f"non_json_content_type: {content_type}"
                    logger.warning("endpoint_non_json url=%s content_type=%s", url, content_type)

                schema = EndpointSchema(
                    timestamp=time.time(),
                    url=url,
                    status_code=status,
                    content_type=content_type,
                    keys=keys,
                    schema_hash=schema_hash,
                    is_error=error_detail is not None,
                    error_detail=error_detail,
                )
                return schema

        except httpx.TimeoutException:
            logger.error("endpoint_timeout url=%s", url)
            return EndpointSchema(
                timestamp=time.time(),
                url=url,
                status_code=0,
                content_type=None,
                keys=[],
                schema_hash="",
                is_error=True,
                error_detail="timeout",
            )
        except httpx.RequestError as e:
            logger.error("endpoint_request_error url=%s error=%s", url, str(e))
            return EndpointSchema(
                timestamp=time.time(),
                url=url,
                status_code=0,
                content_type=None,
                keys=[],
                schema_hash="",
                is_error=True,
                error_detail=f"request_error: {str(e)}",
            )

    def detect_changes(self, observed: EndpointSchema) -> Optional[SchemaChange]:
        """Compare observed schema to baseline.

        Args:
            observed: Current endpoint schema

        Returns:
            SchemaChange if divergence detected, else None
        """
        baseline = self.baselines.get(observed.url)
        if not baseline:
            logger.debug("endpoint_no_baseline url=%s (first scan)", observed.url)
            return None

        # Check 1: Status code change
        if observed.status_code != baseline.status_code:
            change = SchemaChange(
                timestamp=observed.timestamp,
                url=observed.url,
                change_type="status_code_change",
                severity="high" if observed.status_code >= 500 else "medium",
                baseline_hash=None,
                observed_hash=None,
                detail=f"HTTP status changed: {baseline.status_code} → {observed.status_code}",
            )
            self.changes.append(change)
            logger.error("endpoint_status_change url=%s baseline=%d observed=%d",
                        observed.url, baseline.status_code, observed.status_code)
            return change

        # Check 2: Schema hash divergence
        if observed.schema_hash and baseline.schema_hash:
            if observed.schema_hash != baseline.schema_hash:
                change = SchemaChange(
                    timestamp=observed.timestamp,
                    url=observed.url,
                    change_type="schema_mismatch",
                    severity="high",
                    baseline_hash=baseline.schema_hash,
                    observed_hash=observed.schema_hash,
                    detail=f"Schema changed: keys {baseline.keys} → {observed.keys}",
                )
                self.changes.append(change)
                logger.error("endpoint_schema_divergence url=%s baseline_keys=%s observed_keys=%s",
                            observed.url, baseline.keys, observed.keys)
                return change

        # Check 3: Endpoint down (was 200, now error)
        if not observed.is_error and baseline.is_error is False:
            if observed.is_error:
                change = SchemaChange(
                    timestamp=observed.timestamp,
                    url=observed.url,
                    change_type="endpoint_down",
                    severity="high",
                    baseline_hash=baseline.schema_hash,
                    observed_hash=None,
                    detail=f"Endpoint became unreachable: {observed.error_detail}",
                )
                self.changes.append(change)
                logger.error("endpoint_down url=%s detail=%s", observed.url, observed.error_detail)
                return change

        return None

    def schema_merkle_root(self) -> str:
        """Compute Merkle root of all registered endpoint schemas.

        Used to include in checkpoint for consensus verification.
        If CNE changes multiple endpoints, root will differ.
        """
        if not self.baselines:
            return ""

        # Sort by URL, hash each schema
        urls = sorted(self.baselines.keys())
        hashes = [self.baselines[url].schema_hash for url in urls]

        # Build Merkle tree (Bitcoin-style)
        if not hashes:
            return ""

        return self._merkle_root(hashes)

    def _compute_schema_hash(self, keys: list[str]) -> str:
        """Compute SHA256 hash of schema keys.

        ES: Computa SHA256 de las claves del schema.
        """
        data = json.dumps({"keys": keys}, sort_keys=True)
        return hashlib.sha256(data.encode("utf-8")).hexdigest()

    def _merkle_root(self, hashes: list[str]) -> str:
        """Compute Merkle root (Bitcoin-style with odd-level duplication).

        ES: Computa raíz de Merkle (estilo Bitcoin con duplicación en niveles impares).
        """
        if not hashes:
            return ""
        if len(hashes) == 1:
            return hashes[0]

        level = hashes[:]
        while len(level) > 1:
            next_level = []
            for i in range(0, len(level), 2):
                if i + 1 < len(level):
                    combined = level[i] + level[i + 1]
                else:
                    combined = level[i] + level[i]
                parent = hashlib.sha256(combined.encode("utf-8")).hexdigest()
                next_level.append(parent)
            level = next_level

        return level[0]

    def to_forensic_record(self) -> dict[str, Any]:
        """Export as forensic evidence.

        Returns dict suitable for attack_log.jsonl logging.
        """
        return {
            "event_type": "endpoint_integrity_scan",
            "timestamp": time.time(),
            "baselines_count": len(self.baselines),
            "changes_detected": len(self.changes),
            "changes": [asdict(change) for change in self.changes],
            "schema_merkle_root": self.schema_merkle_root(),
        }
