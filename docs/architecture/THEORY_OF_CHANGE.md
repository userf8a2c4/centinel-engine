# Theory of Change — Centinel Engine
## Teoría del Cambio / Theory of Change

**Version:** 1.1 | **Date:** 2026-05-18 | **Status:** Active

---

## Español

### El Problema

Los sistemas de resultados electorales son vulnerables a manipulación **después de que los datos
se capturan en las mesas** y antes de que el público los consulte. Esta manipulación puede
incluir:

- Alteración de totales en tránsito entre mesa y servidor central
- Modificación de registros en base de datos sin dejar rastro
- Sustitución de endpoints de consulta para mostrar resultados distintos a observadores
- Bloqueos estratégicos de información durante ventanas críticas del conteo

El problema no es nuevo: ocurrió en Venezuela 2004, México 2006, Kenya 2007, Honduras 2017
y decenas de otros contextos. La característica común es que **nadie tenía una cadena de
custodia criptográfica de los datos digitales** al momento de la alteración.

### La Intervención

Centinel Engine resuelve esto con tres mecanismos complementarios:

1. **Captura continua**: el sistema descarga los datos oficiales del CNE cada N minutos durante
   todo el período de cómputo.

2. **Encadenamiento criptográfico**: cada snapshot se encadena con SHA-256 al anterior, creando
   una cadena inmutable. El hash de cada bloque se ancla en el blockchain de Bitcoin vía
   OpenTimestamps — una fuente de tiempo externa, descentralizada e imposible de falsificar.

3. **Análisis estadístico automático**: 23 reglas estadísticas (Ley de Benford, Z-scores
   temporales, detección de ventanas negras, análisis de beneficio asimétrico, entre otras)
   evalúan los datos en tiempo real. Cualquier anomalía queda registrada en el log forense.

### Outputs (Lo que produce el sistema)

| Output | Descripción |
|--------|-------------|
| Cadena de hashes SHA-256 | Evidencia criptográfica de cada momento del conteo |
| Ancla Bitcoin (OpenTimestamps) | Timestamp externo verificable por cualquier ciudadano |
| Log forense (`attack_log.jsonl`) | Registro inmutable de anomalías detectadas |
| Reporte PDF auditado | Informe con Benford, heatmaps, KPIs, cadena de hashes |
| Verificador offline | HTML autocontenido que funciona sin internet |
| Panel público en tiempo real | Transparencia continua durante el conteo |

### Outcomes (Lo que cambia)

| Outcome | Mecanismo causal |
|---------|-----------------|
| Los actores maliciosos **saben que cualquier manipulación queda registrada** | La cadena Bitcoin es pública e irrefutable |
| Los observadores tienen evidencia técnica presentable ante tribunales | PDF con hash chain + ancla Bitcoin = evidencia legalmente usable |
| Los ciudadanos pueden verificar sin depender del CNE ni del gobierno | Verificador offline descargable antes de la elección |
| Las irregularidades detectadas en tiempo real permiten intervención oportuna | Log forense + alertas durante el conteo, no después |

### Impacto (Lo que cambia en el largo plazo)

> **La existencia de un sistema de vigilancia criptográfica disuade la manipulación antes
> de que ocurra, y documenta la evidencia cuando ocurre.**

- Reducción del incentivo para manipular datos electorales digitales en contextos donde
  Centinel Engine esté desplegado
- Aumento de la confianza ciudadana en resultados electorales verificables
- Estándar replicable para otros países de la región (Honduras → Guatemala → El Salvador →
  República Dominicana)
- Insumo para litigación postelectoral cuando sea necesario

### Hipótesis del Cambio

**H1 — Hipótesis de disuasión:** Los actores con capacidad de manipular datos no lo harán
si saben que existe una cadena de custodia criptográfica verificable externamente.

**H2 — Hipótesis de evidencia:** Si la manipulación ocurre a pesar de la vigilancia,
Centinel Engine generará evidencia técnica suficientemente sólida para su uso en
procesos judiciales o de revisión electoral.

**H3 — Hipótesis de legitimidad:** La existencia de un sistema de monitoreo independiente
y verificable aumenta la legitimidad percibida del proceso, independientemente del resultado.

### Métricas de Impacto (Cuantificadas)

| Métrica | Valor | Fuente |
|---------|-------|--------|
| Tiempo de detección de anomalía | < 5 minutos | Arquitectura de pipeline horario con dispatch de emergencia en ~60s |
| Coste por elección monitorizada | $0 en licencias | AGPL-3.0, sin dependencias propietarias |
| Coste de despliegue (hardware) | Laptop estándar | No requiere servidor dedicado ni nube |
| Detectores estadísticos activos | 24 | Registrados en `src/centinel/core/rules/` |
| Datos HN-2025 procesados | 96 archivos JSON, 18 departamentos, ~2.5M votos | Dataset `hnd-electoral-audit-2025` |
| Tasa de falsos positivos (13/24 reglas) | 0.0% en datos sintéticos | `docs/FALSE_POSITIVE_ANALYSIS.md` |
| Tests automatizados | ~95 archivos, 403 passing (entorno mínimo) | CI GitHub Actions |
| Cobertura de seguridad | 15/15 issues de red-team cerrados (9.9/10) | `SECURITY_AUDIT.md` RT-01..RT-15 |
| Países de Centroamérica con contexto similar | 5 (Guatemala, El Salvador, Nicaragua, Costa Rica, Panamá) | Replicabilidad regional |
| Tiempo de onboarding operador nuevo | ~15-20 minutos | `make wizard` + `make start` |

### Lo que Centinel Engine NO hace

- No cambia los resultados electorales
- No detecta fraude en el conteo físico de papeletas
- No garantiza que las actas físicas sean correctas
- No es un sistema de observación presencial
- **No tiene opinión sobre candidatos o partidos** — es 100% agnóstico a los resultados

---

## English

### The Problem

Electoral results systems are vulnerable to manipulation **after data is captured at polling
stations** and before the public can access it. This manipulation may include:

- Alteration of vote totals in transit between polling stations and the central server
- Database record modification without leaving an audit trail
- Substitution of query endpoints to show different results to observers
- Strategic information blackouts during critical windows of the count

This is not a new problem: it occurred in Venezuela 2004, Mexico 2006, Kenya 2007, Honduras
2017, and dozens of other contexts. The common thread is that **nobody had a cryptographic
chain of custody of the digital data** at the time of the alteration.

### The Intervention

Centinel Engine addresses this with three complementary mechanisms:

1. **Continuous capture**: the system downloads official CNE data every N minutes throughout
   the entire vote-counting period.

2. **Cryptographic chaining**: each snapshot is chained with SHA-256 to the previous one,
   creating an immutable chain. The hash of each block is anchored in the Bitcoin blockchain
   via OpenTimestamps — an external, decentralized, unfalsifiable time source.

3. **Automated statistical analysis**: 23 statistical rules (Benford's Law, temporal Z-scores,
   blackout window detection, asymmetric benefit analysis, and others) evaluate the data in
   real time. Any anomaly is recorded in the forensic log.

### Outputs (What the system produces)

| Output | Description |
|--------|-------------|
| SHA-256 hash chain | Cryptographic evidence for each moment of the count |
| Bitcoin anchor (OpenTimestamps) | External timestamp verifiable by any citizen |
| Forensic log (`attack_log.jsonl`) | Immutable record of detected anomalies |
| Audited PDF report | Report with Benford, heatmaps, KPIs, hash chain |
| Offline verifier | Self-contained HTML that works without internet |
| Real-time public dashboard | Continuous transparency during the count |

### Outcomes (What changes)

| Outcome | Causal mechanism |
|---------|-----------------|
| Bad actors **know any manipulation is recorded** | The Bitcoin chain is public and irrefutable |
| Observers have technical evidence presentable in court | PDF with hash chain + Bitcoin anchor = legally usable evidence |
| Citizens can verify without depending on CNE or government | Downloadable offline verifier before election day |
| Real-time detected irregularities allow timely intervention | Forensic log + alerts during the count, not after |

### Impact (What changes in the long term)

> **The existence of a cryptographic surveillance system deters manipulation before it
> occurs, and documents the evidence when it does.**

- Reduced incentive to manipulate digital electoral data in contexts where
  Centinel Engine is deployed
- Increased citizen trust in verifiable electoral results
- Replicable standard for other countries in the region (Honduras → Guatemala → El Salvador
  → Dominican Republic)
- Input for post-election litigation when necessary

### Change Hypotheses

**H1 — Deterrence hypothesis:** Actors with the capability to manipulate data will refrain
from doing so if they know an externally verifiable cryptographic chain of custody exists.

**H2 — Evidence hypothesis:** If manipulation occurs despite surveillance, Centinel Engine
will generate technical evidence solid enough for use in judicial or electoral review processes.

**H3 — Legitimacy hypothesis:** The existence of an independent, verifiable monitoring system
increases the perceived legitimacy of the process, regardless of the outcome.

### Impact Metrics (Quantified)

| Metric | Value | Source |
|--------|-------|--------|
| Anomaly detection latency | < 5 minutes | Hourly pipeline + emergency dispatch (~60s) |
| Cost per monitored election | $0 in licenses | AGPL-3.0, no proprietary dependencies |
| Deployment cost (hardware) | Standard laptop | No dedicated server or cloud required |
| Active statistical detectors | 24 | Registered in `src/centinel/core/rules/` |
| HN-2025 data processed | 96 JSON files, 18 departments, ~2.5M votes | Dataset `hnd-electoral-audit-2025` |
| False positive rate (13/24 rules) | 0.0% on synthetic data | `docs/FALSE_POSITIVE_ANALYSIS.md` |
| Automated tests | ~95 files, 403 passing (minimal env) | CI GitHub Actions |
| Security coverage | 15/15 red-team issues closed (9.9/10) | `SECURITY_AUDIT.md` RT-01..RT-15 |
| Central American countries with similar context | 5 (Guatemala, El Salvador, Nicaragua, Costa Rica, Panama) | Regional replicability |
| New operator onboarding time | ~15-20 minutes | `make wizard` + `make start` |

### What Centinel Engine does NOT do

- Does not change electoral results
- Does not detect fraud in the physical ballot count
- Does not guarantee that physical tally sheets are correct
- Is not a physical observation system
- **Has no opinion on candidates or parties** — it is 100% candidate-agnostic

---

## Problem → Intervention → Outputs → Outcomes → Impact

```
PROBLEMA                         INTERVENCIÓN                    OUTPUTS
─────────────────────────────    ──────────────────────────────  ──────────────────────────────
Datos electorales digitales  →   Captura continua cada N min  → Hash chain SHA-256
modificables sin rastro          + Encadenamiento SHA-256        + Ancla Bitcoin
                                 + Análisis estadístico 23       + Log forense
                                   reglas en tiempo real         + Reporte PDF
                                                                 + Verificador offline

OUTCOMES                         IMPACTO
──────────────────────────────   ──────────────────────────────
Actores maliciosos saben que  →  Reducción de incentivos para
cualquier cambio queda           manipulación digital electoral
registrado e irrefutado
                                 Aumento de confianza ciudadana
Observadores tienen evidencia    en resultados verificables
técnica para litigación
                                 Estándar replicable para otros
Ciudadanos verifican sin         países de la región
depender del gobierno
```

---

*Documento bilingüe ES/EN — Última revisión: 2025-05-17*
*Para la metodología técnica detallada ver: [METHODOLOGY.md](METHODOLOGY.md)*
*Para el protocolo de incidentes ver: [INCIDENT_RESPONSE.md](INCIDENT_RESPONSE.md)*
