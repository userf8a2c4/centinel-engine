# Statistical Detection Rules | Reglas de Detección Estadística

**Version:** 2.0 | **Date:** 2026-05-18 | **Status:** Active — 24 rules implemented

> All rules are configured via `command_center/rules.yaml`. Thresholds can be adjusted without redeployment.
> Todas las reglas se configuran en `command_center/rules.yaml`. Los umbrales se ajustan sin redeployment.

---

## Rule Index | Índice de Reglas

| # | Rule / Regla | `config_key` | Severity | FP Rate |
|---|---|---|---|---|
| D-01 | Benford First Digit | `benford_first_digit` | CRITICAL | 0.00% |
| D-02 | Benford by Candidate | `benford_law` | Medium | 0.00% |
| D-03 | Last Digit Uniformity | `last_digit_uniformity` | CRITICAL | 0.00% |
| D-04 | Participation Anomaly (Z-score) | `participation_anomaly` | High | 0.00%* |
| D-05 | Participation Anomaly Advanced | `participation_anomaly_advanced` | CRITICAL | 0.00% |
| D-06 | Turnout Impossible | `turnout_impossible` | CRITICAL | 0.00% |
| D-07 | Arithmetic Consistency | `table_consistency` | CRITICAL | 0.00% |
| D-08 | Null & Blank Votes Excess | `null_blank_votes` | CRITICAL | 0.00% |
| D-09 | Mesa Impossibility | `mesa_impossibility` | CRITICAL | 0.00% |
| D-10 | Large Numbers Convergence | `large_numbers_convergence` | Medium | 0.00% |
| D-11 | Geographic Dispersion | `geographic_dispersion` | CRITICAL | 0.00% |
| D-12 | Granular Anomaly | `granular_anomaly` | CRITICAL | 0.00%* |
| D-13 | Irreversibility | `irreversibility` | High | 0.00% |
| D-14 | Runs Test | `runs_test` | CRITICAL | 0.00% |
| D-15 | Participation-Vote Correlation | `participation_vote_correlation` | CRITICAL | 0.00% |
| D-16 | Basic Diff (record mutation) | `basic_diff` | High | — |
| D-17 | Snapshot Jump | `snapshot_jump` | CRITICAL | — |
| D-18 | Mesas Diff (missing/duplicate) | `mesas_diff` | CRITICAL | — |
| D-19 | Inconsistency Rate | `inconsistency_rate` | CRITICAL | — |
| D-20 | Mesa Reconciliation | `mesa_reconciliation` | CRITICAL | — |
| D-21 | Late Mesa Appearance | `late_mesa` | WARNING | — |
| D-22 | Processing Speed | `processing_speed` | High | — |
| D-23 | Trend Shift | `trend_shift` | High | — |
| D-24 | ML Outliers (Isolation Forest) | `ml_outliers` | Medium | — |

*FP rate applies to single-department synthetic data. In production with 18 departments: <3%. See [`FALSE_POSITIVE_ANALYSIS.md`](FALSE_POSITIVE_ANALYSIS.md).

---

## Severity Levels | Niveles de Severidad

| Level | Meaning | Action |
|-------|---------|--------|
| `CRITICAL` | Statistically impossible in a clean election | Immediate review + independent confirmation |
| `High` | Strong anomaly signal, low FP rate | Investigate before communicating |
| `Medium` | Moderate signal, may need context | Cross-check with other rules |
| `WARNING` | Edge case, informational | Log only |

---

## Rule Descriptions | Descripción de Reglas

### D-01 Benford First Digit — `benford_first_digit` — CRITICAL
**ES:** La distribución del primer dígito de votos por candidato debe seguir la Ley de Benford (log₁₀(1+1/d)). Se usa MAD (Mean Absolute Deviation) y chi-cuadrado como criterios combinados.  
**EN:** The first-digit distribution of candidate votes must follow Benford's Law. Uses combined MAD + chi-square — both must exceed threshold to fire.

```yaml
benford_first_digit:
  enabled: true
  min_samples: 10
  mad_threshold: 0.015
  chi_square_p_threshold: 0.05
```

---

### D-02 Benford by Candidate — `benford_law` — Medium
**ES:** Variante de Benford aplicada por candidato individualmente. Más sensible a fraude focalizado en un partido.  
**EN:** Benford variant applied per candidate. More sensitive to fraud targeting a single party.

---

### D-03 Last Digit Uniformity — `last_digit_uniformity` — CRITICAL
**ES:** Los últimos dígitos de los conteos deben seguir distribución uniforme (0-9). Patrones como exceso de ceros o cincos indican redondeo artificial.  
**EN:** Last digits of vote counts must be uniformly distributed. Excess zeros or fives indicate artificial rounding.

---

### D-04 Participation Anomaly — `participation_anomaly` — High
**ES:** Z-score de participación comparado entre departamentos. Requiere mínimo 3 departamentos con datos para tener baseline estadístico.  
**EN:** Z-score of participation rate compared across departments. Requires ≥3 departments for a valid statistical baseline.

---

### D-05 Participation Anomaly Advanced — `participation_anomaly_advanced` — CRITICAL
**ES:** Versión avanzada que incorpora evolución temporal y comparación histórica. Umbral más estricto.  
**EN:** Advanced version incorporating temporal evolution and historical comparison. Stricter threshold.

---

### D-06 Turnout Impossible — `turnout_impossible` — CRITICAL
**ES:** Detecta participación > 100% del padrón electoral registrado — aritméticamente imposible.  
**EN:** Flags participation > 100% of registered voter rolls — arithmetically impossible.

---

### D-07 Arithmetic Consistency — `table_consistency` — CRITICAL
**ES:** La suma de votos por candidato más nulos más blancos debe igualar el total de votos válidos. Tolerancia configurable.  
**EN:** Sum of candidate votes + null + blank must equal total valid votes. Configurable tolerance.

---

### D-08 Null & Blank Votes — `null_blank_votes` — CRITICAL
**ES:** Detecta ratios inusualmente altos de votos nulos o blancos respecto al total.  
**EN:** Flags unusually high ratios of null or blank votes relative to total cast.

---

### D-09 Mesa Impossibility — `mesa_impossibility` — CRITICAL
**ES:** Detecta actas individuales con participación > 100% de electores registrados en esa mesa.  
**EN:** Flags individual polling stations (mesas) with turnout > 100% of registered voters.

---

### D-10 Large Numbers Convergence — `large_numbers_convergence` — Medium
**ES:** A medida que aumentan las actas procesadas, los porcentajes deben estabilizarse (Ley de Grandes Números). Fluctuaciones tardías son anómalas.  
**EN:** As processed actas increase, percentages must stabilize (Law of Large Numbers). Late fluctuations are anomalous.

---

### D-11 Geographic Dispersion — `geographic_dispersion` — CRITICAL
**ES:** Detecta departamentos con distribución de votos estadísticamente inconsistente con el patrón nacional.  
**EN:** Flags departments with vote distributions statistically inconsistent with the national pattern.

---

### D-12 Granular Anomaly — `granular_anomaly` — CRITICAL
**ES:** Analiza consistencia intra-acta (a nivel de mesa individual). Requiere continuidad temporal entre snapshots de la misma elección.  
**EN:** Analyzes intra-acta consistency at individual mesa level. Requires temporal continuity across snapshots.

---

### D-13 Irreversibility — `irreversibility` — High
**ES:** Los conteos acumulados nunca pueden disminuir entre snapshots. Cualquier decrecimiento es una anomalía criptográfica.  
**EN:** Accumulated counts must never decrease between snapshots. Any decrease is a cryptographic anomaly.

---

### D-14 Runs Test — `runs_test` — CRITICAL
**ES:** Test no-paramétrico de aleatoriedad. La secuencia de incrementos de votos debe pasar el test de rachas (Wald-Wolfowitz).  
**EN:** Non-parametric randomness test. The sequence of vote increments must pass the Wald-Wolfowitz runs test.

---

### D-15 Participation-Vote Correlation — `participation_vote_correlation` — CRITICAL
**ES:** En elecciones limpias, la participación y los votos válidos deben estar altamente correlacionados entre departamentos (r > 0.85). Desviaciones indican manipulación selectiva.  
**EN:** In clean elections, participation and valid votes must be highly correlated across departments (r > 0.85). Deviations indicate selective manipulation.

---

### D-16 Basic Diff — `basic_diff` — High
**ES:** Detecta mutaciones de registros entre publicaciones: valores que cambian sin aumento de actas procesadas.  
**EN:** Detects record mutations between publications: values changing without increase in processed actas.

---

### D-17 Snapshot Jump — `snapshot_jump` — CRITICAL
**ES:** Detecta saltos abruptos entre snapshots consecutivos que excedan el umbral de variación esperado.  
**EN:** Flags abrupt jumps between consecutive snapshots exceeding the expected variation threshold.

---

### D-18 Mesas Diff — `mesas_diff` — CRITICAL
**ES:** Detecta mesas que desaparecen o duplican entre snapshots — imposible en un proceso normal.  
**EN:** Flags polling stations that disappear or duplicate between snapshots — impossible in a normal process.

---

### D-19 Inconsistency Rate — `inconsistency_rate` — CRITICAL
**ES:** Mide la tasa de actas con inconsistencias aritméticas respecto al total procesado. Umbral configurable.  
**EN:** Measures rate of arithmetically inconsistent actas relative to total processed.

---

### D-20 Mesa Reconciliation — `mesa_reconciliation` — CRITICAL
**ES:** Verifica que el número de actas procesadas en snapshots consecutivos sea monotónico y reconciliable.  
**EN:** Verifies that processed actas count is monotonic and reconcilable across consecutive snapshots.

---

### D-21 Late Mesa Appearance — `late_mesa` — WARNING
**ES:** Detecta mesas que aparecen tardíamente en el conteo (>90% de escrutinio) con valores que afectan el resultado.  
**EN:** Flags polling stations appearing late in the count (>90% scrutiny) with result-affecting values.

---

### D-22 Processing Speed — `processing_speed` — High
**ES:** Velocidad de procesamiento de actas por hora. Aceleraciones extremas al final del conteo pueden ser anómalas.  
**EN:** Actas processing speed per hour. Extreme acceleration at count close can be anomalous.

---

### D-23 Trend Shift — `trend_shift` — High
**ES:** Detecta cambios de tendencia estadísticamente significativos en la proporción de votos por candidato.  
**EN:** Detects statistically significant trend shifts in the vote proportion per candidate.

---

### D-24 ML Outliers — `ml_outliers` — Medium
**ES:** Isolation Forest entrenado en el histórico de snapshots. Detecta snapshots estadísticamente anómalos sin reglas explícitas.  
**EN:** Isolation Forest trained on snapshot history. Detects statistically anomalous snapshots without explicit rules.

---

## Operational Principles | Principios Operativos

1. **Flag for review, not for accusation** — no single alert constitutes fraud evidence
2. **Combinatorial signal** — CRITICAL alerts from 3+ independent rules on the same snapshot = significant forensic signal
3. **Calibrated thresholds** — all thresholds in `rules.yaml` are configurable without code changes
4. **Auditable** — every alert includes: rule name, severity, observed value, threshold, snapshot hash

---

*See also: [METHODOLOGY.md](METHODOLOGY.md) | [FALSE_POSITIVE_ANALYSIS.md](FALSE_POSITIVE_ANALYSIS.md) | [ANOMALY-DETECTION.md](ANOMALY-DETECTION.md)*
