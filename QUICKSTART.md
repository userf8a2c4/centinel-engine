# QUICKSTART (5 minutos)

## Español
1. Clona el repo y entra al directorio:
   ```bash
   git clone <repo>
   cd sentinel
   ```
2. Instala dependencias:
   ```bash
   pip install -r requirements.txt
   playwright install
   ```
3. Configura archivos base:
   ```bash
   mkdir -p config
   cp config.example.yaml config/config.yaml
   ```
4. Ajusta `config/config.yaml` (URL base, headers, fuentes).
5. Define `master_switch` en **ON/OFF** para habilitar o detener procesos automáticos.
6. Ejecuta la descarga y el análisis:
   ```bash
   python scripts/download_and_hash.py
   python scripts/analyze_rules.py
   ```
7. Lanza el dashboard:
   ```bash
   streamlit run dashboard.py
   ```

## English
1. Clone the repo and enter the directory:
   ```bash
   git clone <repo>
   cd sentinel
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   playwright install
   ```
3. Set up base files:
   ```bash
   mkdir -p config
   cp config.example.yaml config/config.yaml
   ```
4. Update `config/config.yaml` (base URL, headers, sources).
5. Set `master_switch` to **ON/OFF** to enable or halt automatic processes.
6. Run download + analysis:
   ```bash
   python scripts/download_and_hash.py
   python scripts/analyze_rules.py
   ```
7. Launch the dashboard:
   ```bash
   streamlit run dashboard.py
   ```
