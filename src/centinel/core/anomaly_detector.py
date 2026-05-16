"""
Anomaly Detection Module for Centinel Engine.

ES: Módulo de Detección de Anomalías para Centinel Engine.
   Detecta patrones sospechosos en snapshots mediante:
   - Ley de Benford (distribución de primeros dígitos)
   - Z-score (outliers en métricas electorales)
   - Monotonía de timestamps

EN: Detects suspicious patterns in snapshots via:
   - Benford's Law (first-digit distribution)
   - Z-score (outliers in election metrics)
   - Timestamp monotonicity

This module is inspired by anomaly detection standards in Brazil (TSE),
Mexico (INE), and academic electoral verification literature.

References:
  - Brazil TSE: Benford's Law applied to election results
  - Mexico INE: Congruence rules and statistical thresholds
  - Academic: Mebane (2006) "Election Anomalies" on Benford distribution
"""

from __future__ import annotations

import logging
import statistics
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger("centinel.anomaly_detector")

# Benford's Law: expected frequency of first digits 1–9
# (Ley de Benford: frecuencia esperada de primeros dígitos 1–9)
_BENFORD_EXPECTED = {
    1: 0.301, 2: 0.176, 3: 0.125, 4: 0.097,
    5: 0.079, 6: 0.067, 7: 0.058, 8: 0.051, 9: 0.046,
}


@dataclass
class Anomaly:
    """A single anomaly detected in a snapshot.

    ES: Una sola anomalía detectada en un snapshot.
    """
    snapshot_idx: int
    anomaly_type: str  # "benford", "zscore", "monotonicity"
    severity: str     # "low", "medium", "high"
    detail: str       # Human-readable explanation
    metric: Optional[str] = None  # Which metric was affected (e.g., "votes", "timestamp")
    value: Optional[float] = None  # The actual value that triggered


@dataclass
class AnomalyReport:
    """Summary of anomalies found in a snapshot list.

    ES: Resumen de anomalías encontradas en una lista de snapshots.
    """
    anomalies: list[Anomaly]
    threshold_applied: bool  # True if min_snapshots threshold was met
    analysis_metadata: dict[str, Any]  # Debug info: counts, thresholds used


class AnomalyDetector:
    """Detects electoral anomalies using statistical heuristics.

    ES: Detecta anomalías electorales usando heurísticas estadísticas.

    Design:
    - Does NOT block or reject data (non-fatal)
    - Flags suspicious patterns for auditor review
    - Degrades gracefully when data is insufficient
    - Does not apply rules until >= min_snapshots (avoids overfitting on sparse data)

    Operationally inspired by:
    - Brazil (TSE): Benford's Law check on vote counts
    - Mexico (INE): Z-score thresholds on vote changes
    - Honduras: Real-time anomaly flagging for election-night decision support
    """

    def __init__(
        self,
        min_snapshots: int = 100,
        benford_chi2_threshold: float = 5.99,  # χ² critical value (p<0.05)
        zscore_threshold: float = 3.0,
    ) -> None:
        """Initialize detector with thresholds.

        Args:
            min_snapshots: Don't apply rules until this many snapshots exist.
                          (Avoid false positives on sparse election-night data.)
            benford_chi2_threshold: χ² statistic threshold (5.99 ≈ p<0.05 for df=8).
            zscore_threshold: Number of standard deviations to flag as outlier (3.0 = 99.7%).
        """
        self.min_snapshots = min_snapshots
        self.benford_chi2_threshold = benford_chi2_threshold
        self.zscore_threshold = zscore_threshold

    def analyze(self, snapshots: list[dict]) -> AnomalyReport:
        """Analyze a list of snapshots for anomalies.

        Args:
            snapshots: List of snapshot dicts. Each should have:
                      - "index" (int): ordinal position
                      - "timestamp" (int/str): Unix timestamp or ISO string
                      - "total_votes" (int): votes cast
                      - "registered_voters" (int): eligible voters
                      - "null_votes", "blank_votes", "valid_votes" (int)

        Returns:
            AnomalyReport: List of detected anomalies + metadata.
        """
        anomalies: list[Anomaly] = []
        threshold_applied = len(snapshots) >= self.min_snapshots

        if not threshold_applied:
            logger.debug(
                "anomaly_detector_insufficient_data snapshots=%d min_required=%d",
                len(snapshots),
                self.min_snapshots,
            )
            return AnomalyReport(
                anomalies=[],
                threshold_applied=False,
                analysis_metadata={"snapshots": len(snapshots), "min_required": self.min_snapshots},
            )

        # Extract metrics for statistical analysis
        # ES: Extraer métricas para análisis estadístico
        votes = [s.get("total_votes", 0) for s in snapshots if isinstance(s.get("total_votes"), (int, float))]
        timestamps = []
        for s in snapshots:
            ts = s.get("timestamp")
            if isinstance(ts, (int, float)):
                timestamps.append(ts)
            elif isinstance(ts, str):
                try:
                    timestamps.append(float(ts))
                except ValueError:
                    pass

        # Check 1: Benford's Law on vote counts
        # ES: Chequeo 1: Ley de Benford en conteos de votos
        if votes:
            benford_anomalies = self._check_benford(votes)
            anomalies.extend(benford_anomalies)

        # Check 2: Z-score outliers on vote deltas
        # ES: Chequeo 2: Z-score en cambios de votos
        if len(votes) > 2:
            zscore_anomalies = self._check_zscore_deltas(votes)
            anomalies.extend(zscore_anomalies)

        # Check 3: Timestamp monotonicity
        # ES: Chequeo 3: Monotonicidad de timestamps
        if len(timestamps) > 1:
            monotone_anomalies = self._check_timestamp_monotonicity(timestamps)
            anomalies.extend(monotone_anomalies)

        metadata = {
            "snapshots_analyzed": len(snapshots),
            "votes_analyzed": len(votes),
            "timestamps_analyzed": len(timestamps),
            "benford_threshold_chi2": self.benford_chi2_threshold,
            "zscore_threshold": self.zscore_threshold,
            "min_snapshots_for_rules": self.min_snapshots,
        }

        return AnomalyReport(
            anomalies=anomalies,
            threshold_applied=True,
            analysis_metadata=metadata,
        )

    def _check_benford(self, values: list[int | float]) -> list[Anomaly]:
        """Check if first digits follow Benford's Law.

        Uses χ² (chi-square) goodness-of-fit test.
        ES: Usa prueba χ² de bondad de ajuste.
        """
        if not values:
            return []

        # Extract first digits
        first_digits = []
        for v in values:
            if v > 0:
                first_d = int(str(int(v))[0])  # First digit
                if 1 <= first_d <= 9:
                    first_digits.append(first_d)

        if len(first_digits) < 20:  # Need minimum sample
            return []

        # Count observed frequencies
        observed = {d: 0 for d in range(1, 10)}
        for d in first_digits:
            observed[d] += 1

        # Compute χ² statistic
        chi2 = 0.0
        n = len(first_digits)
        for d in range(1, 10):
            expected_count = _BENFORD_EXPECTED[d] * n
            if expected_count > 0:
                chi2 += ((observed[d] - expected_count) ** 2) / expected_count

        # Check against threshold
        anomalies = []
        if chi2 > self.benford_chi2_threshold:
            anomalies.append(
                Anomaly(
                    snapshot_idx=0,  # Will be overridden by caller
                    anomaly_type="benford",
                    severity="medium",
                    detail=f"First-digit distribution χ²={chi2:.2f} exceeds Benford threshold ({self.benford_chi2_threshold})",
                    metric="votes",
                    value=chi2,
                )
            )
            logger.warning(
                "anomaly_benford_detected chi2=%.2f threshold=%.2f first_digits=%d",
                chi2,
                self.benford_chi2_threshold,
                len(first_digits),
            )

        return anomalies

    def _check_zscore_deltas(self, values: list[int | float]) -> list[Anomaly]:
        """Check for outlier vote deltas using Z-score.

        ES: Detecta cambios inusuales entre snapshots consecutivos.
        """
        if len(values) < 2:
            return []

        # Compute deltas (change in votes between snapshots)
        deltas = [values[i] - values[i - 1] for i in range(1, len(values))]

        if len(deltas) < 3:
            return []

        try:
            mean_delta = statistics.mean(deltas)
            stdev_delta = statistics.stdev(deltas)
        except statistics.StatisticsError:
            return []

        if stdev_delta == 0:
            return []

        # Find outliers
        anomalies = []
        for i, delta in enumerate(deltas):
            z = (delta - mean_delta) / stdev_delta
            if abs(z) > self.zscore_threshold:
                anomalies.append(
                    Anomaly(
                        snapshot_idx=i + 1,  # Delta is between i and i+1
                        anomaly_type="zscore",
                        severity="medium",
                        detail=f"Vote delta {delta} is {abs(z):.1f}σ from mean (unusual magnitude)",
                        metric="vote_delta",
                        value=z,
                    )
                )
                logger.warning(
                    "anomaly_zscore_detected snapshot_idx=%d delta=%d zscore=%.2f",
                    i + 1,
                    delta,
                    z,
                )

        return anomalies

    def _check_timestamp_monotonicity(self, timestamps: list[float]) -> list[Anomaly]:
        """Check if timestamps are strictly increasing (monotonic).

        ES: Verifica que los timestamps siempre avancen (no retrocedan).
        """
        anomalies = []
        for i in range(1, len(timestamps)):
            if timestamps[i] <= timestamps[i - 1]:
                anomalies.append(
                    Anomaly(
                        snapshot_idx=i,
                        anomaly_type="monotonicity",
                        severity="high",
                        detail=f"Timestamp did not advance: {timestamps[i-1]} -> {timestamps[i]} (non-monotonic)",
                        metric="timestamp",
                        value=timestamps[i],
                    )
                )
                logger.error(
                    "anomaly_monotonicity_violated snapshot_idx=%d prev_ts=%.0f curr_ts=%.0f",
                    i,
                    timestamps[i - 1],
                    timestamps[i],
                )

        return anomalies


# Convenience function for one-off anomaly checks
def detect_anomalies(
    snapshots: list[dict],
    min_snapshots: int = 100,
    benford_threshold: float = 5.99,
    zscore_threshold: float = 3.0,
) -> AnomalyReport:
    """Quick anomaly detection without instantiating detector.

    ES: Detección rápida sin instanciar AnomalyDetector.
    """
    detector = AnomalyDetector(
        min_snapshots=min_snapshots,
        benford_chi2_threshold=benford_threshold,
        zscore_threshold=zscore_threshold,
    )
    return detector.analyze(snapshots)
