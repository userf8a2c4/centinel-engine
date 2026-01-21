# Contribuir a Sentinel

Gracias por tu interés en mejorar Sentinel. Este documento describe cómo proponer issues, mejoras y pull requests, además de reglas mínimas de calidad.

## Cómo proponer cambios
1. Abre un issue con el contexto y evidencia (capturas, datos, enlaces).
2. Crea una rama desde `dev-v4`.
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

## Preguntas
Si tienes dudas, abre un issue o contacta al equipo mantenedor.

---

# Contributing to Sentinel

Thanks for your interest in improving Sentinel. This document explains how to propose issues, improvements, and pull requests, plus minimum quality rules.

## How to propose changes
1. Open an issue with context and evidence (screenshots, data, links).
2. Create a branch from `dev-v4`.
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

## Questions
If you have questions, open an issue or contact the maintainers.
