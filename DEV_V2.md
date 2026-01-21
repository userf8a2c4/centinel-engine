# Dev v2

## Objetivo
Repositorio optimizado para operación ligera, lectura segura y administración asistida por GPT.

## Alcance
- Mantener scraping, normalización y auditoría existentes.
- Reducir piezas no esenciales (reportes PDF y visualizaciones auxiliares).
- Priorizar la consulta de reportes en archivos locales.

## Flujo recomendado (GPT)
1. Verificar snapshots existentes en `data/` y hashes en `hashes/`.
2. Ejecutar `python scripts/download_and_hash.py` para nuevos datos (solo cuando sea necesario).
3. Ejecutar `python scripts/analyze_rules.py` para análisis neutral.
4. Revisar el resumen diario en `reports/summary.txt`.

## Principios
- Solo lectura desde los reportes generados (sin scraping fuera del pipeline).
- Neutralidad y respuestas factuales.
- Sin almacenamiento de datos personales.
