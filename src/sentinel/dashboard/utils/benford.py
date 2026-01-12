"""English docstring: Utilities to compute Benford's Law diagnostics.

---
Docstring en español: Utilidades para calcular diagnósticos de la Ley de Benford.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def benford_analysis(series: pd.Series) -> tuple[pd.Series | None, pd.Series | None, float | None]:
    """English docstring: Compute Benford observed and theoretical distributions.

    Args:
        series: Numeric series to analyze.

    Returns:
        A tuple of (observed, theoretical, mean_absolute_deviation_percent).
    ---
    Docstring en español: Calcula distribuciones observada y teórica de Benford.

    Args:
        series: Serie numérica a analizar.

    Returns:
        Una tupla con (observado, teórico, desviación_media_absoluta_porcentaje).
    """

    # Guard against empty or small samples. / Proteger contra muestras vacías o pequeñas.
    if series is None or len(series) < 20:
        return None, None, None

    # Extract first digit (1-9). / Extraer el primer dígito (1-9).
    first_digits = series.astype(str).str.strip().str[0]
    first_digits = pd.to_numeric(first_digits, errors="coerce")
    first_digits = first_digits[(first_digits >= 1) & (first_digits <= 9)]

    if len(first_digits) < 10:
        return None, None, None

    observed = (
        first_digits.value_counts(normalize=True)
        .sort_index()
        .reindex(range(1, 10), fill_value=0.0)
    )
    theoretical = pd.Series(
        [np.log10(1 + 1 / d) for d in range(1, 10)],
        index=range(1, 10),
    )

    deviation = float(np.mean(np.abs(observed - theoretical)) * 100)
    return observed, theoretical, deviation
