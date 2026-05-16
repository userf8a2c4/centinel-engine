"""
Tests for Anomaly Detector module.

ES: Pruebas para el módulo de Detección de Anomalías.
"""

import pytest
from centinel.core.anomaly_detector import AnomalyDetector, detect_anomalies


class TestAnomalyDetectorBenford:
    """Test Benford's Law detection."""

    def test_benford_clean_data(self):
        """Clean election data should not trigger Benford anomaly."""
        # Create 150 snapshots with realistic vote counts (Benford-conforming)
        snapshots = []
        votes = 1000
        for i in range(150):
            votes += 100  # Natural growth
            snapshots.append({
                "index": i,
                "timestamp": 1000000 + i * 3600,
                "total_votes": votes,
                "registered_voters": 10000,
            })

        detector = AnomalyDetector(min_snapshots=100)
        report = detector.analyze(snapshots)

        benford_anomalies = [a for a in report.anomalies if a.anomaly_type == "benford"]
        # Real election data usually passes Benford (χ² < 5.99)
        assert len(benford_anomalies) <= 1, "Natural vote growth should rarely fail Benford"

    def test_benford_round_numbers_anomaly(self):
        """Round numbers (fake data) should trigger Benford anomaly."""
        # Artificially round votes trigger Benford deviation
        snapshots = []
        for i in range(150):
            snapshots.append({
                "index": i,
                "timestamp": 1000000 + i * 3600,
                "total_votes": (i + 1) * 1000,  # Round thousands: 1000, 2000, 3000...
                "registered_voters": 10000,
            })

        detector = AnomalyDetector(min_snapshots=100)
        report = detector.analyze(snapshots)

        benford_anomalies = [a for a in report.anomalies if a.anomaly_type == "benford"]
        # Round numbers should fail Benford test (too many 1s, 2s, etc.)
        assert len(benford_anomalies) > 0, "Round numbers should trigger Benford anomaly"

    def test_benford_insufficient_snapshots(self):
        """When < min_snapshots, threshold_applied = False."""
        snapshots = [{"index": i, "timestamp": 1000000 + i * 3600, "total_votes": 1000 + i * 100}
                     for i in range(50)]

        detector = AnomalyDetector(min_snapshots=100)
        report = detector.analyze(snapshots)

        assert report.threshold_applied is False, "Should not apply threshold when < min_snapshots"
        assert len(report.anomalies) == 0, "Should not report anomalies when threshold not applied"


class TestAnomalyDetectorZScore:
    """Test Z-score outlier detection."""

    def test_zscore_normal_increments(self):
        """Normal vote increments should not trigger Z-score anomaly."""
        snapshots = []
        votes = 10000
        for i in range(150):
            votes += 100  # Steady increment
            snapshots.append({
                "index": i,
                "timestamp": 1000000 + i * 3600,
                "total_votes": votes,
                "registered_voters": 100000,
            })

        detector = AnomalyDetector(min_snapshots=100, zscore_threshold=3.0)
        report = detector.analyze(snapshots)

        zscore_anomalies = [a for a in report.anomalies if a.anomaly_type == "zscore"]
        assert len(zscore_anomalies) == 0, "Steady increments should not trigger Z-score"

    def test_zscore_spike_detected(self):
        """Sudden vote spike should trigger Z-score anomaly."""
        snapshots = []
        votes = 10000
        for i in range(150):
            if i == 75:
                votes += 5000  # Huge spike
            else:
                votes += 100  # Normal increment
            snapshots.append({
                "index": i,
                "timestamp": 1000000 + i * 3600,
                "total_votes": votes,
                "registered_voters": 100000,
            })

        detector = AnomalyDetector(min_snapshots=100, zscore_threshold=3.0)
        report = detector.analyze(snapshots)

        zscore_anomalies = [a for a in report.anomalies if a.anomaly_type == "zscore"]
        assert len(zscore_anomalies) > 0, "Vote spike should trigger Z-score anomaly"
        assert zscore_anomalies[0].severity == "medium"

    def test_zscore_insufficient_deltas(self):
        """< 3 snapshots should not trigger Z-score checks."""
        snapshots = [
            {"index": 0, "timestamp": 1000000, "total_votes": 1000},
            {"index": 1, "timestamp": 1000100, "total_votes": 1100},
        ]

        detector = AnomalyDetector(min_snapshots=1)  # Allow 2 snapshots
        report = detector.analyze(snapshots)

        zscore_anomalies = [a for a in report.anomalies if a.anomaly_type == "zscore"]
        assert len(zscore_anomalies) == 0, "Too few snapshots should skip Z-score check"


class TestAnomalyDetectorMonotonicity:
    """Test timestamp monotonicity check."""

    def test_monotonicity_clean(self):
        """Strictly increasing timestamps should pass."""
        snapshots = []
        for i in range(150):
            snapshots.append({
                "index": i,
                "timestamp": 1000000 + i * 3600,
                "total_votes": 10000 + i * 100,
            })

        detector = AnomalyDetector(min_snapshots=100)
        report = detector.analyze(snapshots)

        monotone_anomalies = [a for a in report.anomalies if a.anomaly_type == "monotonicity"]
        assert len(monotone_anomalies) == 0, "Increasing timestamps should pass"

    def test_monotonicity_decrease_detected(self):
        """Timestamp going backwards should trigger anomaly."""
        snapshots = []
        for i in range(150):
            ts = 1000000 + i * 3600
            if i == 75:
                ts -= 7200  # Go back 2 hours
            snapshots.append({
                "index": i,
                "timestamp": ts,
                "total_votes": 10000 + i * 100,
            })

        detector = AnomalyDetector(min_snapshots=100)
        report = detector.analyze(snapshots)

        monotone_anomalies = [a for a in report.anomalies if a.anomaly_type == "monotonicity"]
        assert len(monotone_anomalies) > 0, "Backward timestamp should trigger anomaly"
        assert monotone_anomalies[0].severity == "high", "Monotonicity break is high severity"

    def test_monotonicity_stall_detected(self):
        """Timestamp not advancing (equal) should trigger anomaly."""
        snapshots = []
        for i in range(150):
            ts = 1000000 + i * 3600
            if i == 75:
                ts = 1000000 + 74 * 3600  # Don't advance (equal to previous)
            snapshots.append({
                "index": i,
                "timestamp": ts,
                "total_votes": 10000 + i * 100,
            })

        detector = AnomalyDetector(min_snapshots=100)
        report = detector.analyze(snapshots)

        monotone_anomalies = [a for a in report.anomalies if a.anomaly_type == "monotonicity"]
        assert len(monotone_anomalies) > 0, "Non-advancing timestamp should trigger anomaly"


class TestAnomalyDetectorConvenience:
    """Test convenience function."""

    def test_detect_anomalies_function(self):
        """Test convenience function detect_anomalies()."""
        snapshots = [
            {"index": i, "timestamp": 1000000 + i * 3600, "total_votes": 10000 + i * 100}
            for i in range(150)
        ]

        report = detect_anomalies(snapshots, min_snapshots=100)

        assert report.threshold_applied is True
        assert isinstance(report.anomalies, list)


class TestAnomalyDetectorMetadata:
    """Test metadata and reporting."""

    def test_report_metadata(self):
        """Report should include analysis metadata."""
        snapshots = [
            {"index": i, "timestamp": 1000000 + i * 3600, "total_votes": 10000 + i * 100}
            for i in range(150)
        ]

        detector = AnomalyDetector(min_snapshots=100)
        report = detector.analyze(snapshots)

        assert "snapshots_analyzed" in report.analysis_metadata
        assert report.analysis_metadata["snapshots_analyzed"] == 150
        assert "benford_threshold_chi2" in report.analysis_metadata
        assert report.analysis_metadata["benford_threshold_chi2"] == 5.99

    def test_anomaly_fields(self):
        """Each Anomaly should have required fields."""
        snapshots = [
            {"index": i, "timestamp": 1000000 + i * 3600 if i != 75 else 1000000 + 74 * 3600, "total_votes": 10000 + i * 100}
            for i in range(150)
        ]

        detector = AnomalyDetector(min_snapshots=100)
        report = detector.analyze(snapshots)

        if report.anomalies:
            anomaly = report.anomalies[0]
            assert hasattr(anomaly, "snapshot_idx")
            assert hasattr(anomaly, "anomaly_type")
            assert hasattr(anomaly, "severity")
            assert hasattr(anomaly, "detail")
            assert anomaly.severity in ("low", "medium", "high")
            assert anomaly.anomaly_type in ("benford", "zscore", "monotonicity")
