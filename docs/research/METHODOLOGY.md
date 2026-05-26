# Metodología Técnica | Technical Methodology

**Version:** 1.1 | **Date:** 2026-05-18 | **Status:** Active

> **Estado de implementación:** Este documento refleja el sistema **tal como está
> implementado y corriendo en producción**, no un plan futuro. Cada regla descrita
> existe en `src/centinel/core/rules/` o `src/auditor/inconsistent_acts.py` y se
> ejecuta en cada ciclo del pipeline. Última sincronización código↔doc: ver `git log`.

---

## ESPAÑOL

### 1. Propósito

Este documento describe la metodología técnica de C.E.N.T.I.N.E.L.: cómo captura
datos electorales públicos, cómo garantiza su integridad criptográficamente y qué
detectores estadísticos aplica para identificar anomalías. Está dirigido a evaluadores
técnicos, observadores electorales (OEA, Carter Center, UE), revisores académicos y
auditores ciudadanos independientes.

### 2. Principios metodológicos

- **Agnóstico al candidato:** el sistema monitorea la *integridad del dato*, no el
  resultado político. Ningún detector favorece a ningún candidato o partido.
- **Reproducibilidad:** todo resultado se deriva de datos públicos verificables con
  hashes encadenados. Un tercero puede reproducir cualquier hallazgo desde cero.
- **Trazabilidad:** cada hallazgo conserva fuente, timestamp, hash y reglas aplicadas.
- **No intrusión:** solo fuentes públicas, sin interferencia, sin datos personales
  (ver `LEGAL-AND-OPERATIONAL-BOUNDARIES.md`).
- **El hueco es la alerta:** toda ventana sin captura se marca sospechosa por defecto.

### 3. Pipeline técnico

1. **Captura** — Ingesta de endpoints oficiales del CNE a cadencia configurable
   (2–5 min), con rate-limiting ético y rotación de proxy/user-agent.
2. **Hashing y encadenamiento** — SHA-256 por snapshot, encadenado al anterior.
   Merkle root computado sobre el conjunto. Alteración histórica propaga mismatch.
3. **Normalización** — Conversión a esquema consistente; parseo de enteros con
   comas (`"1,027,090"` → `1027090`); alineación de claves.
4. **Diffs** — Comparación entre snapshots consecutivos; registro de mutaciones.
5. **Reglas** — 23 reglas estadísticas + 7 detectores forenses (sección 4).
6. **Anclaje externo** — Merkle root anclado a Bitcoin vía OpenTimestamps.
7. **Publicación** — Bloque forense + cobertura a Supabase; panel público.

### 4. Catálogo de detectores implementados

**Total: 23 reglas con decorador `@rule` + 7 detectores forenses = 30 análisis.**
Registro en `src/centinel/core/rules/registry.py`.

#### 4.1 Reglas estadísticas core (23)

| # | Regla | `config_key` | Técnica | Umbral por defecto | Severidad |
|---|---|---|---|---|---|
| 1 | Consistencia Aritmética Básica | `basic_diff` | Igualdad aritmética + cambio relativo | cambio voto >15% | HIGH/MEDIUM |
| 2 | Ley de Benford (Primer Dígito) | `benford_first_digit` | MAD + χ² sobre `P(d)=log₁₀(1+1/d)` | MAD>0.015, p<0.01 | CRITICAL |
| 3 | Ley de Benford (alternativa) | `benford_law` | χ² + desviación % máxima | desv>15%, p<0.05 | MEDIUM |
| 4 | Correlación Participación-Voto | `participation_vote_correlation` | Pearson r(turnout, share líder) | r>0.85, n≥30 | CRITICAL |
| 5 | Dispersión Geográfica | `geographic_dispersion` | Coef. variación entre deptos | CV>0.45, ≥5 deptos | CRITICAL |
| 6 | Anomalías Granulares | `granular_anomaly` | Deltas neg. + Z-score + Benford/depto + reversión | z>3.0, Δ>3%/30min | CRITICAL/HIGH |
| 7 | Irreversibilidad Estadística | `irreversibility` | Brecha vs votos faltantes (SQLite estado) | participación hist. 0.60 | MEDIUM/HIGH |
| 8 | Convergencia Ley Grandes Números | `large_numbers_convergence` | Z-score media muestral vs global | z>3.0, n≥30 | MEDIUM |
| 9 | Uniformidad Último Dígito | `last_digit_uniformity` | χ² uniformidad dígitos 0–9 | p<0.001, n≥20 | CRITICAL |
| 10 | Aparición Tardía de Registros | `late_mesa` | Heurística índice mesas | >90% escrutado, lote≥50 | WARNING/CRITICAL |
| 11 | Imposibilidad Aritmética/Registro | `mesa_impossibility` | Validación aritmética por mesa | emitidos>inscritos, etc. | CRITICAL |
| 12 | Mutación de Registros | `mesa_reconciliation` | Fingerprint SHA-256 por mesa | cambio post-publicación | CRITICAL |
| 13 | Mesas Duplicadas/Desaparecidas | `mesas_diff` | Set difference códigos mesa | aparición/desaparición | CRITICAL |
| 14 | Outliers ML (Isolation Forest) | `ml_outliers` | Isolation Forest sobre Δ% (SQLite hist.) | contamination 0.1 | MEDIUM |
| 15 | Nulos y Blancos Elevados | `null_blank_votes` | Ratio (nulos+blancos)/total | >12% crit, >8% warn | CRITICAL/WARNING |
| 16 | Participación Anómala | `participation_anomaly_advanced` | Rango + Z-score hist./depto | 40–90%, z>3σ | CRITICAL/WARNING |
| 17 | Anomalía de Participación | `participation_anomaly` | Actas vs total + salto escrutinio | salto ≥5% | HIGH/MEDIUM |
| 18 | Velocidad de Procesamiento | `processing_speed` | Actas/min normalizado 15min | >500 actas/15min | HIGH |
| 19 | Runs Test | `runs_test` | Wald-Wolfowitz sobre mesas ordenadas | p<0.01, n≥30 | CRITICAL |
| 20 | Saltos entre Snapshots | `snapshot_jump` | Δ% votos en ventana corta | >5% en ≤10min | CRITICAL |
| 21 | Consistencia por Mesa | `table_consistency` | Aritmética por mesa (tol. ±1) | suma≠total | CRITICAL |
| 22 | Desviación de Tendencia | `trend_shift` | Δ% nuevo vs histórico acumulado | dif>10% | HIGH |
| 23 | Turnout Imposible | `turnout_impossible` | turnout = votos/padrón | <0% o >100% | CRITICAL |

#### 4.2 Detectores forenses de actas inconsistentes (7)

Implementados en `src/auditor/inconsistent_acts.py`, clase `InconsistentActsTracker`:

| Detector | Técnica | Umbral por defecto |
|---|---|---|
| `detect_progressive_injection` | Z-score acumulativo + runs test + autocorrelación lag-1 | ≥5 ciclos, p<0.05, ACF>0.5 |
| `detect_resolution_velocity_anomalies` | Tasa actas/min | >10 actas/min |
| `detect_asymmetric_benefit` | Test z de diferencia de proporciones (especial vs normal) | p<0.01 |
| `detect_hold_and_release` | Estancamiento seguido de liberación masiva | ≥6 ciclos, ≥300 actas |
| `detect_benford_special_scrutiny` | χ² Benford sobre deltas escrutinio especial | p<0.05, ≥10 deltas |
| `detect_blackout_windows` | Gap comunicacional + cambio de tendencia post-gap | gap>30min, shift>0.5% |
| `detect_anomalies` | Orquestador: agrega todos los anteriores + vote_outlier 3σ | z>3.0 |

#### 4.3 Técnicas estadísticas empleadas (resumen)

- **Test χ² (chi-cuadrado):** reglas 2, 3, 6, 19 + Benford forense — 5 análisis
- **Correlación de Pearson:** regla 4
- **Z-score / desviación estándar:** reglas 6, 8, 16 + inyección progresiva — 4 análisis
- **Runs test (Wald-Wolfowitz):** regla 19 + inyección progresiva — 2 análisis
- **Coeficiente de variación:** regla 5
- **Isolation Forest (ML no supervisado):** regla 14
- **Test z de proporciones:** beneficio asimétrico forense
- **Validación aritmética determinista:** reglas 1, 11, 21, 23

### 5. Calibración de parámetros

Todos los umbrales son configurables vía `config/{env}/rules.yaml`. Los valores por
defecto documentados arriba se derivan de:

- **Umbrales estadísticos clásicos:** p<0.05 (significancia estándar), p<0.01 y
  p<0.001 (alta confianza) para reducir falsos positivos en reglas CRITICAL.
- **Umbrales de dominio electoral:** turnout 0–100% (imposibilidad física),
  velocidad de procesamiento (capacidad humana documentada de escrutinio).
- **Z-score ≥3σ:** convención de 3 sigmas (99.7% de la distribución normal).
- **Benford MAD 0.015:** umbral de Nigrini para "marginalmente aceptable".

> **Recalibración para otro país:** ver `REPLICATION_GUIDE.md`. Los umbrales de
> dominio (turnout, velocidad) deben ajustarse al sistema electoral objetivo.

### 6. Limitaciones conocidas (honestidad metodológica)

- **No prueba fraude en el acta física:** el sistema audita el JSON oficial, no la
  papeleta. Detecta manipulación *del dato publicado*, no del voto en la urna.
- **No prueba la corrección del dato original:** si el CNE publica un dato falso
  desde el primer snapshot, el hash chain lo preserva pero no lo invalida. La
  defensa contra esto es el consenso multi-testigo (T2/T4) y los detectores
  estadísticos, no la criptografía sola.
- **Reglas con estado (SQLite):** Irreversibilidad y ML Outliers dependen de
  historial persistido; un despliegue nuevo necesita ciclos de calentamiento.
- **Falsos positivos conocidos:** ver `FALSE_POSITIVE_ANALYSIS.md`. Las reglas
  basadas en ventanas (snapshot_jump, trend_shift) pueden disparar al inicio del
  conteo con baja cobertura; se mitiga con `min_samples` y cobertura mínima.
- **Benford no aplica universalmente:** distribuciones acotadas (ej. mesas con
  rango de votos estrecho) pueden desviarse de Benford sin fraude. Por eso Benford
  es MEDIUM/CRITICAL según el detector y nunca actúa solo.

### 7. Estado de validación

| Componente | Estado |
|---|---|
| Núcleo criptográfico (hash chain, Merkle, OTS) | Implementado, cubierto por tests deterministas |
| 23 reglas estadísticas | Implementadas, cubiertas por tests unitarios |
| 7 detectores forenses | Implementados, cubiertos por `tests/test_inconsistent_acts.py` |
| Tasa de falsos positivos | Medida sobre datos sintéticos — ver `FALSE_POSITIVE_ANALYSIS.md` |
| Revisión académica externa | En curso con UPNFM (Depto. Matemáticas) — pendiente informe firmado |
| Validación contra elección real | Pendiente piloto — ver `PILOT_PLAN.md` |

---

## ENGLISH

### 1. Purpose

This document describes C.E.N.T.I.N.E.L.'s technical methodology: how it captures
public electoral data, how it cryptographically guarantees integrity, and which
statistical detectors it applies. It targets technical evaluators, election
observers (OAS, Carter Center, EU), academic reviewers, and independent citizen
auditors.

### 2. Methodological principles

- **Candidate-agnostic:** the system monitors *data integrity*, not political
  outcomes. No detector favors any candidate or party.
- **Reproducibility:** every result derives from verifiable public data with chained
  hashes. A third party can reproduce any finding from scratch.
- **Traceability:** every finding preserves source, timestamp, hash, applied rules.
- **Non-intrusive:** public sources only, no interference, no personal data.
- **The gap is the alert:** any capture window without data is suspicious by default.

### 3. Technical pipeline

Capture → SHA-256 hashing & chaining → normalization → diffs → 23 rules + 7 forensic
detectors → Bitcoin anchoring (OpenTimestamps) → publication (Supabase + public panel).

### 4. Implemented detector catalog

**Total: 23 `@rule`-decorated rules + 7 forensic detectors = 30 analyses.** See the
Spanish section §4.1–4.3 for the full table (rule, config key, technique, default
threshold, severity). The tables are language-neutral (formulas and parameters).

### 5. Parameter calibration

All thresholds are configurable via `config/{env}/rules.yaml`. Defaults derive from
classical statistical thresholds (p<0.05/0.01/0.001), electoral-domain physical
limits (turnout 0–100%, human scrutiny speed), the 3-sigma convention, and Nigrini's
Benford MAD bounds. Recalibration for another country: see `REPLICATION_GUIDE.md`.

### 6. Known limitations

- Does not prove fraud in the physical tally sheet — it audits the official JSON.
- Does not prove correctness of the original datum — defense is multi-witness
  consensus (T2/T4) plus statistical detectors, not cryptography alone.
- Stateful rules (SQLite) need warm-up cycles on fresh deployment.
- Known false positives documented in `FALSE_POSITIVE_ANALYSIS.md`.
- Benford does not apply universally; bounded distributions may deviate without fraud.

### 7. Validation status

Cryptographic core, 23 rules and 7 detectors are implemented and unit-tested.
False-positive rate measured on synthetic data (`FALSE_POSITIVE_ANALYSIS.md`).
External academic review with UPNFM in progress. Real-election validation pending
pilot (`PILOT_PLAN.md`).

---

### Referencias

- Nigrini, M. (2012). *Benford's Law: Applications for Forensic Accounting, Auditing,
  and Fraud Detection*. Wiley.
- Wald, A. & Wolfowitz, J. (1940). *On a test whether two samples are from the same
  population*. Annals of Mathematical Statistics.
- Marco legal y operativo: `LEGAL-AND-OPERATIONAL-BOUNDARIES.md`
- Arquitectura criptográfica (T1–T4): `ARCHITECTURE.md`
- Análisis de falsos positivos: `FALSE_POSITIVE_ANALYSIS.md`
- Teoría de cambio: `THEORY_OF_CHANGE.md`
