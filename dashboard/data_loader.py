"""English docstring: Data loading utilities for Sentinel dashboard.

---
Docstring en español: Utilidades de carga de datos para el dashboard Sentinel.
"""

from __future__ import annotations

import hashlib
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st

from dashboard.utils.constants import DATA_CACHE_TTL, DEPARTMENTS, PARTIES


def _simulate_snapshot_rows(timestamps: pd.DatetimeIndex) -> list[dict[str, object]]:
    """English docstring: Generate realistic snapshot rows for every timestamp/department.

    Args:
        timestamps: Pandas datetime index used as snapshot time points.

    Returns:
        A list of dictionaries representing snapshot rows.
    ---
    Docstring en español: Genera filas realistas de snapshots por timestamp/departamento.

    Args:
        timestamps: Índice de fechas usado como puntos de tiempo.

    Returns:
        Lista de diccionarios con filas de snapshots.
    """

    rng = np.random.default_rng(42)
    rows: list[dict[str, object]] = []

    for ts in timestamps:
        for department in DEPARTMENTS:
            total_votes = int(rng.integers(8000, 60000))
            shares = rng.dirichlet([4.2, 3.6, 1.5, 0.7])
            party_votes = rng.multinomial(total_votes, shares)
            hash_input = f"{ts.isoformat()}_{department}_{party_votes.tolist()}"
            hash_val = hashlib.sha256(hash_input.encode()).hexdigest()

            rows.append(
                {
                    "timestamp": ts,
                    "departamento": department,
                    "total_votos": total_votes,
                    **{party: int(v) for party, v in zip(PARTIES, party_votes)},
                    "hash": hash_val,
                }
            )

    return rows


@st.cache_data(ttl=DATA_CACHE_TTL)
def load_data() -> pd.DataFrame:
    """English docstring: Load (simulated) CNE snapshots with caching.

    Returns:
        DataFrame containing snapshot rows.
    ---
    Docstring en español: Carga snapshots simulados del CNE con caching.

    Returns:
        DataFrame con filas de snapshots.
    """

    # Simulate snapshots every 15 minutes. / Simular snapshots cada 15 minutos.
    start = datetime(2025, 11, 30, 18, 0)
    end = datetime(2025, 12, 1, 6, 0)
    timestamps = pd.date_range(start, end, freq="15min")

    rows = _simulate_snapshot_rows(timestamps)
    return pd.DataFrame(rows)
