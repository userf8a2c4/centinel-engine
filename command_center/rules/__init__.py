"""Reglas de detección individuales para el centro de comando.

Individual detection rules for the command center.
"""

from .benford_first_digit import check_benford_first_digit
from .benford_second_digit import benford_second_digit_test, extract_second_digit
from .consistencia_agregada import check_consistencia_agregada
from .correlacion_departamental import check_correlacion_departamental
from .last_digit_uniformity import last_digit_uniformity_test
from .nulos_anomalias import check_nulos_anomalias
from .spike_time_series import detect_spike_in_time_series
from .turnout_zscore import check_turnout_zscore

__all__ = [
    "check_benford_first_digit",
    "check_consistencia_agregada",
    "check_correlacion_departamental",
    "check_nulos_anomalias",
    "check_turnout_zscore",
    "benford_second_digit_test",
    "detect_spike_in_time_series",
    "extract_second_digit",
    "last_digit_uniformity_test",
]
