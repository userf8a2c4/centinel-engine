# Guía rápida / Quickstart

## Español

Esta guía resume el arranque mínimo de **Centinel (C.E.N.T.I.N.E.L.)** en producción.

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
3. Ajusta `command_center/config.yaml` y `command_center/.env` (URL base, headers, fuentes).
4. Genera un snapshot inicial:
   ```bash
   poetry run python scripts/download_and_hash.py
   ```
5. Ejecuta el análisis:
   ```bash
   poetry run python scripts/analyze_rules.py
   ```
6. (Alternativa) Ejecuta todo el pipeline:
   ```bash
   poetry run python scripts/run_pipeline.py --once
   ```
   Alternativa rápida:
   ```bash
   make pipeline
   ```

---

## English

This guide summarizes the minimum startup for **Centinel (C.E.N.T.I.N.E.L.)** in production.

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
3. Update `command_center/config.yaml` and `command_center/.env` (base URL, headers, sources).
4. Generate an initial snapshot:
   ```bash
   poetry run python scripts/download_and_hash.py
   ```
5. Run the analysis:
   ```bash
   poetry run python scripts/analyze_rules.py
   ```
6. (Alternative) Run the full pipeline:
   ```bash
   poetry run python scripts/run_pipeline.py --once
   ```
   Quick alternative:
   ```bash
   make pipeline
   ```
