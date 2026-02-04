# CI/CD (Bilingüe / Bilingual)

## Objetivo / Objective
Este documento describe el CI para C.E.N.T.I.N.E.L., con foco en reproducibilidad, trazabilidad y confiabilidad frente a auditorías externas (matemáticos, ingenieros, OEA, Carter Center). Cada workflow separa responsabilidades y reporta resultados claros. 
This document describes the CI for C.E.N.T.I.N.E.L., focused on reproducibility, traceability, and reliability for external audits (mathematicians, engineers, OEA, Carter Center). Each workflow separates responsibilities and reports clear results.

## Resumen de workflows / Workflow summary
- **Lint (push)**: `flake8` + `black --check`. Rápido y determinista. 
  **Lint (push)**: `flake8` + `black --check`. Fast and deterministic.
- **Test (pull_request)**: `pytest` con `pytest-cov` y matriz Python 3.10–3.12. Publica `coverage.xml` como artefacto y reporta a Codecov. 
  **Test (pull_request)**: `pytest` with `pytest-cov` and Python 3.10–3.12 matrix. Publishes `coverage.xml` as artifact and reports to Codecov.
- **Security (push/pull_request)**: `bandit` con exclusiones razonables para reducir falsos positivos. 
  **Security (push/pull_request)**: `bandit` with reasonable exclusions to reduce false positives.
- **Chaos (pull_request, opcional)**: ejecuta `scripts/chaos_test.py` en modo ligero. 
  **Chaos (pull_request, optional)**: runs `scripts/chaos_test.py` in light mode.

## Reproducibilidad y credibilidad / Reproducibility and credibility
- Se fija la matriz de versiones de Python y se usa Poetry con `--no-root --no-interaction --no-ansi`. 
  Python versions are pinned in a matrix and Poetry uses `--no-root --no-interaction --no-ansi`.
- Se cachea `.venv` y `~/.cache/pypoetry` para mejorar velocidad y estabilidad. 
  `.venv` and `~/.cache/pypoetry` are cached to improve speed and stability.
- `pytest` usa `--import-mode=importlib` y `PYTHONPATH=src` para evitar fallas de discovery. 
  `pytest` uses `--import-mode=importlib` and `PYTHONPATH=src` to avoid discovery failures.

## Configuración clave / Key configuration
- **Coverage**: `.coveragerc` excluye `tests/` y `chaos_test.py`. 
  **Coverage**: `.coveragerc` excludes `tests/` and `chaos_test.py`.
- **Pytest**: `pyproject.toml` define `testpaths`, `pythonpath` y `--import-mode=importlib`. 
  **Pytest**: `pyproject.toml` defines `testpaths`, `pythonpath`, and `--import-mode=importlib`.
- **Bandit**: `pyproject.toml` excluye `tests/` y `chaos_test.py`, y evita falsos positivos comunes (`B101`). 
  **Bandit**: `pyproject.toml` excludes `tests/` and `chaos_test.py`, and avoids common false positives (`B101`).

## Cómo ejecutar localmente / How to run locally
Requiere Python 3.10+ y Poetry. 
Requires Python 3.10+ and Poetry.

```bash
poetry install --with dev
```

### Lint / Lint
```bash
make lint
```

### Tests + Coverage / Pruebas + Cobertura
```bash
make test
poetry run pytest --cov=centinel --cov-report=xml --cov-report=term-missing
```

### Bandit / Bandit
```bash
poetry run bandit -r src -c pyproject.toml
```

### Chaos (ligero) / Chaos (light)
```bash
poetry run python scripts/chaos_test.py --config chaos_config.yaml.example --level low --duration-minutes 0.1
```

## Troubleshooting / Resolución de problemas
### Poetry lock / poetry.lock
Si el CI falla por dependencias, actualiza el lockfile con: 
If CI fails due to dependencies, update the lockfile with:

```bash
poetry lock --no-update
```

### Pytest discovery / Descubrimiento de pytest
Si `pytest` no encuentra módulos, verifica que `PYTHONPATH=src` y `--import-mode=importlib` estén activos. 
If `pytest` does not find modules, ensure `PYTHONPATH=src` and `--import-mode=importlib` are active.

### Bandit falsos positivos / Bandit false positives
Bandit puede reportar `B101` (asserts) en tests o utilidades. Esto se excluye para evitar ruido, pero se recomienda revisar cualquier reporte nuevo. 
Bandit may report `B101` (asserts) in tests or utilities. This is excluded to avoid noise, but any new report should be reviewed.

## Políticas de contribución CI / CI contribution policy
- Mantener tests deterministas y reproducibles. 
  Keep tests deterministic and reproducible.
- Evitar dependencias de red en pruebas unitarias. 
  Avoid network dependencies in unit tests.
- Agregar cobertura cuando se añade lógica nueva. 
  Add coverage when new logic is introduced.
