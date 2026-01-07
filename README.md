# HND-SENTINEL-2029
## Sistema Autónomo de Integridad de Datos Electorales | Automated Electoral Data Integrity System

---

## [ES] Español

### ¿Qué es esto?
**HND-SENTINEL-2029** es un sistema técnico independiente para observar y auditar datos electorales públicos en Honduras. Su función es registrar, normalizar, verificar y analizar cambios en los datos publicados, produciendo reportes técnicos reproducibles.

### ¿Para qué sirve?
- Capturar snapshots de datos públicos por departamento.
- Verificar integridad mediante hashes encadenados (SHA-256).
- Detectar anomalías lógicas y cambios atípicos.
- Generar análisis estadísticos y reportes verificables.
- Publicar alertas técnicas de forma automatizada.

### Componentes principales
- `scripts/download_and_hash.py`: adquisición de datos y hashing.
- `scripts/analyze_rules.py`: análisis de anomalías y tendencias.
- `scripts/post_to_telegram.py`: publicación de alertas.

### Documentación
- Manual de configuración y scraping: `docs/manual.md`
- Fuentes configurables en `config.yaml` (incluye nacional y departamentos).
- Arquitectura: `docs/architecture.md`
- Principios operativos: `docs/operating_principles.md`
- Metodología: `docs/methodology.md`
- Reglas técnicas: `docs/rules.md`
- Formato de datos: `docs/data_format.md`

### Configuración rápida
1. Copia `config.example.yaml` a `config.yaml` en la raíz del repositorio.
2. Edita `config.yaml` con la URL base, headers y fuentes reales de tu entorno.
3. Ejecuta los scripts; el sistema continúa leyendo desde `config.yaml`.

### Estado del proyecto (actual)
- Captura de datos: configurable vía `config.yaml` (fuentes, niveles y mapeo de campos).
- Integridad: snapshots crudos + JSON normalizados + hashes encadenados SHA-256.
- Análisis: reglas de anomalías, tendencias y resúmenes en lenguaje común.
- Publicación: plantillas técnicas neutrales para Telegram y X.
- Fallback de scraping: habilitar `use_playwright: true` en `config.yaml` cuando falle `requests` (requiere `pip install playwright` y `playwright install`).

### Visualizaciones rápidas
- `scripts/visualize_benford.py` genera un gráfico de distribución de primeros dígitos.

### Dashboard
Ejecuta el panel interactivo con Streamlit después de generar snapshots:

1. Instala dependencias: `pip install -r requirements.txt`
2. Ejecuta el dashboard: `streamlit run dashboard.py`
3. Abre el navegador en la URL indicada por Streamlit.

---

## [EN] English

### What is this?
**HND-SENTINEL-2029** is an independent technical system to observe and audit public electoral data in Honduras. Its role is to record, normalize, verify, and analyze changes in published data, producing reproducible technical reports.

### What is it for?
- Capture public data snapshots per department.
- Verify integrity via chained hashes (SHA-256).
- Detect logical anomalies and atypical changes.
- Generate statistical analysis and verifiable reports.
- Publish automated technical alerts.

### Main components
- `scripts/download_and_hash.py`: data acquisition and hashing.
- `scripts/analyze_rules.py`: anomaly and trend analysis.
- `scripts/post_to_telegram.py`: alert publishing.

### Documentation
- Configuration and scraping manual: `docs/manual.md`
- Sources configurable in `config.yaml` (includes national and departments).
- Architecture: `docs/architecture.md`
- Operating principles: `docs/operating_principles.md`
- Methodology: `docs/methodology.md`
- Technical rules: `docs/rules.md`
- Data format: `docs/data_format.md`

### Quick setup
1. Copy `config.example.yaml` to `config.yaml` in the repository root.
2. Edit `config.yaml` with the real base URL, headers, and sources for your environment.
3. Run the scripts; the system still reads from `config.yaml`.

### Project status (current)
- Data capture: configurable via `config.yaml` (sources, levels, and field mapping).
- Integrity: raw snapshots + normalized JSON + chained SHA-256 hashes.
- Analysis: anomaly rules, trends, and plain-language summaries.
- Publishing: neutral technical templates for Telegram and X.
- Scraping fallback: enable `use_playwright: true` in `config.yaml` when `requests` fails (requires `pip install playwright` and `playwright install`).

### Quick visualizations
- `scripts/visualize_benford.py` generates a first-digit distribution chart.

---

**AUDIT_MODE:** ACTIVE | **LICENSE:** MIT | **REPOSITORY_STATUS:** VERIFIED
