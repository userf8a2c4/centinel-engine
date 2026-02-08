"""Regla ML para detectar outliers en cambios relativos de votos.

ML rule to detect outliers in relative vote changes.
"""

from __future__ import annotations

import collections
import logging
from typing import Dict, List, Optional

from sentinel.core.rules.common import extract_department, extract_total_votes


_HISTORY: Dict[str, List[float]] = collections.defaultdict(list)
logger = logging.getLogger(__name__)


def apply(
    current_data: dict, previous_data: Optional[dict], config: dict
) -> List[dict]:
    """
    Detecta outliers estadísticos en cambios relativos con Isolation Forest.

    La regla calcula el cambio porcentual de votos totales entre snapshots y lo
    incorpora a una serie histórica por departamento. Con suficientes puntos, se
    entrena un modelo Isolation Forest para identificar saltos atípicos. Si el punto
    actual es marcado como outlier, se genera una alerta de anomalía ML.

    Args:
        current_data: Snapshot JSON actual del CNE.
        previous_data: Snapshot JSON anterior (None en el primer snapshot).
        config: Sección de configuración específica de la regla desde config.yaml.

    Returns:
        Lista de alertas en formato estándar (vacía si todo normal).

    English:
        Detects statistical outliers in relative vote changes using Isolation Forest.

        The rule computes the percentage change in total votes between snapshots and
        stores it in a department-level history. Once enough points exist, an
        Isolation Forest model flags abnormal jumps; if the current point is an
        outlier, an ML anomaly alert is emitted.

    Args:
        current_data: Current CNE JSON snapshot.
        previous_data: Previous JSON snapshot (None for the first snapshot).
        config: Rule-specific configuration section from config.yaml.

    Returns:
        List of alerts in the standard format (empty if normal).
    """
    alerts: List[dict] = []
    if not previous_data:
        return alerts

    current_total = extract_total_votes(current_data)
    previous_total = extract_total_votes(previous_data)
    if not current_total or not previous_total:
        return alerts
    if previous_total <= 0:
        return alerts

    relative_change_pct = ((current_total - previous_total) / previous_total) * 100
    department = extract_department(current_data)
    history = _HISTORY[department]
    history.append(relative_change_pct)

    max_history = int(config.get("max_history", 200))
    if len(history) > max_history:
        del history[: len(history) - max_history]

    min_samples = int(config.get("min_samples", 5))
    if len(history) < min_samples:
        return alerts

    contamination = float(config.get("contamination", 0.1))
    try:
        from sklearn.ensemble import IsolationForest
    except ModuleNotFoundError:
        logger.warning("sklearn_missing rule=ml_outliers")
        return alerts

    model = IsolationForest(contamination=contamination, random_state=42)
    values = [[value] for value in history]
    model.fit(values)
    predictions = model.predict(values)
    if predictions[-1] == -1:
        alerts.append(
            {
                "type": "Outlier Estadístico ML",
                "severity": "Medium",
                "department": department,
                "justification": (
                    "Isolation Forest detectó un cambio relativo atípico. "
                    f"delta_pct={relative_change_pct:.2f}%, "
                    f"contamination={contamination}, muestras={len(history)}."
                ),
            }
        )

    return alerts
