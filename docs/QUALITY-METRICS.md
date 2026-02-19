# Quality Metrics by Rule / Métricas de calidad por regla

## Objetivo
Publicar métricas auditables de calidad analítica por regla (FP/FN, precision, recall, F1) con casos etiquetados revisables.

## Formato de entrada (casos etiquetados)
Cada caso debe incluir:
- `rule_key`
- `predicted_anomaly` (bool)
- `actual_anomaly` (bool)

Se soporta:
- `JSONL` (una línea por caso)
- `JSON` con lista raíz o `{ "cases": [...] }`

## Cálculo
Comando:

```bash
python scripts/rule_quality_metrics.py \
  --input artifacts/labeled_cases.jsonl \
  --output artifacts/rule_quality_metrics.json
```

Salida por regla:
- `tp`, `fp`, `tn`, `fn`
- `precision`, `recall`, `f1`
- `confidence` (rúbrica: `low_sample`, `medium`, `high`, `review_required`)

## Rúbrica de confianza (transparente)
- `low_sample`: menos de 20 casos.
- `high`: precision >= 0.90 y recall >= 0.85.
- `medium`: precision >= 0.75 y recall >= 0.65.
- `review_required`: resto de escenarios.
