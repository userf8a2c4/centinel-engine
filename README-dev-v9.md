# Centinel Engine (dev-v9)

## 4. Análisis Forense del Escrutinio Especial de Actas Inconsistentes

El módulo `src/auditor/inconsistent_acts.py` implementa una separación estricta de capas:

- **normal_votes**: deltas de votos observados cuando el contador de inconsistentes no disminuye.
- **special_scrutiny_votes**: deltas de votos incorporados exactamente en ciclos donde el conteo de actas inconsistentes baja.

### Algoritmo de separación y eventos

1. Detecta dinámicamente la clave de inconsistentes en el JSON (`actasInconsistentes`, variantes, o coincidencias por patrones) y la persiste en `config/inconsistent_key.json`.
2. En cada ciclo (`≤5 min`), calcula:
   - `delta_actas = previous_inconsistent_count - current_inconsistent_count`.
   - deltas de voto por candidato.
3. Clasifica eventos:
   - `resolution`: `delta_actas > 0`.
   - `bulk_resolution`: `delta_actas >= 300` (configurable).
   - `stagnation`: contador sin cambio por `>= 6` ciclos (configurable).

### Pruebas estadísticas incluidas

- **Diferencia de proporciones** (z-score) entre capa especial y capa normal.
- **Chi-cuadrado de bondad de ajuste** de la capa especial contra distribución nacional acumulada.
- **Binomial exacto por candidato** con hipótesis nula de proporción nacional.
- **Ajuste Bonferroni** para múltiples comparaciones.
- **Intervalos de confianza 95%** por proporción especial.
- **Potencia estadística aproximada** para contraste de proporciones.
- **Tendencia temporal** de votos especiales por regresión lineal (pendiente, intercepto, `R²`).

### Justificación matemática y trazabilidad

El reporte forense (`generate_forensic_report`) emite Markdown con fragmentos LaTeX:

\[
z = \frac{\hat{p}_{special} - \hat{p}_{normal}}{\sqrt{\hat{p}(1-\hat{p})(\frac{1}{n_{special}}+\frac{1}{n_{normal}})}}
\]

\[
\chi^2 = \sum_i \frac{(O_i - E_i)^2}{E_i}, \quad E_i = n_{special}\,p_{national,i}
\]

Además, incluye hashes SHA-256 de cada snapshot JSON para reproducibilidad criptográfica e idempotencia de resultados.
