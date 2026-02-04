# CI/CD para C.E.N.T.I.N.E.L. / CI/CD for C.E.N.T.I.N.E.L.

## Resumen / Summary
Este repositorio utiliza GitHub Actions para validar calidad, pruebas, seguridad y salud operativa en cada cambio. Los flujos están divididos para mantener claridad y tiempos de ejecución razonables. / This repository uses GitHub Actions to validate quality, tests, security, and operational health on every change. Workflows are split to keep clarity and reasonable runtimes.

## Workflows principales / Main workflows

### 1) `ci.yml` (workflow principal / main workflow)
**Objetivo:** ejecución completa de calidad + pruebas + seguridad en branches principales y PRs. / **Goal:** full quality + tests + security on main branches and PRs.

Incluye: / Includes:
- Matriz Python 3.10–3.12. / Python 3.10–3.12 matrix.
- Instalación con Poetry (`poetry install --no-root`). / Poetry install (`poetry install --no-root`).
- Lint: `flake8` + `black --check`. / Lint: `flake8` + `black --check`.
- Pruebas con cobertura (`pytest --cov`). / Tests with coverage (`pytest --cov`).
- Seguridad con Bandit. / Security scan with Bandit.
- Cache de Poetry + entorno virtual. / Poetry + virtualenv cache.

### 2) `lint.yml` (push)
**Objetivo:** feedback rápido en pushes de estilo y formato. / **Goal:** quick feedback on push for style and formatting.

### 3) `test.yml` (pull_request)
**Objetivo:** pruebas en PRs con matriz de Python. / **Goal:** run tests on PRs with Python matrix.

### 4) `chaos-test.yml` (low level, PRs)
**Objetivo:** ejecutar pruebas de caos a bajo nivel en PRs. / **Goal:** run low-level chaos tests on PRs.

## Cómo contribuir sin romper CI / How to contribute without breaking CI
- **Instalar dependencias con Poetry**: `poetry install`. / **Install dependencies with Poetry**: `poetry install`.
- **Ejecutar lint local**: `poetry run flake8 .` y `poetry run black --check .`. / **Run lint locally**: `poetry run flake8 .` and `poetry run black --check .`.
- **Ejecutar pruebas**: `poetry run pytest --cov=centinel --cov-report=term-missing`. / **Run tests**: `poetry run pytest --cov=centinel --cov-report=term-missing`.
- **Chaos tests (si aplica)**: `poetry run pytest tests/chaos -q`. / **Chaos tests (if applicable)**: `poetry run pytest tests/chaos -q`.
- **Actualizar Poetry lock** cuando se agreguen dependencias. / **Update Poetry lock** when adding dependencies.

## Troubleshooting / Solución de problemas
- **Falla de lint por Black**: asegúrate de ejecutar `poetry run black .` antes del PR. / **Black lint failure**: run `poetry run black .` before PR.
- **Falla de flake8**: revisa estilo y líneas largas; usa exclusiones solo si están justificadas. / **flake8 failure**: check style and long lines; use exclusions only with justification.
- **Bandit reporta falsos positivos**: revisa el contexto y agrega exclusiones específicas con criterio. / **Bandit false positives**: review context and add targeted exclusions with care.
- **Cobertura no sube**: revisa que se haya generado `coverage.xml`. / **Coverage not uploaded**: ensure `coverage.xml` is generated.
- **Cache inválido**: elimina la cache o actualiza el lockfile ejecutando `poetry lock`. / **Invalid cache**: clear cache or update the lockfile by running `poetry lock`.

## Referencias / References
- GitHub Actions: https://docs.github.com/en/actions
- Poetry: https://python-poetry.org/docs/
- Codecov: https://docs.codecov.com/
