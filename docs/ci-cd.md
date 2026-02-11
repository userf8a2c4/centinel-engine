# CI/CD (Bilingüe / Bilingual)

## Objetivo / Objective
Este documento describe el CI actual de C.E.N.T.I.N.E.L. con un flujo único, reproducible y mantenible.
This document describes the current CI setup for C.E.N.T.I.N.E.L. with a single, reproducible, maintainable workflow.

## Diseño actual / Current design
- **Workflow principal:** `.github/workflows/ci.yml`.
- **Jobs obligatorios:** `lint`, `tests`, `security`.
- **Gatillos:** `push` (`main`, `work`, `dev-v*`), `pull_request` y `workflow_dispatch`.
- **Concurrencia:** cancela ejecuciones previas del mismo branch/PR para evitar colas innecesarias.

## Qué valida CI / What CI validates
1. **Lint (Python 3.11)**
   - `flake8 .`
   - `black --check .`
2. **Tests (matriz Python 3.10 y 3.11)**
   - `pytest` con cobertura (`--cov=centinel`).
   - Excluye suites no deterministas/pesadas en el job principal (`tests/chaos`, `tests/integration`).
   - Ejecuta además `tests/resilience/` con cobertura de `scripts`.
3. **Security (Python 3.11)**
   - `bandit -r src -c pyproject.toml`

## Cambios respecto al esquema anterior / Changes vs previous setup
- Se eliminaron workflows redundantes de CI (`lint.yml`, `security.yml`, `chaos.yml`, `sentinel-pipeline.yml`).
- `ci.yml` pasa a ser la única fuente de verdad para calidad, pruebas y seguridad.
- Se normalizan versiones de Python y criterios de ejecución para reducir drift documental.

## Ejecutar localmente / Run locally
Requiere Python 3.10+.

```bash
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m flake8 .
python -m black --check .
python -m pytest --cov=centinel --cov-report=xml --cov-report=term-missing --ignore=tests/chaos --ignore=tests/integration
python -m pytest tests/resilience/ -v --cov=scripts
python -m bandit -r src -c pyproject.toml
```

## Buenas prácticas para contribuir / Contribution guidelines
- Mantener pruebas deterministas en `tests/`.
- Evitar dependencias de red en unit tests.
- Si agregas nueva lógica, añade cobertura y actualiza este documento si cambias CI.
