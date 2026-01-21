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
Crea o edita `config/config.yaml` en la carpeta `config/`:
```yaml
base_url: "https://<URL_DEL_ENDPOINT>"
timeout: 15
retries: 3
headers:
  User-Agent: "C.E.N.T.I.N.E.L."
backoff_base_seconds: 1
backoff_max_seconds: 30
```

#### Fallback con Playwright si los endpoints fallan
- Activa `use_playwright: true` en `config/config.yaml` y revisa `endpoints`/`fallback_nacional`.
- Instala los navegadores necesarios: `python -m playwright install --with-deps chromium`.
- Asegúrate de ajustar `playwright_user_agent` y `playwright_locale` si el sitio requiere contexto local.
- Si el endpoint nacional cambia, actualiza `endpoints.nacional` y conserva el fallback.

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

### Resumen diario
```bash
python scripts/summarize_findings.py
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
Create or edit `config/config.yaml` inside the `config/` folder:
```yaml
base_url: "https://<ENDPOINT_URL>"
timeout: 15
retries: 3
headers:
  User-Agent: "C.E.N.T.I.N.E.L."
backoff_base_seconds: 1
backoff_max_seconds: 30
```

#### Playwright fallback when endpoints fail
- Enable `use_playwright: true` in `config/config.yaml` and review `endpoints`/`fallback_nacional`.
- Install required browsers: `python -m playwright install --with-deps chromium`.
- Adjust `playwright_user_agent` and `playwright_locale` if the site requires local context.
- If the national endpoint changes, update `endpoints.nacional` and keep the fallback.

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

### Daily summary
```bash
python scripts/summarize_findings.py
```

### Suggested cadence
- Download: every 1 hour
- Reports: every 1–3 hours
- Daily summary: once per day
