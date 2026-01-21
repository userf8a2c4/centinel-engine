# Reglas de análisis

## Español

Esta carpeta contiene una regla de análisis por archivo. Cada regla es independiente, autocontenida y sigue estrictamente el estándar definido a continuación para facilitar mantenimiento, colaboración y extensión futura.

### Estándar de regla
- Nombre de archivo: inglés snake_case (ej. `benford_law_rule.py`).
- Función única principal: `apply(current_data: dict, previous_data: Optional[dict], config: dict) -> List[dict]`.
- Docstring obligatoria: estilo Google bilingüe (español completo primero, luego inglés completo).
- Retorna lista de alertas (vacía si no hay violación).
- Formato estándar de alerta (dict):
  {
      "type": "Nombre de la alerta en español",
      "severity": "Low|Medium|High",
      "justification": "Explicación matemática detallada con valores numéricos...",
      "department": "XX"  # opcional, si aplica por departamento
  }
- Manejo robusto de errores: división por cero, datos nulos/missing, timestamps inválidos → `return []` sin fallar.
- Todos los umbrales deben tomarse de `config` (con defaults razonables).

### Reglas actuales
(Se actualizará automáticamente al finalizar)
- benford_law_rule.py
- ml_outliers_rule.py
- basic_diff_rule.py
- participation_anomaly_rule.py
- trend_shift_rule.py
- processing_speed_rule.py
- irreversibility_rule.py

---

## English

This folder contains one analysis rule per file. Each rule is independent, self-contained, and follows the standard below to simplify maintenance, collaboration, and future extension.

### Rule standard
- File name: English snake_case (e.g., `benford_law_rule.py`).
- Single main function: `apply(current_data: dict, previous_data: Optional[dict], config: dict) -> List[dict]`.
- Required docstring: Google style bilingual (full Spanish first, then full English).
- Returns a list of alerts (empty if no violation).
- Standard alert format (dict):
  {
      "type": "Alert name in Spanish",
      "severity": "Low|Medium|High",
      "justification": "Detailed mathematical explanation with numeric values...",
      "department": "XX"  # optional, if applicable by department
  }
- Robust error handling: divide by zero, null/missing data, invalid timestamps → `return []` without crashing.
- All thresholds must come from `config` (with reasonable defaults).

### Current rules
(To be updated automatically at the end)
- benford_law_rule.py
- ml_outliers_rule.py
- basic_diff_rule.py
- participation_anomaly_rule.py
- trend_shift_rule.py
- processing_speed_rule.py
- irreversibility_rule.py
