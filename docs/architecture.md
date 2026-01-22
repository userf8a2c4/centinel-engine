# Arquitectura de Proyecto C.E.N.T.I.N.E.L.

## [ES] Español

### Visión general
C.E.N.T.I.N.E.L. sigue una arquitectura tipo pipeline para que cada etapa sea **independiente, verificable y auditable**.

**Entrada → Hash → Normalización → Análisis → Almacenamiento → Publicación**

### Componentes principales
- **Fuentes públicas**: endpoints oficiales publicados por instituciones electorales.
- **Ingesta y hashing** (`scripts/download_and_hash.py`): descarga, valida y genera hashes encadenados.
- **Normalización** (`core/`, `src/`): homogeniza estructuras para comparación temporal.
- **Reglas de análisis** (`command_center/rules/`): aplica detección de variaciones y anomalías.
- **Registro histórico** (`data/`, `hashes/`): conserva evidencia inmutable.
- **Publicación y anclaje** (`centinel_engine/`): ancla resultados en L2 para reforzar integridad.

### Flujo de datos (paso a paso)
1. **Captura** de datos públicos en intervalos definidos.
2. **Hashing encadenado** para garantizar integridad y orden temporal.
3. **Normalización** de campos, tipos y estructuras.
4. **Análisis** con reglas deterministas y configurables.
5. **Persistencia** de snapshots y métricas para auditoría.
6. **Publicación** de reportes y eventos detectados.

### Beneficios de esta arquitectura
- **Trazabilidad completa:** cada snapshot se vincula a su fuente, tiempo y hash.
- **Reproducibilidad:** cualquier tercero puede repetir el flujo con las mismas entradas.
- **Modularidad:** puedes reemplazar una etapa sin romper las demás.
- **Seguridad de evidencia:** el encadenamiento de hashes hace visibles las alteraciones.

---

## [EN] English

### Overview
C.E.N.T.I.N.E.L. follows a pipeline architecture so every stage is **independent, verifiable, and auditable**.

**Input → Hash → Normalization → Analysis → Storage → Publishing**

### Core components
- **Public sources**: official endpoints published by electoral institutions.
- **Ingestion and hashing** (`scripts/download_and_hash.py`): downloads, validates, and generates chained hashes.
- **Normalization** (`core/`, `src/`): standardizes structures for time-based comparisons.
- **Analysis rules** (`command_center/rules/`): applies configurable anomaly and variation detection.
- **Historical logging** (`data/`, `hashes/`): preserves immutable evidence.
- **Publishing and anchoring** (`centinel_engine/`): anchors results on L2 to reinforce integrity.

### Data flow (step by step)
1. **Capture** public data on a defined schedule.
2. **Chained hashing** to guarantee integrity and temporal order.
3. **Normalization** of fields, types, and structures.
4. **Analysis** with deterministic, configurable rules.
5. **Persistence** of snapshots and metrics for audit.
6. **Publishing** of technical reports and detected events.

### Benefits of this architecture
- **Full traceability:** each snapshot links to source, time, and hash.
- **Reproducibility:** any third party can re-run the flow with identical inputs.
- **Modularity:** you can replace a stage without breaking the rest.
- **Evidence security:** chained hashes make tampering visible.
