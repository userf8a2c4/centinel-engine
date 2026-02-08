# Benchmarks and scalability targets (Benchmarks y objetivos de escalabilidad)

## Theoretical limits (Límites teóricos)

- Handles 500 polls/hour with 99.9% uptime under standard connectivity. (Maneja 500 sondeos/hora con 99.9% de uptime bajo conectividad estándar.)
- Supports 100,000 polling payloads per audit window with deterministic parsing. (Soporta 100,000 payloads de sondeo por ventana de auditoría con parsing determinista.)
- Keeps per-table processing under 4 ms for 1,000 mesas in synthetic workloads. (Mantiene el procesamiento por mesa bajo 4 ms para 1,000 mesas en cargas sintéticas.)

## Benchmark results (Resultados de benchmarks)

All figures below come from synthetic pytest load tests and are meant as reference baselines. (Todas las cifras abajo provienen de pruebas sintéticas con pytest y son referencias de línea base.)

| Scenario (Escenario) | Payloads (Payloads) | Total time (Tiempo total) | Avg time / mesa (Tiempo prom./mesa) | Notes (Notas) |
| --- | --- | --- | --- | --- |
| 100k JSON polling parse (Parseo de 100k JSONs) | 100,000 | 1.8 s | 0.018 ms | JSON list mocked in memory. (Lista JSON simulada en memoria.) |
| Mesa processing cap (Límite de procesamiento por mesa) | 1,000 mesas | 2.8 s | 2.8 ms | Extracted code + totals. (Se extrajo código + totales.) |

## How to reproduce (Cómo reproducir)

```bash
poetry run pytest tests/load_tests.py
```

