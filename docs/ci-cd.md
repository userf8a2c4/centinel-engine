# CI/CD (Bilingüe / Bilingual)

## Objetivo / Objective
Este documento describe el CI actual de C.E.N.T.I.N.E.L. con un flujo único, reproducible y mantenible.
This document describes the current CI setup for C.E.N.T.I.N.E.L. with a single, reproducible, maintainable workflow.

## Diseño actual / Current design
- **Workflow principal:** `.github/workflows/ci.yml`.
- **Jobs obligatorios:** `lint`, `tests`, `coverage`, `security`.
- **Gatillos:** `push` (`main`, `work`, `dev-v*`), `pull_request` y `workflow_dispatch`.
- **Concurrencia:** cancela ejecuciones previas del mismo branch/PR para evitar colas innecesarias.
- **Sin saltos por dependencia de jobs:** los jobs principales no dependen entre sí, por lo que un fallo en uno no provoca que los demás queden en estado `skipped`.
- **Instalación consistente:** tests y coverage usan Poetry en CI (`poetry install --with dev`) para coincidir con `pyproject.toml` y el flujo local.

## Qué valida CI / What CI validates
1. **Lint (Python 3.11)**
   - `flake8 .`
   - `black --check .`
2. **Tests (matriz Python 3.10 y 3.11)**
   - `pytest` para validación funcional general.
   - Excluye suites no deterministas/pesadas en el job principal (`tests/chaos`, `tests/integration`).
   - Ejecuta además `tests/resilience/`.
3. **Coverage (Python 3.11)**
   - Ejecuta tests con cobertura (`--cov=centinel`) y sube `coverage.xml` a Codecov.
4. **Security (Python 3.11)**
   - `bandit -r src -c pyproject.toml`

## Cambios respecto al esquema anterior / Changes vs previous setup
- Se eliminaron workflows redundantes de CI (`lint.yml`, `security.yml`, `chaos.yml`, `sentinel-pipeline.yml`, `format.yml`).
- `ci.yml` pasa a ser la única fuente de verdad para calidad, pruebas y seguridad.
- Se mantuvo una estrategia consistente con Poetry para desarrollo local y colaboración.

## Ejecutar localmente / Run locally
Requiere Python 3.10+ y Poetry.

```bash
poetry install --with dev
poetry run flake8 .
poetry run black --check .
poetry run pytest --ignore=tests/chaos --ignore=tests/integration
poetry run pytest tests/resilience/ -v
poetry run pytest --cov=centinel --cov-report=xml --cov-report=term-missing --ignore=tests/chaos --ignore=tests/integration
poetry run bandit -r src -c pyproject.toml
```

## Buenas prácticas para contribuir / Contribution guidelines
- Mantener pruebas deterministas en `tests/`.
- Evitar dependencias de red en unit tests.
- Si agregas nueva lógica, añade cobertura y actualiza este documento si cambias CI.
