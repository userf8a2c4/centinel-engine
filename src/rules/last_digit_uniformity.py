"""Last-digit uniformity rule."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from .base_rule import BaseRule
from ..utils.stats import chi_square_statistic, last_digit_distribution, uniform_expected_counts


class LastDigitUniformityRule(BaseRule):
    """Checks last-digit uniformity for candidate votes."""

    name = "last_digit_uniformity"

    def evaluate(
        self,
        previous_data: Optional[Dict[str, Any]],
        current_data: Dict[str, Any],
    ) -> Tuple[str, Dict[str, Any]]:
        candidates = current_data.get("candidates", [])
        votes = [candidate.get("votes", 0) for candidate in candidates]
        min_samples = int(self.params.get("min_samples", 50))
        if len(votes) < min_samples:
            return "warn", {"message": "Insufficient samples for last-digit check."}

        distribution = last_digit_distribution(votes)
        total = sum(distribution.values())
        if total < min_samples:
            return "warn", {"message": "Not enough valid vote counts."}

        observed = [distribution.get(digit, 0) for digit in range(10)]
        expected = uniform_expected_counts(total, 10)
        chi_stat = chi_square_statistic(observed, expected)

        deviation_pct = max(
            abs((distribution.get(digit, 0) / total * 100) - 10)
            for digit in range(10)
        )
        threshold = float(self.params.get("deviation_pct", 20))

        status = "pass" if deviation_pct <= threshold else "fail"

        return (
            status,
            {
                "chi_square": round(chi_stat, 4),
                "deviation_pct": round(deviation_pct, 2),
                "threshold": threshold,
                "min_samples": min_samples,
            },
        )
