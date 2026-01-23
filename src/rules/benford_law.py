"""Benford's law rule."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .base_rule import BaseRule
from ..utils.stats import (
    benford_expected_distribution,
    chi_square_statistic,
    first_digit_distribution,
)


class BenfordLawRule(BaseRule):
    """Checks Benford distribution for candidate votes."""

    name = "benford_law"

    def evaluate(
        self,
        previous_data: Optional[Dict[str, Any]],
        current_data: Dict[str, Any],
    ) -> Tuple[str, Dict[str, Any]]:
        candidates = current_data.get("candidates", [])
        votes = [candidate.get("votes", 0) for candidate in candidates]
        min_samples = int(self.params.get("min_samples", 10))
        if len(votes) < min_samples:
            return "warn", {"message": "Insufficient samples for Benford check."}

        distribution = first_digit_distribution(votes)
        total = sum(distribution.values())
        if total < min_samples:
            return "warn", {"message": "Not enough valid vote counts."}

        expected_pct = benford_expected_distribution()
        observed_counts = [distribution.get(digit, 0) for digit in range(1, 10)]
        expected_counts = [expected_pct[digit] / 100 * total for digit in range(1, 10)]
        chi_stat = chi_square_statistic(observed_counts, expected_counts)

        deviation_pct = max(
            abs((distribution.get(digit, 0) / total * 100) - expected_pct[digit])
            for digit in range(1, 10)
        )
        threshold = float(self.params.get("deviation_pct", 15))
        chi_threshold = float(self.params.get("chi_square_threshold", 0.05))

        status = "pass"
        if deviation_pct > threshold or chi_stat > chi_threshold:
            status = "fail"

        return (
            status,
            {
                "chi_square": round(chi_stat, 4),
                "deviation_pct": round(deviation_pct, 2),
                "threshold": threshold,
                "min_samples": min_samples,
            },
        )
