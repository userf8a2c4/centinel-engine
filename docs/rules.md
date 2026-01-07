# Reglas Técnicas – Sentinel

## [ES] Español

### R-01 Integridad de Conteo Acumulado
Los votos acumulados nunca pueden disminuir entre snapshots consecutivos.

### R-02 Monotonicidad Temporal
Los timestamps deben avanzar o mantenerse, nunca retroceder.

### R-03 Consistencia Aritmética
La suma de votos por candidato debe coincidir con el total válido.

### R-04 Variación Atípica
Incrementos abruptos fuera de desviación histórica se registran como eventos.

### R-05 Reescritura Implícita
Cambio de valores sin aumento de actas se registra.

---

## [EN] English

### R-01 Accumulated Counting Integrity
Accumulated votes must never decrease between consecutive snapshots.

### R-02 Temporal Monotonicity
Timestamps must move forward or remain stable.

### R-03 Arithmetic Consistency
Sum of candidate votes must match valid votes.

### R-04 Atypical Variation
Abrupt increases outside historical deviation are logged as events.

### R-05 Implicit Rewrite
Value changes without act increase are logged.
