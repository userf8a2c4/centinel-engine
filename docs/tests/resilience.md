# Resilience Test Suite / Suite de Resiliencia

## Objetivo / Objective

**Español:** Esta suite valida la resiliencia operativa del motor Centinel para auditoría electoral pública (solo JSON nacional/departamental del CNE). Se enfoca en tolerancia a fallas, recuperación, trazabilidad y disciplina de reintentos, con credibilidad técnica para matemáticos, ingenieros y observadores internacionales (OEA, Carter Center).

**English:** This suite validates operational resilience for the Centinel engine in public election audits (CNE national/department JSON only). It focuses on fault tolerance, recovery, traceability, and retry discipline to build credibility with mathematicians, engineers, and international observers (OAS, Carter Center).

## Requisitos de entorno / Environment setup

**Español:**
- Python 3.10+ y dependencias de desarrollo instaladas (`poetry install --with dev` o `pip install -r requirements-dev.txt`).
- No se requiere red real: todas las llamadas HTTP están simuladas.

**English:**
- Python 3.10+ and development dependencies installed (`poetry install --with dev` or `pip install -r requirements-dev.txt`).
- No real network is required: all HTTP calls are mocked.

## Comandos / Commands

```bash
pytest tests/resilience/ -v --cov=scripts
```

## Qué validan / What they validate

**Español:**
- Circuit breaker: transición CLOSED → OPEN → HALF_OPEN, tiempo de recuperación y cadencia de alertas.
- Retry con tenacity: backoff exponencial + jitter, headers persistentes, reintentos ante 429/503/timeout, y límites de max_attempts.
- Watchdog: heartbeat stale, respeto de grace period, recuperación con logging y reinicio simulado.
- Proxy rotation: round-robin, validación/fallo de proxies, fallback a directo y recuperación del pool.
- Escenarios CNE: rate-limit 429, 503/timeout, conexión lenta, proxy 403 y JSON malformado parcial.
- Evidencia de resiliencia: `failed_requests.jsonl`, ausencia de excepciones no manejadas.

**English:**
- Circuit breaker: CLOSED → OPEN → HALF_OPEN transitions, recovery timing, and alert cadence.
- Tenacity retries: exponential backoff + jitter, persistent headers, retries on 429/503/timeout, and max_attempts limits.
- Watchdog: stale heartbeat detection, grace period enforcement, recovery logging, and simulated restart.
- Proxy rotation: round-robin, proxy validation/failure, fallback to direct, and pool refresh recovery.
- CNE scenarios: 429 rate-limit, 503/timeout, slow connection, proxy 403, and partially malformed JSON.
- Resilience evidence: `failed_requests.jsonl` writes and no unhandled exceptions.

## Cómo interpretar la cobertura / Interpreting coverage

**Español:**
- `--cov=scripts` mide lógica crítica de resiliencia en scripts operativos (circuit breaker y watchdog).
- Revisar que los caminos de error (timeouts, JSON malformado, proxies fallidos) estén cubiertos.

**English:**
- `--cov=scripts` measures critical resilience logic in operational scripts (circuit breaker and watchdog).
- Ensure error paths (timeouts, malformed JSON, failed proxies) are covered.

## Por qué suma credibilidad en auditoría internacional / Why this adds credibility

**Español:**
- La suite reproduce escenarios realistas de estrés CNE sin alterar datos electorales sensibles.
- Los tests son deterministas, rápidos y trazables, lo que facilita revisiones externas.
- La evidencia de recuperación controlada y registro estructurado fortalece la confianza pública.

**English:**
- The suite reproduces realistic CNE stress scenarios without touching sensitive electoral data.
- Tests are deterministic, fast, and traceable, enabling external review.
- Evidence of controlled recovery and structured logging strengthens public trust.
