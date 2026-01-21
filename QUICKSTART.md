# QUICKSTART (5 minutos)

## Español
1. Clona el repo y entra al directorio:
   ```bash
   git clone <repo>
   cd sentinel
   ```
2. Instala dependencias con Poetry:
   ```bash
   poetry install
   ```
3. Configura archivos base (control maestro):
   ```bash
   cp control_master/config.yaml.example control_master/config.yaml
   cp control_master/.env.example control_master/.env
   ```
4. Ajusta `control_master/config.yaml` (URL base, headers, fuentes).
5. Define `master_switch` en **ON/OFF** para habilitar o detener procesos automáticos.
6. Ejecuta la descarga y el análisis:
   ```bash
   poetry run python scripts/download_and_hash.py
   poetry run python scripts/analyze_rules.py
   ```
7. Genera el resumen diario:
   ```bash
   poetry run python scripts/summarize_findings.py
   ```

## English
1. Clone the repo and enter the directory:
   ```bash
   git clone <repo>
   cd sentinel
   ```
2. Install dependencies with Poetry:
   ```bash
   poetry install
   ```
3. Configure base files (master control):
   ```bash
   cp control_master/config.yaml.example control_master/config.yaml
   cp control_master/.env.example control_master/.env
   ```
4. Update `control_master/config.yaml` (base URL, headers, sources).
5. Set `master_switch` to **ON/OFF** to enable or halt automatic processes.
6. Run download + analysis:
   ```bash
   poetry run python scripts/download_and_hash.py
   poetry run python scripts/analyze_rules.py
   ```
7. Generate the daily summary:
   ```bash
   poetry run python scripts/summarize_findings.py
   ```
