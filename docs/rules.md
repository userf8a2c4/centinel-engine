# Reglas Técnicas – Proyecto C.E.N.T.I.N.E.L.

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

### R-06 Variación Relativa Excesiva
Cambios porcentuales de votos mayores a un umbral configurado se registran.

### R-07 Saltos de Escrutinio
Saltos abruptos en el porcentaje escrutado se registran como eventos.

### R-08 Discrepancias Totales
Desajustes entre votos totales, blancos y nulos se registran.

### R-09 Actas Fuera de Rango
Actas procesadas por encima del total esperado se registran.

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

### R-06 Excess Relative Variation
Vote percentage changes above a configurable threshold are logged.

### R-07 Scrutiny Jumps
Abrupt jumps in scrutiny percentage are logged as events.

### R-08 Totals Discrepancies
Mismatches between total, blank, and null votes are logged.

### R-09 Actas Out of Range
Processed actas above the expected total are logged.
