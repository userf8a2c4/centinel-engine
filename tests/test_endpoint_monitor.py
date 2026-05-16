"""
Tests for endpoint integrity monitor.

Validates that endpoint schema changes are detected and logged.
"""

import time
from unittest.mock import MagicMock, patch

import pytest

from centinel.core.endpoint_monitor import (
    EndpointMonitor,
    EndpointSchema,
    SchemaChange,
)


class TestEndpointSchema:
    """Test EndpointSchema dataclass."""

    def test_create_schema(self):
        """Create valid endpoint schema."""
        schema = EndpointSchema(
            timestamp=time.time(),
            url="https://cne.hn/api/results",
            status_code=200,
            content_type="application/json",
            keys=["votes", "timestamp", "location"],
            schema_hash="abc123" * 10 + "abcd",  # 64-char hash
        )

        assert schema.url == "https://cne.hn/api/results"
        assert schema.status_code == 200
        assert len(schema.keys) == 3
        assert schema.is_error is False

    def test_schema_with_error(self):
        """Schema marked as error."""
        schema = EndpointSchema(
            timestamp=time.time(),
            url="https://cne.hn/api/results",
            status_code=503,
            content_type=None,
            keys=[],
            schema_hash="",
            is_error=True,
            error_detail="service_unavailable",
        )

        assert schema.is_error is True
        assert schema.error_detail == "service_unavailable"


class TestEndpointMonitor:
    """Test EndpointMonitor class."""

    def test_monitor_creation(self):
        """Create monitor instance."""
        monitor = EndpointMonitor(timeout=5.0)
        assert monitor.timeout == 5.0
        assert len(monitor.baselines) == 0

    def test_register_baseline(self):
        """Register endpoint baseline."""
        monitor = EndpointMonitor()
        schema = EndpointSchema(
            timestamp=time.time(),
            url="https://cne.hn/api/results",
            status_code=200,
            content_type="application/json",
            keys=["votes", "timestamp"],
            schema_hash="abc" * 21 + "defg",
        )

        monitor.register_baseline("https://cne.hn/api/results", schema)
        assert "https://cne.hn/api/results" in monitor.baselines
        assert monitor.baselines["https://cne.hn/api/results"] == schema

    def test_compute_schema_hash(self):
        """Compute schema hash from keys."""
        monitor = EndpointMonitor()
        hash1 = monitor._compute_schema_hash(["a", "b", "c"])
        hash2 = monitor._compute_schema_hash(["a", "b", "c"])

        # Same keys → same hash (deterministic)
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256

    def test_schema_hash_sensitivity(self):
        """Different keys → different hash."""
        monitor = EndpointMonitor()
        hash1 = monitor._compute_schema_hash(["votes", "timestamp"])
        hash2 = monitor._compute_schema_hash(["votes", "timestamp", "location"])

        assert hash1 != hash2

    def test_merkle_root_single(self):
        """Merkle root of single hash."""
        monitor = EndpointMonitor()
        single_hash = "a" * 64
        root = monitor._merkle_root([single_hash])

        assert root == single_hash

    def test_merkle_root_two(self):
        """Merkle root of two hashes."""
        monitor = EndpointMonitor()
        hash1 = "a" * 64
        hash2 = "b" * 64
        root = monitor._merkle_root([hash1, hash2])

        # Should combine and hash
        assert len(root) == 64
        assert root != hash1 and root != hash2

    def test_merkle_root_odd(self):
        """Merkle root of odd number of hashes."""
        monitor = EndpointMonitor()
        hashes = ["a" * 64, "b" * 64, "c" * 64]
        root = monitor._merkle_root(hashes)

        assert len(root) == 64

    def test_merkle_deterministic(self):
        """Merkle root is deterministic."""
        monitor = EndpointMonitor()
        hashes = ["a" * 64, "b" * 64]
        root1 = monitor._merkle_root(hashes)
        root2 = monitor._merkle_root(hashes)

        assert root1 == root2

    def test_detect_no_baseline(self):
        """No change detected if no baseline exists."""
        monitor = EndpointMonitor()
        schema = EndpointSchema(
            timestamp=time.time(),
            url="https://cne.hn/api/results",
            status_code=200,
            content_type="application/json",
            keys=["votes"],
            schema_hash="abc" * 21 + "defg",
        )

        change = monitor.detect_changes(schema)
        assert change is None  # First time, no baseline

    def test_detect_status_code_change(self):
        """Detect HTTP status code change."""
        monitor = EndpointMonitor()

        baseline = EndpointSchema(
            timestamp=time.time(),
            url="https://cne.hn/api/results",
            status_code=200,
            content_type="application/json",
            keys=["votes"],
            schema_hash="abc" * 21 + "defg",
        )
        monitor.register_baseline(baseline.url, baseline)

        observed = EndpointSchema(
            timestamp=time.time() + 10,
            url="https://cne.hn/api/results",
            status_code=503,
            content_type="application/json",
            keys=["votes"],
            schema_hash="abc" * 21 + "defg",
        )

        change = monitor.detect_changes(observed)
        assert change is not None
        assert change.change_type == "status_code_change"
        assert change.severity == "high"

    def test_detect_schema_divergence(self):
        """Detect schema key changes."""
        monitor = EndpointMonitor()

        baseline = EndpointSchema(
            timestamp=time.time(),
            url="https://cne.hn/api/results",
            status_code=200,
            content_type="application/json",
            keys=["votes", "timestamp"],
            schema_hash="abc" * 21 + "defg",
        )
        monitor.register_baseline(baseline.url, baseline)

        observed = EndpointSchema(
            timestamp=time.time() + 10,
            url="https://cne.hn/api/results",
            status_code=200,
            content_type="application/json",
            keys=["votes", "timestamp", "location"],  # Changed
            schema_hash="xyz" * 21 + "hijk",  # Different hash
        )

        change = monitor.detect_changes(observed)
        assert change is not None
        assert change.change_type == "schema_mismatch"
        assert change.severity == "high"

    def test_schema_merkle_root(self):
        """Compute schema Merkle root."""
        monitor = EndpointMonitor()

        schema1 = EndpointSchema(
            timestamp=time.time(),
            url="https://cne.hn/api/results",
            status_code=200,
            content_type="application/json",
            keys=["votes"],
            schema_hash="a" * 64,
        )

        schema2 = EndpointSchema(
            timestamp=time.time(),
            url="https://cne.hn/api/votes",
            status_code=200,
            content_type="application/json",
            keys=["candidate", "count"],
            schema_hash="b" * 64,
        )

        monitor.register_baseline(schema1.url, schema1)
        monitor.register_baseline(schema2.url, schema2)

        root = monitor.schema_merkle_root()
        assert len(root) == 64
        assert root != "a" * 64 and root != "b" * 64

    def test_forensic_record(self):
        """Export forensic evidence."""
        monitor = EndpointMonitor()

        baseline = EndpointSchema(
            timestamp=time.time(),
            url="https://cne.hn/api/results",
            status_code=200,
            content_type="application/json",
            keys=["votes"],
            schema_hash="abc" * 21 + "defg",
        )
        monitor.register_baseline(baseline.url, baseline)

        observed = EndpointSchema(
            timestamp=time.time() + 10,
            url="https://cne.hn/api/results",
            status_code=503,
            content_type="application/json",
            keys=["votes"],
            schema_hash="abc" * 21 + "defg",
        )
        monitor.detect_changes(observed)

        record = monitor.to_forensic_record()
        assert record["event_type"] == "endpoint_integrity_scan"
        assert record["baselines_count"] == 1
        assert record["changes_detected"] == 1
        assert "schema_merkle_root" in record


class TestEndpointMonitorIntegration:
    """Integration tests with mocked HTTP."""

    @patch("httpx.Client.get")
    def test_scan_endpoint_success(self, mock_get):
        """Scan endpoint successfully."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"votes": 1000, "timestamp": "2026-05-16"}
        mock_get.return_value = mock_response

        monitor = EndpointMonitor()
        schema = monitor.scan_endpoint("https://cne.hn/api/results")

        assert schema is not None
        assert schema.status_code == 200
        assert schema.keys == ["timestamp", "votes"]  # Sorted
        assert schema.is_error is False

    @patch("httpx.Client.get")
    def test_scan_endpoint_http_error(self, mock_get):
        """Scan endpoint with HTTP error."""
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.headers = {"content-type": "text/html"}
        mock_get.return_value = mock_response

        monitor = EndpointMonitor()
        schema = monitor.scan_endpoint("https://cne.hn/api/results")

        assert schema is not None
        assert schema.status_code == 503
        assert schema.is_error is True

    @patch("httpx.Client.get")
    def test_scan_endpoint_timeout(self, mock_get):
        """Scan endpoint with timeout."""
        import httpx

        mock_get.side_effect = httpx.TimeoutException("timeout")

        monitor = EndpointMonitor()
        schema = monitor.scan_endpoint("https://cne.hn/api/results")

        assert schema is not None
        assert schema.is_error is True
        assert "timeout" in schema.error_detail
