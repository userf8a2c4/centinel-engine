"""Regla de spikes en series temporales para anomalías temporales.

Time-series spike rule for temporary anomalies.
"""

from typing import List


def detect_spike_in_time_series(
    timestamps: List[str],
    values: List[int],
    suspicious_window_start: str = "02:00",
    suspicious_window_end: str = "04:00",
) -> bool:
    """
    Detecta spikes sospechosos en ventana horaria (ej. madrugada).
    Detects suspicious spikes within a time window (e.g., early morning).

    Args:
        timestamps (List[str]): Lista de timestamps (formato HH:MM).
        timestamps (List[str]): List of timestamps (HH:MM format).
        values (List[int]): Valores acumulados o incrementos.
        values (List[int]): Accumulated values or increments.
        suspicious_window_start/end (str): Ventana horaria sospechosa.
        suspicious_window_start/end (str): Suspicious time window.

    Returns:
        bool: True si hay spike significativo en la ventana.
        bool: True if there is a significant spike within the window.
    """
    # Implementación simple: suma de incrementos en ventana > 30% del total.
    # Simple implementation: sum of increments in window > 30% of total.
    total = sum(values)
    if total == 0:
        return False

    spike_sum = 0
    for ts, val in zip(timestamps, values):
        hour = int(ts.split(":")[0])
        if int(suspicious_window_start.split(":")[0]) <= hour < int(suspicious_window_end.split(":")[0]):
            spike_sum += val

    return (spike_sum / total) > 0.30  # Umbral temporal 30%. / Temporary threshold 30%.
