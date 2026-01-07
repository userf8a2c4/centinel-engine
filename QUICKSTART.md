# QUICKSTART

## Dashboard
1. Instala dependencias: `pip install -r requirements.txt`
2. Ejecuta el dashboard: `streamlit run dashboard.py`
3. Abre la URL indicada por Streamlit.

## Exportar CSV desde el dashboard
- Usa los botones **Descargar snapshots (CSV)** y **Descargar alertas (CSV)** en la vista principal.

## Generar y descargar PDF
1. Genera primero los JSON de análisis:
   - `python scripts/analyze_rules.py` (crea `analysis_results.json` y `anomalies_report.json`).
2. Crea el PDF:
   - `python scripts/export_report.py`
3. Descarga desde el dashboard:
   - En la barra lateral, haz clic en **Descargar reporte PDF** (usa `reports/latest_report.pdf`).

## Ubicación de archivos
- PDF: `reports/report_<timestamp>.pdf` y `reports/latest_report.pdf`
- CSV: descargados desde el navegador en tu carpeta de descargas
