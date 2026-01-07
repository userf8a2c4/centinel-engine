# Flujo de descarga y replay (ejemplo 2025)

## [ES] Español

### Descarga (snapshot + hash)
1. Configura `config.yaml` con el endpoint del CNE.
2. Ejecuta la descarga:
   ```bash
   python scripts/download_and_hash.py
   ```
3. Resultado esperado:
   - `data/`: snapshots crudos por departamento.
   - `hashes/`: hashes SHA-256 encadenados.

### Replay (reprocesar snapshots ya descargados)
Usa snapshots ya guardados para regenerar salidas deterministas:
```bash
python scripts/cli.py run \
  --data-dir tests/fixtures/snapshots_2025 \
  --output-dir docs/examples/replay_2025 \
  --department "Francisco Morazán" \
  --year 2025
```
Salida principal:
- `docs/examples/replay_2025/normalized/` (JSON canónico por snapshot)
- `docs/examples/replay_2025/hashchain.json`
- `docs/examples/replay_2025/anomalies.json`
- `docs/examples/replay_2025/status.json`
- `docs/examples/replay_2025/registry.json`

### Análisis neutral documentado
Para evaluar reglas y tendencias sobre los snapshots normalizados (ejecuta desde `docs/examples/analysis_2025`):
```bash
cd docs/examples/analysis_2025
PYTHONPATH=../.. python -c "from scripts.analyze_rules import run_audit; run_audit('../replay_2025/normalized')"
```
Resultados guardados en `docs/examples/analysis_2025/`:
- `analysis_results.json`
- `anomalies_report.json`
- `reports/summary_es.txt`
- `reports/summary_en.txt`
- `reports/centinel.db` (binario, se genera localmente y no se versiona)

Los textos de resumen son neutrales: describen eventos y métricas sin atribuir intención.

### Reporte neutral de diffs (demo interna)
Genera un reporte de diferencias entre snapshots consecutivos:
```bash
python scripts/replay_2025_demo.py --source-dir docs/examples/replay_2025/normalized --output reports/replay_2025_report.json
```

---

## [EN] English

### Download (snapshot + hash)
1. Configure `config.yaml` with the CNE endpoint.
2. Run the downloader:
   ```bash
   python scripts/download_and_hash.py
   ```
3. Expected output:
   - `data/`: raw snapshots per department.
   - `hashes/`: chained SHA-256 hashes.

### Replay (reprocess stored snapshots)
Use existing snapshots to regenerate deterministic outputs:
```bash
python scripts/cli.py run \
  --data-dir tests/fixtures/snapshots_2025 \
  --output-dir docs/examples/replay_2025 \
  --department "Francisco Morazán" \
  --year 2025
```
Primary outputs:
- `docs/examples/replay_2025/normalized/` (canonical JSON per snapshot)
- `docs/examples/replay_2025/hashchain.json`
- `docs/examples/replay_2025/anomalies.json`
- `docs/examples/replay_2025/status.json`
- `docs/examples/replay_2025/registry.json`

### Documented neutral analysis
To review rules and trends on normalized snapshots (run from `docs/examples/analysis_2025`):
```bash
cd docs/examples/analysis_2025
PYTHONPATH=../.. python -c "from scripts.analyze_rules import run_audit; run_audit('../replay_2025/normalized')"
```
Results stored in `docs/examples/analysis_2025/`:
- `analysis_results.json`
- `anomalies_report.json`
- `reports/summary_es.txt`
- `reports/summary_en.txt`
- `reports/centinel.db` (binary, generated locally and not committed)

The summaries are neutral: they report events and metrics without attributing intent.

### Neutral diff report (internal demo)
Generate a diff report between consecutive snapshots:
```bash
python scripts/replay_2025_demo.py --source-dir docs/examples/replay_2025/normalized --output reports/replay_2025_report.json
```
