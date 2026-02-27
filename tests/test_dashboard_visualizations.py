"""Tests for dashboard scientific visualizations utilities."""

import pandas as pd

from dashboard.utils.visualizations import compute_benford_statistics


def test_compute_benford_statistics_balanced_distribution() -> None:
    df = pd.DataFrame(
        {
            "digit": list(range(1, 10)),
            "expected": [30.1, 17.6, 12.5, 9.7, 7.9, 6.7, 5.8, 5.1, 4.6],
            "observed": [30.0, 17.7, 12.4, 9.8, 7.9, 6.7, 5.8, 5.1, 4.6],
        }
    )

    p_value, z_score = compute_benford_statistics(df, sample_size=5000)

    assert 0.0 <= p_value <= 1.0
    assert z_score < 1.0


def test_compute_benford_statistics_deviated_distribution() -> None:
    df = pd.DataFrame(
        {
            "digit": list(range(1, 10)),
            "expected": [30.1, 17.6, 12.5, 9.7, 7.9, 6.7, 5.8, 5.1, 4.6],
            "observed": [20.0, 25.0, 14.0, 10.0, 9.0, 8.0, 6.0, 5.0, 3.0],
        }
    )

    p_value, z_score = compute_benford_statistics(df, sample_size=5000)

    assert p_value < 0.05
    assert z_score > 3.0
