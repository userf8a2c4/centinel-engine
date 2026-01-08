# Dev v2

## Objetivo
Repositorio optimizado para operación ligera, lectura segura y administración asistida por GPT.

## Alcance
- Mantener scraping, normalización y auditoría existentes.
- Reducir piezas no esenciales (reportes PDF y visualizaciones auxiliares).
- Priorizar el bot Telegram como interfaz de consulta rápida.

## Flujo recomendado (GPT)
1. Verificar snapshots existentes en `data/` y hashes en `hashes/`.
2. Ejecutar `python scripts/download_and_hash.py` para nuevos datos (solo cuando sea necesario).
3. Ejecutar `python scripts/analyze_rules.py` para análisis neutral.
4. Operar el bot con `python bot.py`.

## Principios
- Solo lectura desde el bot (sin scraping dentro del bot).
- Neutralidad y respuestas factuales.
- Sin almacenamiento de datos personales.
