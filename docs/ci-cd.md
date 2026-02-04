# CI/CD / Integración y entrega continua

## Resumen / Overview

**ES:** Este documento describe los workflows de GitHub Actions que validan calidad, seguridad y resiliencia del proyecto **centinel-engine**. El objetivo es mantener un pipeline confiable, rápido y reproducible para un proyecto open‑source de alta credibilidad.  
**EN:** This document describes the GitHub Actions workflows that validate quality, security, and resilience for **centinel-engine**. The goal is a reliable, fast, and reproducible pipeline for a high‑credibility open‑source project.

## Workflows activos / Active workflows

### `ci.yml` — Pipeline principal / Main pipeline

**ES:** Se ejecuta en `push` a `main` y `dev-v6`, y en `pull_request`. Incluye matriz de Python 3.10–3.12 y valida estilo, pruebas, cobertura y seguridad.  
**EN:** Runs on `push` to `main` and `dev-v6`, and on `pull_request`. Includes a Python 3.10–3.12 matrix and validates lint, tests, coverage, and security.

**Pasos principales / Core steps:**
- **Checkout / Checkout**: obtiene el código.  
- **Setup Python / Setup Python**: configura versión de Python y cache de Poetry.  
- **Poetry install / Poetry install**: `poetry install --no-root --with dev`.  
- **Lint / Lint**: `flake8` y `black --check`.  
- **Tests / Tests**: `pytest` con `pytest-cov`.  
- **Security / Security**: `bandit` con exclusiones razonables para `tests`, `docs`, `.venv`, `build`, `dist`.

### `lint.yml` — Lint en push / Lint on push

**ES:** Ejecuta el análisis de estilo en cada `push` a `main` y `dev-v6`, con Poetry y cache.  
**EN:** Runs linting on every `push` to `main` and `dev-v6`, using Poetry and caching.

### `test.yml` — Tests en PR / Tests on PR

**ES:** Ejecuta pruebas con cobertura en cada `pull_request`.  
**EN:** Runs tests with coverage on every `pull_request`.

### `chaos-test.yml` — Chaos tests (low) en PR

**ES:** Ejecuta pruebas de caos en modo **low** para PRs (duración reducida), como validación de resiliencia sin sobrecargar el CI.  
**EN:** Runs chaos tests in **low** mode for PRs (short duration) to validate resilience without overloading CI.

## Cómo contribuir sin romper CI / Contributing without breaking CI

**ES:** Recomendaciones para mantener el CI estable:
1. **Instala dependencias con Poetry**:  
   ```bash
   poetry install --no-root --with dev
   ```
2. **Ejecuta lint antes de subir cambios**:  
   ```bash
   poetry run flake8 .
   poetry run black --check .
   ```
3. **Ejecuta pruebas con cobertura**:  
   ```bash
   poetry run pytest --cov=centinel --cov-report=term-missing
   ```
4. **Evita tests largos en PRs**: las pruebas de caos en PR están en modo bajo; para pruebas más intensas, coordina con mantenedores.

**EN:** Recommendations to keep CI stable:
1. **Install dependencies with Poetry**:  
   ```bash
   poetry install --no-root --with dev
   ```
2. **Run lint before pushing**:  
   ```bash
   poetry run flake8 .
   poetry run black --check .
   ```
3. **Run tests with coverage**:  
   ```bash
   poetry run pytest --cov=centinel --cov-report=term-missing
   ```
4. **Avoid long-running tests in PRs**: chaos tests run at low level in PRs; coordinate with maintainers for heavier runs.

## Troubleshooting / Solución de problemas

**ES:**
- **Falla en lint (black/flake8)**: ejecuta los comandos localmente y corrige el estilo antes de volver a hacer `push`.  
- **Falla en tests**: revisa el log de pytest; si es un test flakey, proporciona evidencia reproducible.  
- **Bandit reporta falsos positivos**: documenta la justificación en el PR y, si corresponde, agrega `# nosec` con explicación.  
- **Cache inconsistente**: limpia el cache re‑ejecutando el workflow o incrementando el hash de dependencias.

**EN:**
- **Lint failure (black/flake8)**: run commands locally and fix style issues before pushing again.  
- **Test failure**: inspect pytest logs; if it is flaky, provide a reproducible case.  
- **Bandit false positives**: document the rationale in the PR and add `# nosec` with explanation when appropriate.  
- **Inconsistent cache**: clear cache by re‑running workflows or updating dependency hashes.
