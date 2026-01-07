# Reportes locales

`centinel.db` se genera al ejecutar `scripts/analyze_rules.py`.
No se versiona porque es un archivo binario.

Para recrearlo:
```bash
cd docs/examples/analysis_2025
PYTHONPATH=../.. python -c "from scripts.analyze_rules import run_audit; run_audit('../replay_2025/normalized')"
```
