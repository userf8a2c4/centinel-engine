"""Reglas de detección individuales para dev-v4.

Individual detection rules for dev-v4.
"""

from .benford_second_digit import benford_second_digit_test, extract_second_digit
from .last_digit_uniformity import last_digit_uniformity_test
from .spike_time_series import detect_spike_in_time_series

__all__ = [
    "benford_second_digit_test",
    "detect_spike_in_time_series",
    "extract_second_digit",
    "last_digit_uniformity_test",
]
