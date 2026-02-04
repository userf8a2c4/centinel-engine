# Resilience Test Suite

## Objetivo / Objective

Español: Esta suite valida la resiliencia operativa del motor Centinel para auditoría electoral pública (solo JSON del CNE a nivel nacional/departamental). Se enfoca en tolerancia a fallas, recuperación y trazabilidad para observadores internacionales.

English: This suite validates operational resilience for Centinel's public election audit engine (CNE JSON at national/department level only). It focuses on fault tolerance, recovery, and traceability for international observers.

## Qué valida / What it validates

- Circuit breaker (CLOSED → OPEN → HALF_OPEN) y recuperación tras cooldown.
- Modo low-profile de polling (intervalo + jitter acotado).
- Reintentos con tenacity: backoff exponencial, jitter, headers persistentes, max_attempts.
- Manejo de errores HTTP (429/503), timeouts y JSON malformado.
- Watchdog: heartbeat stale, grace period y reinicio automático con logging crítico.
- Proxy rotation: round-robin, validación, fallback a directo, agotamiento de pool.

## Cómo correr / How to run

```bash
pytest tests/resilience/ -v --cov=scripts
```

## Notas de reproducibilidad / Reproducibility notes

Español: Todos los tests usan mocks (responses/httpx) y archivos temporales, sin depender de red real. Se incluyen docstrings bilingües y aserciones de logs/tiempos para auditoría confiable.

English: All tests use mocks (responses/httpx) and temporary files, with no real network access. Bilingual docstrings and log/time assertions provide audit-friendly reproducibility.
