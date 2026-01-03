# HND-SENTINEL-2029
## Automated Electoral Data Integrity System | Sistema Autónomo de Integridad de Datos Electorales

---

### [ES] SECCIÓN EN ESPAÑOL

#### 1. NATURALEZA DEL PROYECTO
**HND-SENTINEL-2029** es una infraestructura técnica independiente diseñada para la fiscalización digital de los resultados electorales en Honduras. El sistema actúa como un "Escribano Digital" que registra, firma y audita los flujos de datos públicos en tiempo real.

#### 2. ESPECIFICACIONES DE AUDITORÍA (MÉTODO)
El sistema garantiza la transparencia mediante cuatro pilares técnicos:
* **Integridad Criptográfica:** Cada snapshot de datos es procesado con SHA-256. Cualquier alteración posterior del archivo invalidará la firma.
* **Monitoreo de Monotonicidad:** Detección automática de "votos perdidos" (regresiones) en conteos acumulativos.
* **Correlación de Actas:** Verificación de consistencia entre votos sumados y documentos procesados reportados.
* **Inmutabilidad Histórica:** Registro cronológico inalterable que impide la manipulación retroactiva de la base de datos.

#### 3. COMPONENTES DEL MOTOR
* `download_and_hash.py`: Módulo de adquisición y firma digital.
* `analyze_rules.py`: Algoritmo de detección de anomalías lógicas.
* `post_to_telegram.py`: Interfaz de difusión de alertas técnicas.

#### 4. PROTOCOLO DE CONEXIÓN (API)
El sistema monitorea endpoints REST oficiales utilizando parámetros geográficos (`dept`) y de nivel (`level=PD`), asegurando una captura granular por cada uno de los 18 departamentos.

#### 5. VERIFICACIÓN INDEPENDIENTE
La legitimidad del dato es verificable por cualquier tercero mediante:
`sha256sum data/snapshot_YYYYMMDD_HHMM.json`

---

### [EN] ENGLISH SECTION

#### 1. PROJECT NATURE
**HND-SENTINEL-2029** is an independent technical infrastructure for the digital oversight of electoral results in Honduras. The system functions as a "Digital Notary," recording, signing, and auditing public data streams in real-time.

#### 2. AUDIT SPECIFICATIONS (METHOD)
System transparency is secured through four technical pillars:
* **Cryptographic Integrity:** Every data snapshot is hashed via SHA-256. Any subsequent file alteration invalidates the signature.
* **Monotonicity Monitoring:** Automatic detection of "lost votes" (regressions) in cumulative counts.
* **Tally Correlation:** Consistency verification between total votes and reported processed documents.
* **Historical Immutability:** Unalterable chronological record-keeping that prevents retroactive database manipulation.

#### 3. ENGINE COMPONENTS
* `download_and_hash.py`: Data acquisition and digital signature module.
* `analyze_rules.py`: Logical anomaly detection algorithm.
* `post_to_telegram.py`: Technical alert dissemination interface.

#### 4. CONNECTION PROTOCOL (API)
The system monitors official REST endpoints using geographic (`dept`) and level (`level=PD`) parameters, ensuring granular capture across all 18 departments.

#### 5. INDEPENDENT VERIFICATION
Data legitimacy is independently verifiable by any third party using:
`sha256sum data/snapshot_YYYYMMDD_HHMM.json`

---

**AUDIT_MODE:** ACTIVE | **LICENSE:** MIT | **REPOSITORY_STATUS:** VERIFIED
