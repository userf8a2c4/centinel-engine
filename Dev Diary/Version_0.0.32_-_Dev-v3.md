# [ES] Dashboard Streamlit robusto + nuevas vistas analíticas

  /dev: Notas del parche: Versión: v0.0.32 (commit 681ecdd)



# [ES] Notas de Parche – C.E.N.T.I.N.E.L.

**Versión:** v0.0.32  
**Fecha:** 11-ene-2026  
**Autor:** userf8a2c4.

### Resumen
Se reforzó el dashboard de Streamlit con carga de datos resiliente y se añadieron nuevas vistas de análisis (Benford, predicciones y NLP).

### Cambios principales
- **Mejora/Fix:** Carga de snapshots más robusta para el dashboard.  
  - **Por qué:** Evitar fallos cuando no hay datos locales y asegurar la lectura desde GitHub.  
  - **Impacto:** El panel muestra datos aún sin snapshots locales, usando el repositorio como fuente remota.  

- **Mejora/Fix:** Nuevas páginas analíticas en Streamlit (Benford y predicciones/NLP).  
  - **Por qué:** Ofrecer herramientas rápidas de auditoría y tendencias con visualizaciones dedicadas.  
  - **Impacto:** Mayor capacidad de exploración para observadores y auditores en tiempo real.  

- **Mejora/Fix:** Flujo de autoformato con Black en GitHub Actions.  
  - **Por qué:** Mantener estilo consistente en PRs sin intervención manual.  
  - **Impacto:** Menos fricción en revisiones y commits más homogéneos.  

### Cambios técnicos
- Se añadió `sentinel/dashboard/data_loader.py` con lectura local/remota, normalización y filtrado de snapshots con señal numérica.
- `dashboard.py` utiliza helpers de carga para métricas, tendencias y tabla de candidatos basadas en snapshots recientes.
- Se agregaron las páginas `pages/02_benford.py` y `pages/03_predicciones.py` para análisis estadístico y predicciones rápidas.
- Nuevo workflow `.github/workflows/format.yml` para ejecutar Black automáticamente en PRs.

### Notas adicionales
- La lectura remota usa la API de GitHub y `raw.githubusercontent.com` cuando no existen archivos locales.
- Las visualizaciones de predicción usan regresión lineal y resumen automático basado en el último snapshot.

**Objetivo de C.E.N.T.I.N.E.L.:** Monitoreo independiente, neutral y transparente de datos electorales públicos. Solo números. Solo hechos. Código abierto MIT para el pueblo hondureño.


-------------


# [EN] Patch Notes – C.E.N.T.I.N.E.L.

**Version:** v0.0.32  
**Date:** January 11, 2026  
**Author:** userf8a2c4.

### Summary
The Streamlit dashboard was hardened with resilient data loading and new analysis views (Benford, predictions, and NLP).

### Main Changes
- **Improvement/Fix:** More robust snapshot loading for the dashboard.  
  - **Why:** Prevent failures when local data is missing and ensure GitHub can be used as a remote source.  
  - **Impact:** The panel still renders data even without local snapshots.  

- **Improvement/Fix:** New Streamlit analytics pages (Benford and predictions/NLP).  
  - **Why:** Provide quick audit tools and trend insights with dedicated visualizations.  
  - **Impact:** Stronger exploratory capabilities for observers and real-time auditors.  

- **Improvement/Fix:** Black auto-formatting workflow in GitHub Actions.  
  - **Why:** Keep consistent styling in PRs without manual intervention.  
  - **Impact:** Less review friction and more consistent commits.  

### Technical Changes
- Added `sentinel/dashboard/data_loader.py` with local/remote reading, normalization, and signal-based snapshot filtering.
- `dashboard.py` now uses loader helpers for metrics, trends, and candidate tables based on recent snapshots.
- Added `pages/02_benford.py` and `pages/03_predicciones.py` for statistical analysis and quick predictions.
- New `.github/workflows/format.yml` workflow to run Black automatically on PRs.

### Additional Notes
- Remote loading uses the GitHub API and `raw.githubusercontent.com` when local files are unavailable.
- Prediction visualizations use linear regression and an auto-generated summary from the latest snapshot.

**C.E.N.T.I.N.E.L. Goal:** Independent, neutral and transparent monitoring of public electoral data. Only numbers. Only facts. MIT open-source for the Honduran people.
