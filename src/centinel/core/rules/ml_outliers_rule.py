"""Regla ML para detectar outliers en cambios relativos de votos. (ML rule to detect outliers in relative vote changes.)"""

from __future__ import annotations

import logging
import os
import sqlite3
from typing import List, Optional

from centinel.core.rules.common import extract_department, extract_total_votes
from centinel.core.rules.registry import rule

logger = logging.getLogger(__name__)

_DEFAULT_DB_PATH = "reports/ml_outliers_history.db"


class _HistoryStore:
    """SQLite-backed history store for ML outlier detection.

    Replaces the previous in-memory ``_HISTORY`` dict so that data
    survives process restarts.

    Almacén de historial respaldado por SQLite para detección de outliers ML.
    Reemplaza el diccionario en memoria ``_HISTORY`` para que los datos
    sobrevivan reinicios del proceso.
    """

    def __init__(self, db_path: str) -> None:
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self._conn = sqlite3.connect(db_path)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS ml_history (
                department TEXT NOT NULL,
                seq INTEGER NOT NULL,
                value REAL NOT NULL,
                PRIMARY KEY (department, seq)
            )
            """)
        self._conn.commit()

    def append(self, department: str, value: float, max_history: int) -> List[float]:
        """Append a value and return the trimmed history for *department*."""
        cursor = self._conn.execute(
            "SELECT COALESCE(MAX(seq), -1) FROM ml_history WHERE department = ?",
            (department,),
        )
        next_seq = cursor.fetchone()[0] + 1

        self._conn.execute(
            "INSERT INTO ml_history (department, seq, value) VALUES (?, ?, ?)",
            (department, next_seq, value),
        )

        # Trim old entries beyond max_history
        self._conn.execute(
            """
            DELETE FROM ml_history
            WHERE department = ? AND seq <= (
                SELECT MAX(seq) - ? FROM ml_history WHERE department = ?
            )
            """,
            (department, max_history, department),
        )
        self._conn.commit()

        rows = self._conn.execute(
            "SELECT value FROM ml_history WHERE department = ? ORDER BY seq",
            (department,),
        ).fetchall()
        return [r[0] for r in rows]

    def close(self) -> None:
        self._conn.close()


_store: Optional[_HistoryStore] = None


def _get_store(db_path: str) -> _HistoryStore:
    global _store
    if _store is None:
        _store = _HistoryStore(db_path)
    return _store


@rule(
    name="Outliers ML (Isolation Forest)",
    severity="Medium",
    description="Detecta outliers estadísticos en cambios relativos de votos con ML.",
    config_key="ml_outliers",
)
def apply(current_data: dict, previous_data: Optional[dict], config: dict) -> List[dict]:
    """
    Detecta outliers estadísticos en cambios relativos con Isolation Forest.
    (Detect statistical outliers in relative vote changes using Isolation Forest.)

    La regla calcula el cambio porcentual de votos totales entre snapshots y lo
    incorpora a una serie histórica por departamento. Con suficientes puntos, se
    entrena un modelo Isolation Forest para identificar saltos atípicos. Si el punto
    actual es marcado como outlier, se genera una alerta de anomalía ML. (The rule
    computes the percentage change in total votes between snapshots and stores it
    in a department-level history. Once enough points exist, an Isolation Forest
    model flags abnormal jumps; if the current point is an outlier, an ML anomaly
    alert is emitted.)

    Args:
        current_data: Snapshot JSON actual del CNE. (Current CNE JSON snapshot.)
        previous_data: Snapshot JSON anterior (None en el primer snapshot). (Previous JSON snapshot (None for the first snapshot).)
        config: Sección de configuración específica de la regla desde config.yaml. (Rule-specific configuration section from config.yaml.)

    Returns:
        Lista de alertas en formato estándar (vacía si todo normal). (List of alerts in the standard format (empty if normal).)
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

    max_history = int(config.get("max_history", 200))
    db_path = config.get("history_db_path", _DEFAULT_DB_PATH)
    store = _get_store(db_path)
    history = store.append(department, relative_change_pct, max_history)

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
