# Proyecto C.E.N.T.I.N.E.L.
## Centinela Electrónico Neutral Transparente Íntegro Nacional Electoral Libre
## Sistema Autónomo de Integridad de Datos Electorales | Automated Electoral Data Integrity System

---

## [ES] Español

### Primeros pasos (5 minutos)
1. Instala dependencias: `pip install -r requirements.txt`
2. Copia `config.example.yaml` a `config.yaml` y ajusta las fuentes principales.
3. Genera un snapshot inicial: `python scripts/download_and_hash.py`
4. Revisa los resultados en `data/` y los hashes en `hashes/`.
5. (Opcional) Abre el dashboard: `streamlit run dashboard.py`

### ¿Qué es esto?
**Proyecto C.E.N.T.I.N.E.L.** es un sistema técnico independiente para observar y auditar datos electorales públicos en Honduras. Su función es registrar, normalizar, verificar y analizar cambios en los datos publicados, produciendo reportes técnicos reproducibles.

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
- Inicio rápido: `QUICKSTART.md`
- Manual de configuración y scraping: `docs/manual.md`
- Fuentes configurables en `config.yaml` (incluye nacional y departamentos).
- Arquitectura: `docs/architecture.md`
- Principios operativos: `docs/operating_principles.md`
- Metodología: `docs/methodology.md`
- Reglas técnicas: `docs/rules.md`
- Formato de datos: `docs/data_format.md`
- Guía rápida (5 minutos): `QUICKSTART.md`

### Configuración rápida
1. Copia `config.example.yaml` a `config.yaml` en la raíz del repositorio.
2. Edita `config.yaml` con la URL base, headers y fuentes reales de tu entorno.
3. Ejecuta los scripts; el sistema continúa leyendo desde `config.yaml`.
4. Copia `.env.example` a `.env` para configurar tokens y logging.

### Estado del proyecto (actual)
- Captura de datos: configurable vía `config.yaml` (fuentes, niveles y mapeo de campos).
- Integridad: snapshots crudos + JSON normalizados + hashes encadenados SHA-256.
- Análisis: reglas de anomalías, tendencias y resúmenes en lenguaje común.
- Publicación: plantillas técnicas neutrales para Telegram y X.
- Fallback de scraping: habilitar `use_playwright: true` en `config.yaml` (incluye modo stealth básico y requiere `playwright install`).

### Dashboard
Ejecuta el panel interactivo con Streamlit después de generar snapshots:

1. Instala dependencias (incluye Streamlit): `pip install -r requirements.txt`
2. Ejecuta el dashboard: `streamlit run dashboard.py`
3. Abre el navegador en la URL indicada por Streamlit.
4. Usa el botón “Actualizar datos ahora” para refrescar snapshots.
5. Descarga reportes en CSV desde la sección “Exportar reportes”.

#### Cómo usar el dashboard
- Copia `.env.example` a `.env` si publicarás alertas (Telegram).
- Asegúrate de tener snapshots en `data/` y hashes en `hashes/`.
- El modo debug permite inspeccionar el JSON del último snapshot.

### Cómo usar dashboard
1. Genera datos con `python scripts/download_and_hash.py` o deja que otro proceso actualice `data/`.
2. Inicia el panel con `streamlit run dashboard.py`.
3. Verifica la carpeta `data/` para snapshots `.json` y `hashes/` para `.sha256`.
4. Revisa alertas en `data/alerts.json` (si existe) o `alerts.log`.

**Troubleshooting**
- Si no hay snapshots, el panel mostrará un aviso para ejecutar `download_and_hash.py`.
- Si falta `alerts.json`/`alerts.log`, el panel seguirá funcionando y mostrará "No hay alertas recientes".
- Usa el botón "Actualizar datos ahora" para disparar una recarga sin bloquear el panel.

### Reportes y exportaciones
- Exportar CSV desde el dashboard:
  - Usa los botones **Descargar snapshots (CSV)** y **Descargar alertas (CSV)**.

---

## [EN] English

### What is this?
**Proyecto C.E.N.T.I.N.E.L.** is an independent technical system to observe and audit public electoral data in Honduras. Its role is to record, normalize, verify, and analyze changes in published data, producing reproducible technical reports.

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
- 5-minute quickstart guide: `QUICKSTART.md`

### Quick setup
1. Copy `config.example.yaml` to `config.yaml` in the repository root.
2. Edit `config.yaml` with the real base URL, headers, and sources for your environment.
3. Run the scripts; the system still reads from `config.yaml`.
4. Copy `.env.example` to `.env` to configure tokens and logging.

### Project status (current)
- Data capture: configurable via `config.yaml` (sources, levels, and field mapping).
- Integrity: raw snapshots + normalized JSON + chained SHA-256 hashes.
- Analysis: anomaly rules, trends, and plain-language summaries.
- Publishing: neutral technical templates for Telegram and X.
- Scraping fallback: enable `use_playwright: true` in `config.yaml` (includes basic stealth and requires `playwright install`).

### Dashboard
Run the interactive Streamlit panel after generating snapshots:

1. Install dependencies: `pip install -r requirements.txt`
2. Start the dashboard: `streamlit run dashboard.py`
3. Open the URL shown by Streamlit in your browser.
4. Use “Actualizar datos ahora” to refresh snapshots.
5. Download CSV reports from “Exportar reportes”.

#### How to use the dashboard
- Copy `.env.example` to `.env` if you will publish alerts (Telegram).
- Ensure snapshots exist in `data/` and hashes in `hashes/`.
- Debug mode shows raw JSON for the latest snapshot.

---

**AUDIT_MODE:** ACTIVE | **LICENSE:** MIT | **REPOSITORY_STATUS:** VERIFIED
