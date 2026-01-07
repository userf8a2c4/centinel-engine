# Manual de Configuración y Operación

## [ES] Español

### Requisitos
- Python 3.11+
- Dependencias: `requirements.txt`

### Instalación
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Configuración de scraping (CNE)
Crea o edita `config.yaml` en la raíz del repositorio:
```yaml
base_url: "https://<URL_DEL_ENDPOINT>"
timeout: 15
retries: 3
headers:
  User-Agent: "HND-SENTINEL-2029"
backoff_base_seconds: 1
backoff_max_seconds: 30
```

También puedes usar variables de entorno:
- `BASE_URL`
- `TIMEOUT`
- `RETRIES`
- `HEADERS` (JSON en string)

### Descarga y hash de datos
```bash
python scripts/download_and_hash.py
```
Salida:
- JSON crudos en `data/`
- hashes en `hashes/`

### Análisis de reglas y tendencias
```bash
python scripts/analyze_rules.py
```
Salida:
- `analysis_results.json`
- `analysis_results.parquet` (si hay soporte en el entorno)
- `anomalies_report.json`

### Dashboard local
```bash
streamlit run dashboard.py
```

### Publicación en Telegram
Variables necesarias:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

Ejemplo:
```bash
python scripts/post_to_telegram.py "Reporte técnico" "hashes/snapshot_XX.sha256" neutral
```

### Frecuencia sugerida
- Descarga: cada 1 hora
- Reportes: cada 1–3 horas
- Resumen diario: 1 vez al día

---

## [EN] English

### Requirements
- Python 3.11+
- Dependencies: `requirements.txt`

### Installation
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Scraping configuration (CNE)
Create or edit `config.yaml` in the repository root:
```yaml
base_url: "https://<ENDPOINT_URL>"
timeout: 15
retries: 3
headers:
  User-Agent: "HND-SENTINEL-2029"
backoff_base_seconds: 1
backoff_max_seconds: 30
```

You can also use environment variables:
- `BASE_URL`
- `TIMEOUT`
- `RETRIES`
- `HEADERS` (JSON string)

### Data download and hashing
```bash
python scripts/download_and_hash.py
```
Outputs:
- Raw JSON in `data/`
- Hashes in `hashes/`

### Rules and trend analysis
```bash
python scripts/analyze_rules.py
```
Outputs:
- `analysis_results.json`
- `analysis_results.parquet` (if supported)
- `anomalies_report.json`

### Local dashboard
```bash
streamlit run dashboard.py
```

### Telegram publishing
Required variables:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

Example:
```bash
python scripts/post_to_telegram.py "Technical report" "hashes/snapshot_XX.sha256" neutral
```

### Suggested cadence
- Download: every 1 hour
- Reports: every 1–3 hours
- Daily summary: once per day
