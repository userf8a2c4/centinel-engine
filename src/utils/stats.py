"""Statistical helpers for integrity checks and dashboards."""

from __future__ import annotations

import collections
import math
from typing import Iterable, List, Dict


def benford_expected_distribution() -> Dict[int, float]:
    """Return expected Benford distribution percentages for digits 1-9."""
    return {digit: math.log10(1 + 1 / digit) * 100 for digit in range(1, 10)}


def chi_square_statistic(observed: List[int], expected: List[float]) -> float:
    """Compute chi-square statistic for observed vs expected counts."""
    total = 0.0
    for obs, exp in zip(observed, expected):
        if exp <= 0:
            continue
        total += (obs - exp) ** 2 / exp
    return total


def first_digit_distribution(values: Iterable[int]) -> Dict[int, int]:
    """Compute a count distribution of first digits for positive integers."""
    digits = [int(str(value)[0]) for value in values if value and value > 0]
    return dict(collections.Counter(digits))


def last_digit_distribution(values: Iterable[int]) -> Dict[int, int]:
    """Compute a count distribution of last digits for integers."""
    digits = [abs(value) % 10 for value in values if value is not None]
    return dict(collections.Counter(digits))


def uniform_expected_counts(total: int, buckets: int) -> List[float]:
    """Generate expected uniform counts for chi-square tests."""
    if buckets <= 0:
        return []
    expected = total / buckets
    return [expected] * buckets
