# CI/CD (Bilingüe / Bilingual)

## Objetivo / Objective
Este documento describe el CI/CD vigente de C.E.N.T.I.N.E.L., con foco en reproducibilidad, trazabilidad y confiabilidad frente a auditorías externas.
This document describes the active C.E.N.T.I.N.E.L. CI/CD setup, focused on reproducibility, traceability, and reliability for external audits.

## Workflows activos / Active workflows

- **CI (`.github/workflows/ci.yml`)**
  - **Trigger:** `push` (`main`, `work`, `dev-v*`), `pull_request`, `workflow_dispatch`.
  - **Jobs:** `lint` (flake8 crítico) + `tests` (smoke suite en Python 3.10/3.11).

- **CodeQL (`.github/workflows/codeql.yml`)**
  - **Trigger:** `push`/`pull_request` sobre `main` + ejecución semanal programada.
  - **Objetivo:** análisis estático de seguridad para `python` y `actions`.

- **Scheduler de captura (`.github/workflows/scheduler.yml`)**
  - **Trigger:** `schedule` cada 15 minutos + ejecución manual.
  - **Objetivo:** ejecutar `python -m scripts.download_and_hash`, persistir snapshots y commitear evidencia.

- **Deploy Dashboard (`.github/workflows/deploy-dashboard.yml`)**
  - **Trigger:** `push` en ramas de despliegue configuradas.
  - **Objetivo:** desplegar `dashboard.py` en Streamlit Community Cloud.

> Nota: ver diagnóstico de legado y obsolescencia en [`docs/workflows-audit.md`](workflows-audit.md).

## Cómo ejecutar validaciones localmente / Local validation

Requiere Python 3.10+.
Requires Python 3.10+.

```bash
python -m pip install -U pip
python -m pip install pytest==8.3.3 python-dateutil "flake8>=7,<8"
```

### Lint

```bash
python -m flake8 . --select=E9,F63,F7,F82 --show-source --statistics
```

### Tests (smoke suite)

```bash
python -m pytest -q tests/test_hashchain.py tests/test_turnout_impossible_rule.py
```

## Buenas prácticas / Contribution guidelines

- Mantener pruebas deterministas en `tests/`.
- Evitar dependencias de red en unit tests.
- Si cambias workflows, actualiza este documento y la auditoría de workflows.
