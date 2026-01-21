# Scripts

## [ES] Español

Esta carpeta contiene los ejecutables principales del pipeline:

- `download_and_hash.py`: descarga datos por departamento, normaliza y calcula hash.
- `analyze_rules.py`: analiza series temporales y genera reportes de anomalías.
- `summarize_findings.py`: genera resúmenes diarios (si aplica).
- `replay_2025_demo.py`: genera un reporte neutral de diffs para el replay 2025.

Uso típico:
1. Ejecutar `download_and_hash.py` para capturar datos.
2. Ejecutar `analyze_rules.py` para generar reportes.
3. Ejecutar `summarize_findings.py` para generar resúmenes.

---

## [EN] English

This folder contains the main pipeline executables:

- `download_and_hash.py`: downloads department data, normalizes, and hashes.
- `analyze_rules.py`: analyzes time series and generates anomaly reports.
- `summarize_findings.py`: generates daily summaries (if applicable).
- `replay_2025_demo.py`: generates a neutral diff report for the 2025 replay.

Typical usage:
1. Run `download_and_hash.py` to capture data.
2. Run `analyze_rules.py` to generate reports.
3. Run `summarize_findings.py` to produce summaries.
