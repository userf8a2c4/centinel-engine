# Metodología técnica | Technical Methodology

## Español

### Propósito
Este documento describe la metodología técnica actual de C.E.N.T.I.N.E.L. y define espacios para pruebas estadísticas futuras. Complementa el [README](../README.md) y el flujo operativo en [OPERATIONAL-FLOW-AND-CADENCE.md](OPERATIONAL-FLOW-AND-CADENCE.md).

### Principios metodológicos
- **Reproducibilidad:** todo resultado se deriva de datos públicos verificables y snapshots con hashes encadenados.
- **Neutralidad técnica:** se reporta evidencia, no interpretaciones políticas.
- **Trazabilidad:** cada hallazgo conserva fuente, fecha, hash y reglas aplicadas.
- **No intrusión:** se respetan límites operativos y legales (ver [LEGAL-AND-OPERATIONAL-BOUNDARIES.md](LEGAL-AND-OPERATIONAL-BOUNDARIES.md)).

### Metodología actual (pipeline técnico)
1. **Captura de datos públicos**
   - Ingesta de fuentes oficiales publicadas.
   - Respeto a cadencias definidas por modo operativo.

2. **Hashing y encadenamiento criptográfico**
   - Hash por snapshot para integridad.
   - Encadenamiento para detectar alteraciones históricas.

3. **Normalización estructural**
   - Conversión a formatos consistentes para comparación.
   - Alineación de claves, orden y esquemas.

4. **Comparación y diferencias (diffs)**
   - Detección de cambios relevantes en el tiempo.
   - Registro de modificaciones para auditoría.

5. **Reglas de análisis**
   - Conjunto de reglas técnicas configurables para identificar eventos atípicos.
   - Resultados documentados con metadatos reproducibles.

6. **Registro histórico y reportes**
   - Reportes técnicos listos para revisión externa.
   - Preparación para expansión a reportes PDF y resúmenes ejecutivos.

### Estructura de evidencia (resumen)

| Elemento | Descripción | Propósito |
| --- | --- | --- |
| Snapshot | Copia puntual de datos públicos | Base verificable de auditoría |
| Hash | Huella criptográfica del snapshot | Integridad y no manipulación |
| Diff | Diferencias entre snapshots | Identificación de cambios |
| Regla | Lógica de detección | Señales técnicas sin juicio político |
| Metadatos | Fecha, fuente, versión | Reproducibilidad completa |

### Placeholders para pruebas estadísticas futuras
> Estos espacios están reservados para incorporar análisis estadísticos avanzados con rigor matemático. Se integrarán como módulos opcionales, manteniendo trazabilidad e integridad.

#### 1) Ley de Benford (primer dígito)
- **Objetivo:** evaluar distribución de primeros dígitos para identificar desviaciones significativas.
- **Fórmula base:**
  \[
  P(d) = \log_{10}(1 + \frac{1}{d}), \quad d \in {1,2,\dots,9}
  \]
- **Integración propuesta:** reporte de desviaciones por entidad y periodo.
- **Estado:** placeholder para futuras versiones.

#### 2) Prueba \(\chi^2\) (chi-cuadrado)
- **Objetivo:** comparar distribuciones observadas vs. esperadas.
- **Fórmula base:**
  \[
  \chi^2 = \sum_{i=1}^{k} \frac{(O_i - E_i)^2}{E_i}
  \]
- **Integración propuesta:** detección de anomalías en conteos agregados.
- **Estado:** placeholder para futuras versiones.

#### 3) Detección de anomalías multivariadas
- **Objetivo:** identificar patrones atípicos usando métricas estadísticas multivariadas.
- **Referencia matemática:** distancia de Mahalanobis
  \[
  D_M(x) = \sqrt{(x - \mu)^T \Sigma^{-1} (x - \mu)}
  \]
- **Integración propuesta:** alertas por desviaciones simultáneas de múltiples variables.
- **Estado:** placeholder para futuras versiones.

### Referencias y expansión
- La metodología se complementa con el marco legal en [LEGAL-AND-OPERATIONAL-BOUNDARIES.md](LEGAL-AND-OPERATIONAL-BOUNDARIES.md).
- La seguridad y gestión de secretos se detalla en [SECURITY-AND-SECRETS.md](SECURITY-AND-SECRETS.md).
- Se prevé expansión a reportes PDF y anexos técnicos con evidencia reproducible.

---

## English

### Purpose
This document describes the current technical methodology of C.E.N.T.I.N.E.L. and defines placeholders for future statistical tests. It complements the [README](../README.md) and the operating flow in [OPERATIONAL-FLOW-AND-CADENCE.md](OPERATIONAL-FLOW-AND-CADENCE.md).

### Methodological principles
- **Reproducibility:** every result derives from verifiable public data and snapshots with chained hashes.
- **Technical neutrality:** evidence is reported, not political interpretations.
- **Traceability:** each finding preserves source, timestamp, hash, and applied rules.
- **Non-intrusive operation:** legal and operational boundaries are respected (see [LEGAL-AND-OPERATIONAL-BOUNDARIES.md](LEGAL-AND-OPERATIONAL-BOUNDARIES.md)).

### Current methodology (technical pipeline)
1. **Capture public data**
   - Ingests official published sources.
   - Respects cadences defined by operating mode.

2. **Cryptographic hashing and chaining**
   - Hash per snapshot for integrity.
   - Chaining to detect historical alteration.

3. **Structural normalization**
   - Converts to consistent formats for comparison.
   - Aligns keys, order, and schemas.

4. **Comparison and diffs**
   - Detects relevant changes over time.
   - Logs modifications for auditability.

5. **Rule-based analysis**
   - Configurable technical rules to flag atypical events.
   - Results documented with reproducible metadata.

6. **Historical logging and reports**
   - Technical reports ready for external review.
   - Prepared for expansion to PDF reports and executive summaries.

### Evidence structure (summary)

| Element | Description | Purpose |
| --- | --- | --- |
| Snapshot | Point-in-time copy of public data | Verifiable audit base |
| Hash | Cryptographic fingerprint of snapshot | Integrity and non-tampering |
| Diff | Differences between snapshots | Change identification |
| Rule | Detection logic | Technical signals without political judgment |
| Metadata | Timestamp, source, version | Full reproducibility |

### Placeholders for future statistical tests
> These sections are reserved for advanced statistical analysis with mathematical rigor. They will be added as optional modules while preserving traceability and integrity.

#### 1) Benford's Law (first digit)
- **Goal:** evaluate first-digit distributions to identify significant deviations.
- **Base formula:**
  \[
  P(d) = \log_{10}(1 + \frac{1}{d}), \quad d \in {1,2,\dots,9}
  \]
- **Proposed integration:** deviation reports by entity and period.
- **Status:** placeholder for future releases.

#### 2) \(\chi^2\) test (chi-square)
- **Goal:** compare observed vs. expected distributions.
- **Base formula:**
  \[
  \chi^2 = \sum_{i=1}^{k} \frac{(O_i - E_i)^2}{E_i}
  \]
- **Proposed integration:** anomaly detection in aggregated counts.
- **Status:** placeholder for future releases.

#### 3) Multivariate anomaly detection
- **Goal:** identify atypical patterns using multivariate statistical metrics.
- **Mathematical reference:** Mahalanobis distance
  \[
  D_M(x) = \sqrt{(x - \mu)^T \Sigma^{-1} (x - \mu)}
  \]
- **Proposed integration:** alerts for simultaneous deviations across multiple variables.
- **Status:** placeholder for future releases.

### References and expansion
- The methodology is complemented by the legal framework in [LEGAL-AND-OPERATIONAL-BOUNDARIES.md](LEGAL-AND-OPERATIONAL-BOUNDARIES.md).
- Security and secrets management are detailed in [SECURITY-AND-SECRETS.md](SECURITY-AND-SECRETS.md).
- Planned expansion includes PDF reports and technical annexes with reproducible evidence.


### Revisión académica externa
- Las reglas matemáticas se encuentran en revisión técnica continua junto a especialistas de la **UPNFM**, con el objetivo de elevar precisión analítica, robustez estadística y trazabilidad metodológica sin comprometer neutralidad operativa.
