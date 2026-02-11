# Auditoría de workflows de GitHub Actions

Fecha de auditoría: 2026-02-11.

## Resumen ejecutivo

Se revisaron los 7 workflows existentes en `.github/workflows/` para identificar cuáles están alineados con el estado actual del repositorio (`main` como línea principal, estructura `src/`, scripts vigentes) y cuáles muestran señales claras de obsolescencia.

### Clasificación rápida

- **Vigentes / en uso recomendado**: `ci.yml`, `codeql.yml`, `deploy-dashboard.yml`, `scheduler.yml`.
- **Obsoletos o redundantes (recomendado descontinuar)**: `fetcher.yml`, `audit.yml`, `sentinel_visualizer.yml`.

## Inventario detallado

| Workflow | Estado | Motivo técnico |
| --- | --- | --- |
| `.github/workflows/ci.yml` | **Vigente** | CI básica (lint + tests smoke), compatible con estructura actual. |
| `.github/workflows/codeql.yml` | **Vigente** | Escaneo de seguridad estándar para Python y GitHub Actions sobre `main`. |
| `.github/workflows/deploy-dashboard.yml` | **Vigente con ajuste recomendado** | Despliega dashboard en push a `main` y `dev-v6`; `main` es coherente, `dev-v6` parece legado. |
| `.github/workflows/scheduler.yml` | **Vigente (canónico de captura)** | Corre cada 15 minutos, usa `python -m scripts.download_and_hash` y comitea datos. |
| `.github/workflows/fetcher.yml` | **Obsoleto / redundante** | Duplica función de `scheduler.yml`, usa acciones más antiguas (`checkout@v3`, `setup-python@v4`) y empuja a rama fija `dev-v3` (legada). |
| `.github/workflows/audit.yml` | **Obsoleto (rota por referencias ausentes)** | Invoca `scripts/calculate_diffs.py` y `scripts/post_to_telegram.py`, que no existen en el repo actual. |
| `.github/workflows/sentinel_visualizer.yml` | **Obsoleto (rota + ramas legacy)** | Se dispara en `dev`, `dev-v2`, `dev-v3`, y llama `scripts.visualize_benford` inexistente. |

## Evidencia puntual de obsolescencia

### 1) Scripts referenciados que ya no existen

No se encuentran en `scripts/` ni en `src/`:

- `calculate_diffs.py`
- `post_to_telegram.py`
- `visualize_benford.py`

Esto hace que `audit.yml` y `sentinel_visualizer.yml` fallen o estén parcialmente inutilizados.

### 2) Triggers hacia ramas legacy

Hay workflows que dependen de ramas históricas (`dev`, `dev-v2`, `dev-v3`, `dev-v6`) que no representan la línea principal actual. Esto aumenta ruido operativo y mantenimiento innecesario.

### 3) Duplicidad funcional

`scheduler.yml` y `fetcher.yml` cubren prácticamente el mismo objetivo (captura periódica + commit), pero con diferencias de implementación y destino de push, lo que puede generar inconsistencia.

## Recomendación de saneamiento

1. **Mantener**: `ci.yml`, `codeql.yml`, `scheduler.yml`, `deploy-dashboard.yml`.
2. **Descontinuar**: `fetcher.yml`, `audit.yml`, `sentinel_visualizer.yml`.
3. **Ajuste mínimo**: en `deploy-dashboard.yml`, retirar ramas legacy del trigger y dejar `main` (o definir explícitamente ramas activas reales).
4. **Documentar workflow canónico** de captura en `docs/ci-cd.md` para evitar reintroducir duplicados.

## Resultado esperado tras limpieza

- Menos fallos falsos en Actions.
- Menor ambigüedad sobre cuál pipeline opera en producción.
- Menor deuda técnica en automatizaciones.
- Mayor trazabilidad para auditoría externa.
