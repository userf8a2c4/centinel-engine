"""English docstring: Shared constants for the Sentinel dashboard.

---
Docstring en español: Constantes compartidas para el dashboard de Sentinel.
"""

# Department list used for filters and data simulation. / Lista de departamentos usada para filtros y simulación.
DEPARTMENTS = [
    "Cortés",
    "Francisco Morazán",
    "Atlántida",
    "Comayagua",
    "Choluteca",
    "Yoro",
]

# Political parties list used across the dashboard. / Lista de partidos usada en todo el dashboard.
PARTIES = ["Libre", "Nacional", "PSH", "Otros"]

# Benford deviation alert threshold (percentage points). / Umbral de alerta de desviación Benford (puntos porcentuales).
BENFORD_THRESHOLD = 5.0

# Cache settings (seconds). / Configuración de cache (segundos).
DATA_CACHE_TTL = 1800
