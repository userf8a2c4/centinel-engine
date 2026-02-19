# Resilience / Resiliencia

## Active controls only / Solo controles activos

Este documento describe únicamente mecanismos activos en el flujo actual.
This document describes only active mechanisms in the current flow.

### 1) Client rate limiter
- Token-bucket local para evitar ráfagas y respetar cadencia ética.
- Ajustable por configuración sin cambiar el flujo principal.

### 2) Proxy + User-Agent rotation
- Rotación de identidad de cliente para reducir bloqueos temporales.
- Fallback automático a modo directo si no hay proxy válido.

### 3) Vital signs modes
- `normal`: cadencia base.
- `conservative`: desaceleración ante degradación operativa.
- `critical`: pausa prolongada y prioridad de preservación de evidencia.

### 4) Secure backup
- Backup cifrado de estado crítico y hash chain.
- Multi-destino (local, Dropbox, S3) según credenciales disponibles.

## Operational principle / Principio operativo

Continuidad sin agresividad: preservar evidencia, reducir carga y mantener trazabilidad.
Continuity without aggressiveness: preserve evidence, reduce load, and maintain traceability.


## Métricas públicas recomendadas / Recommended public metrics
- MTTR por incidente recuperable.
- Conteo de eventos `429/503` por ventana operativa.
- Retries efectivos y recoveries por watchdog.
- `resilience_score` por release (ponderado por recuperación, no solo por uptime).
