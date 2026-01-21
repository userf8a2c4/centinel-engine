# Guía rápida / Quickstart

## Español

1. Instala dependencias con Poetry:
   ```bash
   poetry install
   ```
2. Copia las plantillas de configuración:
   ```bash
   cp command_center/config.yaml.example command_center/config.yaml
   cp command_center/.env.example command_center/.env
   ```
3. Ajusta `command_center/config.yaml` (URL base, headers, fuentes).
4. Genera un snapshot inicial:
   ```bash
   poetry run python scripts/download_and_hash.py
   ```
5. Ejecuta el análisis:
   ```bash
   poetry run python scripts/analyze_rules.py
   ```

---

## English

1. Install dependencies with Poetry:
   ```bash
   poetry install
   ```
2. Copy the configuration templates:
   ```bash
   cp command_center/config.yaml.example command_center/config.yaml
   cp command_center/.env.example command_center/.env
   ```
3. Update `command_center/config.yaml` (base URL, headers, sources).
4. Generate an initial snapshot:
   ```bash
   poetry run python scripts/download_and_hash.py
   ```
5. Run the analysis:
   ```bash
   poetry run python scripts/analyze_rules.py
   ```
