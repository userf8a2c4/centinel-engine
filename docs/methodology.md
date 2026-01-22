# Metodología Operativa

## [ES] Español

### Objetivo
Estandarizar un flujo reproducible para capturar datos públicos, preservar evidencia y reportar cambios de forma neutral.

### Flujo metodológico
1. **Descarga de datos públicos**
   - Consulta endpoints oficiales publicados.
   - Registra timestamps y metadatos de origen.
2. **Hash criptográfico**
   - Genera hashes SHA-256 y los encadena para preservar integridad y secuencia.
3. **Normalización**
   - Homologa estructuras, nombres de campos y tipos para comparación histórica.
4. **Aplicación de reglas**
   - Ejecuta reglas deterministas para detectar cambios, inconsistencias o eventos atípicos.
5. **Registro histórico**
   - Almacena snapshots, hashes y resultados en formatos auditables.
6. **Publicación automática**
   - Emite reportes técnicos y conserva evidencia accesible para auditoría externa.

### Resultados esperados
- Snapshots verificables con hashes encadenados.
- Reportes técnicos reproducibles.
- Historial transparente de variaciones y eventos.

### Beneficios metodológicos
- **Neutralidad:** separa observación técnica de interpretación política.
- **Reproducibilidad:** cualquier tercero puede repetir el análisis.
- **Trazabilidad:** cada dato tiene fuente, tiempo y hash asociado.

No hay intervención humana durante la ejecución automática.

---

## [EN] English

### Goal
Standardize a reproducible flow to capture public data, preserve evidence, and report changes in a neutral way.

### Methodological flow
1. **Public data download**
   - Queries official published endpoints.
   - Records timestamps and source metadata.
2. **Cryptographic hashing**
   - Generates SHA-256 hashes and chains them to preserve integrity and sequence.
3. **Normalization**
   - Standardizes structures, field names, and types for historical comparison.
4. **Rule application**
   - Runs deterministic rules to detect changes, inconsistencies, or anomalies.
5. **Historical logging**
   - Stores snapshots, hashes, and results in auditable formats.
6. **Automatic publication**
   - Releases technical reports and preserves evidence for external audit.

### Expected outputs
- Verifiable snapshots with chained hashes.
- Reproducible technical reports.
- Transparent history of variations and events.

### Methodological benefits
- **Neutrality:** separates technical observation from political interpretation.
- **Reproducibility:** any third party can repeat the analysis.
- **Traceability:** each data point has source, time, and hash.

There is no human intervention during automated execution.
