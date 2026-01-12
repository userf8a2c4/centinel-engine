# Reglas de Análisis / Analysis Rules

Esta carpeta contiene una regla de análisis por archivo. Cada regla es independiente, autocontenida y sigue estrictamente el estándar definido a continuación para facilitar mantenimiento, colaboración y extensión futura.

## Estándar de Regla / Rule Standard
- Nombre de archivo: inglés snake_case (ej. `benford_law_rule.py`).
- Función única principal: `apply(current_data: dict, previous_data: Optional[dict], config: dict) -> List[dict]`
- Docstring obligatoria: Google style bilingüe (español completo primero, luego inglés completo).
- Retorna lista de alertas (vacía si no hay violación).
- Formato estándar de alerta (dict):
  {
      "type": "Nombre de la alerta en español",
      "severity": "Low|Medium|High",
      "justification": "Explicación matemática detallada con valores numéricos...",
      "department": "XX"  # opcional, si aplica por departamento
  }
- Manejo robusto de errores: división por cero, datos nulos/missing, timestamps inválidos → return [] sin crash.
- Todos los umbrales deben tomarse de `config` (con defaults razonables).

## Reglas actuales / Current Rules
(Se actualizará automáticamente al finalizar)
- benford_law_rule.py
- ml_outliers_rule.py
- basic_diff_rule.py
- participation_anomaly_rule.py
- trend_shift_rule.py
- processing_speed_rule.py
- irreversibility_rule.py
