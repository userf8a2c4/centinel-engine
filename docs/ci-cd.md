# CI/CD (Bilingüe / Bilingual)

## Objetivo / Objective
Este documento describe el CI para C.E.N.T.I.N.E.L., con foco en reproducibilidad, trazabilidad y confiabilidad frente a auditorías externas (matemáticos, ingenieros, OEA, Carter Center). Cada workflow separa responsabilidades y reporta resultados claros. 
This document describes the CI for C.E.N.T.I.N.E.L., focused on reproducibility, traceability, and reliability for external audits (mathematicians, engineers, OEA, Carter Center). Each workflow separates responsibilities and reports clear results.

## Resumen de workflows / Workflow summary
- **Lint (push)**: `flake8` de errores críticos (`E9,F63,F7,F82`) para feedback rápido y determinista.
  **Lint (push)**: critical-error `flake8` (`E9,F63,F7,F82`) for fast deterministic feedback.
- **CI (push/pull_request)**: jobs `Lint` + `Tests` (matriz Python 3.10–3.11) con foco en estabilidad operativa.
  **CI (push/pull_request)**: `Lint` + `Tests` jobs (Python 3.10–3.11 matrix) focused on operational stability.
- **Security (push/pull_request)**: `bandit` con exclusiones razonables para reducir falsos positivos. 
  **Security (push/pull_request)**: `bandit` with reasonable exclusions to reduce false positives.
- **Chaos (pull_request, opcional)**: ejecuta `scripts/chaos_test.py` en modo ligero. 
  **Chaos (pull_request, optional)**: runs `scripts/chaos_test.py` in light mode.

## Reproducibilidad y credibilidad / Reproducibility and credibility
- Se fija la matriz de versiones de Python y se usa instalación mínima de dependencias por job para reducir superficie de fallo en CI.
  Python versions are pinned in a matrix and each job installs a minimal dependency set to reduce CI failure surface.
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
python -m flake8 . --select=E9,F63,F7,F82 --show-source --statistics
```

### Tests / Pruebas
```bash
make test
poetry run pytest -q tests/test_hashchain.py tests/test_turnout_impossible_rule.py
```

### Bandit / Bandit
```bash
poetry run bandit -r src -c pyproject.toml
```

## Buenas prácticas para contribuir / Contribution guidelines
- Mantener pruebas deterministas en `tests/`.
- Evitar dependencias de red en unit tests.
- Si agregas nueva lógica, añade cobertura y actualiza este documento si cambias CI.
