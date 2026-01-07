# Scripts

## [ES] Español

Esta carpeta contiene los ejecutables principales del pipeline:

- `download_and_hash.py`: descarga datos por departamento, normaliza y calcula hash.
- `analyze_rules.py`: analiza series temporales y genera reportes de anomalías.
- `post_to_telegram.py`: publica alertas técnicas en Telegram.
- `summarize_findings.py`: genera resúmenes diarios (si aplica).

Uso típico:
1. Ejecutar `download_and_hash.py` para capturar datos.
2. Ejecutar `analyze_rules.py` para generar reportes.
3. Ejecutar `post_to_telegram.py` para difundir resultados.

---

## [EN] English

This folder contains the main pipeline executables:

- `download_and_hash.py`: downloads department data, normalizes, and hashes.
- `analyze_rules.py`: analyzes time series and generates anomaly reports.
- `post_to_telegram.py`: publishes technical alerts to Telegram.
- `summarize_findings.py`: generates daily summaries (if applicable).

Typical usage:
1. Run `download_and_hash.py` to capture data.
2. Run `analyze_rules.py` to generate reports.
3. Run `post_to_telegram.py` to publish results.
