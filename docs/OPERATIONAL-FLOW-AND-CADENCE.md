# Flujo operativo y cadencia | Operational Flow and Cadence

## Español

### Propósito
Describe el flujo operativo completo de C.E.N.T.I.N.E.L. y las cadencias recomendadas para distintos modos. Se alinea con el [README](../README.md) y con el marco legal de [LEGAL-AND-OPERATIONAL-BOUNDARIES.md](LEGAL-AND-OPERATIONAL-BOUNDARIES.md).

### Flujo operativo detallado (6 pasos)
1. **Captura de datos públicos**
   - Se consultan fuentes oficiales publicadas y accesibles públicamente.
   - Se aplica scraping defensivo y respetuoso para minimizar carga.

2. **Hash criptográfico y encadenamiento**
   - Cada snapshot se firma con hashes criptográficos.
   - Los hashes se encadenan para asegurar integridad histórica.

3. **Normalización y versionado**
   - Se homogeniza estructura de datos para comparaciones consistentes.
   - Se conserva un historial de versiones para auditoría reproducible.

4. **Reglas de análisis (detección técnica)**
   - Se aplican reglas configurables para identificar eventos atípicos.
   - No se interpreta políticamente; se documenta evidencia técnica.

5. **Registro histórico con metadatos**
   - Se almacena fecha, fuente, hash, diffs y resultado de reglas.
   - Se garantiza trazabilidad para auditoría externa.

6. **Reportes técnicos y publicación controlada**
   - Se generan reportes reproducibles basados en evidencia.
   - Listos para revisión por terceros y expansión a formatos PDF.

> Ver más detalles metodológicos en [METHODOLOGY.md](METHODOLOGY.md).

### Cadencias recomendadas

| Modo | Frecuencia | Objetivo |
| --- | --- | --- |
| **Mantenimiento / desarrollo** | 1 vez al mes | Validar pipeline y mantener integridad básica. |
| **Monitoreo normal** | Cada 24–72 horas | Seguimiento regular con bajo impacto. |
| **Elección activa** | Cada 5–15 minutos | Detección cercana en periodos críticos. |

### Señales para ajustar la cadencia
- **Aumentar frecuencia** si hay cambios recurrentes en fuentes oficiales.
- **Reducir frecuencia** si se detecta presión de carga o limitaciones técnicas.
- **Coordinar ventanas** con responsables de infraestructura para evitar sobrecargas.

### Enlaces relacionados
- [README](../README.md)
- [LEGAL-AND-OPERATIONAL-BOUNDARIES.md](LEGAL-AND-OPERATIONAL-BOUNDARIES.md)
- [METHODOLOGY.md](METHODOLOGY.md)
- [SECURITY-AND-SECRETS.md](SECURITY-AND-SECRETS.md)

---

## English

### Purpose
Describes the full operational flow of C.E.N.T.I.N.E.L. and recommended cadences for different modes. It aligns with the [README](../README.md) and the legal framework in [LEGAL-AND-OPERATIONAL-BOUNDARIES.md](LEGAL-AND-OPERATIONAL-BOUNDARIES.md).

### Detailed operational flow (6 steps)
1. **Capture public data**
   - Queries official publicly available sources.
   - Applies defensive, respectful scraping to minimize load.

2. **Cryptographic hashing and chaining**
   - Each snapshot is signed with cryptographic hashes.
   - Hashes are chained to ensure historical integrity.

3. **Normalization and versioning**
   - Data structure is normalized for consistent comparisons.
   - Version history is preserved for reproducible audits.

4. **Rule-based analysis (technical detection)**
   - Configurable rules flag atypical events.
   - No political interpretation; only technical evidence is recorded.

5. **Historical logging with metadata**
   - Stores timestamp, source, hash, diffs, and rule results.
   - Ensures traceability for external auditing.

6. **Technical reports and controlled publication**
   - Generates reproducible reports based on evidence.
   - Ready for third-party review and future PDF expansion.

> See methodological detail in [METHODOLOGY.md](METHODOLOGY.md).

### Recommended cadences

| Mode | Frequency | Goal |
| --- | --- | --- |
| **Maintenance / development** | Once per month | Validate pipeline and maintain baseline integrity. |
| **Normal monitoring** | Every 24–72 hours | Regular tracking with low impact. |
| **Active election** | Every 5–15 minutes | Near-real-time detection during critical periods. |

### Signals to adjust cadence
- **Increase frequency** if official sources change frequently.
- **Reduce frequency** if load pressure or technical limits appear.
- **Coordinate windows** with infrastructure owners to avoid overload.

### Related links
- [README](../README.md)
- [LEGAL-AND-OPERATIONAL-BOUNDARIES.md](LEGAL-AND-OPERATIONAL-BOUNDARIES.md)
- [METHODOLOGY.md](METHODOLOGY.md)
- [SECURITY-AND-SECRETS.md](SECURITY-AND-SECRETS.md)
