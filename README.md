# Proyecto C.E.N.T.I.N.E.L.
**Centinela Electrónico Neutral Transparente Íntegro Nacional Electoral Libre**

---

## Español (prioridad)

### ¿Qué es Centinel?
Centinel es un sistema técnico independiente para observar y auditar datos electorales públicos en Honduras. Registra, normaliza y verifica cambios en datos publicados para producir reportes técnicos reproducibles y trazables.

### ¿Por qué importa?
La integridad electoral requiere evidencia verificable. Centinel aporta transparencia técnica mediante snapshots, hashes encadenados y análisis de anomalías con enfoque ciudadano y neutral.

### Marco legal y límites de operación (Honduras)
Este proyecto se sustenta en el derecho de acceso a la información pública y en la obligación de publicar información por medios electrónicos.

Referencias normativas principales:
- **Ley de Transparencia y Acceso a la Información Pública** (Decreto 170-2006, reformas Decreto 60-2022).
- **Art. 3 y 4:** Reconocen el derecho ciudadano a acceder a información pública.
- **Art. 5:** Establece la obligación de facilitar el acceso por medios electrónicos.

Alcance operativo:
- Centinel opera con finalidad de auditoría técnica y evidencia reproducible.
- No interfiere con sistemas oficiales ni sustituye a autoridades electorales.
- No procesa datos personales; solo usa fuentes públicas.
- Aplica scraping defensivo y respetuoso para evitar sobrecargas.

### ¿Qué problema resuelve?
- **Evidencia verificable:** conserva snapshots con hashes encadenados para que cualquier tercero pueda confirmar integridad.
- **Transparencia técnica:** transforma datos públicos en registros auditables sin interpretación partidaria.
- **Trazabilidad histórica:** permite comparar versiones a lo largo del tiempo y detectar cambios relevantes.

### ¿Cómo funciona el flujo operativo?
1. **Captura de datos públicos** desde fuentes oficiales publicadas.
2. **Hash criptográfico y encadenamiento** para garantizar integridad.
3. **Normalización** para comparar estructuras en el tiempo.
4. **Reglas de análisis** para identificar eventos atípicos o inconsistencias.
5. **Registro histórico** con metadatos reproducibles.
6. **Reportes técnicos** listos para auditoría externa.

### Beneficios clave
- **Neutralidad técnica:** no acusa ni interpreta, solo registra y compara.
- **Reproducibilidad total:** cada resultado puede replicarse con las mismas fuentes y reglas.
- **Escalabilidad operativa:** diseñado para operación periódica o intensiva en elecciones activas.
- **Seguridad de evidencia:** hashes y metadatos evitan alteraciones silenciosas.

### Estado actual
- **AUDIT ACTIVE**

### Control centralizado
El único punto de control editable es **`command_center/`**.

- `command_center/` es la fuente de verdad de configuración operativa.
- Todo el control se concentra aquí para evitar redundancias y ambigüedad.

### Componentes del repositorio
- **command_center/**: configuración operativa centralizada y panel de control.
- **centinel_engine/**: motor separado en Node.js para anclaje de hashes y publicación en L2.
- **scripts/**: automatizaciones para descarga, hash, análisis y reportes.
- **docs/**: documentación técnica y guías de operación.
- **Nota de operación:** la interacción es por scripts/CLI; no hay UI de Streamlit incluida.

### Primeros pasos (5 minutos)
1. Instala dependencias con Poetry:
   ```bash
   poetry install
   ```
2. Inicializa archivos de configuración:
   ```bash
   poetry run python scripts/bootstrap.py
   ```
   Alternativa rápida:
   ```bash
   make init
   ```
3. Configura fuentes y secretos en `command_center/config.yaml` y `command_center/.env`.
4. Genera un snapshot inicial:
   ```bash
   poetry run python scripts/download_and_hash.py
   ```
5. Ejecuta el análisis:
   ```bash
   poetry run python scripts/analyze_rules.py
   ```
6. (Opcional) Genera un resumen:
   ```bash
   poetry run python scripts/summarize_findings.py
   ```
7. (Alternativa) Ejecuta el pipeline completo:
   ```bash
   poetry run python scripts/run_pipeline.py --once
   ```
   Alternativa rápida:
   ```bash
   make pipeline
   ```

### Cadencia operativa recomendada
- **Modo mantenimiento/desarrollo:** scraping y anclaje en L2 **1 vez al mes**.
- **Modo monitoreo normal:** entre **24 y 72 horas**.
- **Modo elección activa:** entre **5 y 15 minutos**.

### Producción con Docker
- Construye la imagen:
  ```bash
  docker build -t centinel_engine .
  ```
- Levanta servicios (cron):
  ```bash
  docker compose up -d
  ```

### Enlaces destacados
- [Guía rápida](QUICKSTART.md)
- [Manual de operación](docs/manual.md)
- [Arquitectura](docs/architecture.md)
- [Metodología](docs/methodology.md)
- [Contribución](CONTRIBUTING.md)
- [Roadmap](ROADMAP.md)
- [Diario de desarrollo](Dev%20Diary/)
- [Seguridad](Security.md)
- [Licencia: MIT](LICENSE)

## Gestión de Secrets y Backup
Consulta las instrucciones de resguardo seguro en [docs/SECRETS_BACKUP.md](docs/SECRETS_BACKUP.md).

### Agradecimientos
Gracias a la comunidad cívica, periodistas de datos y personas voluntarias que promueven transparencia electoral con evidencia verificable.

---

## English

### What is Centinel?
Centinel is an independent technical system to observe and audit public electoral data in Honduras. It records, normalizes, and verifies changes in published data to produce reproducible, traceable technical reports.

### Why does it matter?
Electoral integrity needs verifiable evidence. Centinel provides technical transparency through snapshots, chained hashes, and anomaly analysis with a neutral, civic-first focus.

### Legal basis and operating boundaries (Honduras)
This project is grounded in the right to access public information and the obligation to publish information through electronic means.

Primary legal references:
- **Law on Transparency and Access to Public Information** (Decree 170-2006, amended by Decree 60-2022).
- **Arts. 3 & 4:** Recognize the citizen right to access public information.
- **Art. 5:** Establishes the obligation to facilitate access through electronic means.

Operational scope:
- Centinel operates for technical auditing and reproducible evidence.
- It does not interfere with official systems or replace electoral authorities.
- It does not process personal data; it only uses public sources.
- It applies defensive, respectful scraping to avoid overload.

### What problem does it solve?
- **Verifiable evidence:** preserves snapshots with chained hashes so any third party can confirm integrity.
- **Technical transparency:** turns public data into auditable records without partisan interpretation.
- **Historical traceability:** enables comparisons across versions over time to spot meaningful changes.

### How does the operational flow work?
1. **Capture public data** from official published sources.
2. **Cryptographic hash chaining** to guarantee integrity.
3. **Normalization** to compare structures over time.
4. **Rule-based analysis** to flag anomalies or inconsistencies.
5. **Historical logging** with reproducible metadata.
6. **Technical reports** ready for external auditing.

### Key benefits
- **Technical neutrality:** no accusations, no interpretation—only recording and comparison.
- **Full reproducibility:** every result can be replicated with the same sources and rules.
- **Operational scalability:** designed for periodic or high-frequency monitoring during elections.
- **Evidence security:** hashes and metadata prevent silent tampering.

### Current status
- **AUDIT ACTIVE**

### Centralized control
The only editable control point is **`command_center/`**.

- `command_center/` is the source of truth for operational configuration.
- All control is centralized here to avoid redundancy and ambiguity.

### Repository components
- **command_center/**: centralized operational configuration and control panel.
- **centinel_engine/**: separate Node.js engine for hash anchoring and L2 publishing.
- **scripts/**: automations for downloads, hashing, analysis, and reporting.
- **docs/**: technical documentation and operating guides.
- **Operational note:** interaction is via scripts/CLI; there is no bundled Streamlit UI.

### Quick start (5 minutes)
1. Install dependencies with Poetry:
   ```bash
   poetry install
   ```
2. Initialize configuration files:
   ```bash
   poetry run python scripts/bootstrap.py
   ```
   Quick alternative:
   ```bash
   make init
   ```
3. Configure sources and secrets in `command_center/config.yaml` and `command_center/.env`.
4. Generate an initial snapshot:
   ```bash
   poetry run python scripts/download_and_hash.py
   ```
5. Run the analysis:
   ```bash
   poetry run python scripts/analyze_rules.py
   ```
6. (Optional) Build a summary:
   ```bash
   poetry run python scripts/summarize_findings.py
   ```
7. (Alternative) Run the full pipeline:
   ```bash
   poetry run python scripts/run_pipeline.py --once
   ```
   Quick alternative:
   ```bash
   make pipeline
   ```

### Recommended operating cadence
- **Maintenance/development mode:** scraping and L2 anchoring **once per month**.
- **Normal monitoring mode:** between **24 and 72 hours**.
- **Active election mode:** between **5 and 15 minutes**.

### Production with Docker
- Build the image:
  ```bash
  docker build -t centinel_engine .
  ```
- Start services (cron):
  ```bash
  docker compose up -d
  ```

### Key links
- [Quickstart guide](QUICKSTART.md)
- [Operations manual](docs/manual.md)
- [Architecture](docs/architecture.md)
- [Methodology](docs/methodology.md)
- [Contributing](CONTRIBUTING.md)
- [Roadmap](ROADMAP.md)
- [Dev diary](Dev%20Diary/)
- [Security](Security.md)
- [License: MIT](LICENSE)

## Secrets management and backup
See the secure backup guide at [docs/SECRETS_BACKUP.md](docs/SECRETS_BACKUP.md).

### Thanks
Thanks to civic community members, data journalists, and volunteers advancing electoral transparency through verifiable evidence.
