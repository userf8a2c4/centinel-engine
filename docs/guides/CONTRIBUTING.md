# Contributing | Contribuir a C.E.N.T.I.N.E.L.

**Version:** 1.1 | **Date:** 2026-05-18 | **Status:** Active

Gracias por tu interés en mejorar C.E.N.T.I.N.E.L. Este documento describe cómo proponer issues, mejoras y pull requests, además de reglas mínimas de calidad.

## Cómo proponer cambios
1. Abre un issue con el contexto y evidencia (capturas, datos, enlaces).
2. Crea una rama desde `main`.
3. Realiza cambios pequeños y revisables.
4. Documenta la motivación en el PR.

## Estándares de calidad
- Código Python formateado con **Black**.
- Lint con **Ruff**.
- Tipado con **Mypy** (cuando aplique).
- Tests con **Pytest** con cobertura razonable.
- Documentación y comentarios bilingües (español primero, luego inglés).

## Cómo correr checks localmente
```bash
poetry install
poetry run ruff check .
poetry run black --check .
poetry run mypy .
poetry run pytest --cov=src/centinel --cov-report=term-missing
```

## Estilo de commits
- Usa mensajes claros en presente ("Add", "Fix", "Improve").
- Relaciona el commit con el issue cuando exista.

## Seguridad y datos sensibles
- **Nunca** subas tokens o claves privadas.
- Usa `.env` para credenciales locales.

## Añadir una nueva regla detectora

1. Crear `src/centinel/core/rules/mi_regla_rule.py`
2. Decorar con `@rule(name=..., severity=..., config_key=..., description=...)`
3. Añadir `config_key` a `command_center/rules.yaml` con umbrales
4. Añadir tests en `tests/test_mi_regla.py`
5. Documentar en `docs/RULES.md` (tabla + sección descriptiva)

## Preguntas
Si tienes dudas, abre un issue o contacta al equipo mantenedor.

---

# Contributing to C.E.N.T.I.N.E.L.

Thanks for your interest in improving C.E.N.T.I.N.E.L. This document explains how to propose issues, improvements, and pull requests, plus minimum quality rules.

## How to propose changes
1. Open an issue with context and evidence (screenshots, data, links).
2. Create a branch from `main`.
3. Make small, reviewable changes.
4. Document motivation in the PR.

## Quality standards
- Python code formatted with **Black**.
- Lint with **Ruff**.
- Type checks with **Mypy** (when applicable).
- Tests with **Pytest** and reasonable coverage.
- Bilingual documentation and comments (Spanish first, then English).

## Run checks locally
```bash
poetry install
poetry run ruff check .
poetry run black --check .
poetry run mypy .
poetry run pytest --cov=src/centinel --cov-report=term-missing
```

## Commit style
- Use clear present-tense messages ("Add", "Fix", "Improve").
- Link commits to issues when applicable.

## Security and sensitive data
- **Never** commit tokens or private keys.
- Use `.env` for local credentials.

## Adding a new detection rule

1. Create `src/centinel/core/rules/my_rule_rule.py`
2. Decorate with `@rule(name=..., severity=..., config_key=..., description=...)`
3. Add `config_key` to `command_center/rules.yaml` with thresholds
4. Add tests in `tests/test_my_rule.py`
5. Document in `docs/RULES.md` (table row + description section)

## Architecture for contributors

```
Pipeline flow:  download → hash → normalize → rules_engine → anchor → report
Key files:
  scripts/run_pipeline.py      — orchestrator, entry point
  src/centinel/core/rules/     — add new detectors here
  command_center/rules.yaml    — tune thresholds here (no redeployment needed)
  src/centinel/api/main.py     — FastAPI public API
```

## Questions
If you have questions, open an issue or contact the maintainers.
