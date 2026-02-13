# Proyecto C.E.N.T.I.N.E.L.

[Quick Start](#quick-start) • [Documentación completa](/docs/README.md) • [Metodología](/docs/methodology.md) • [Contribuir](/docs/contributing.md) • [Licencia](/LICENSE)

[![Licencia: AGPL v3](https://img.shields.io/badge/Licencia-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue)](https://www.python.org/)
[![Último commit](https://img.shields.io/github/last-commit/userf8a2c4/centinel-engine/main)](https://github.com/userf8a2c4/centinel-engine/commits/main)
[![CI](https://github.com/userf8a2c4/centinel-engine/actions/workflows/ci.yml/badge.svg)](https://github.com/userf8a2c4/centinel-engine/actions/workflows/ci.yml)
[![CodeQL](https://github.com/userf8a2c4/centinel-engine/actions/workflows/codeql.yml/badge.svg)](https://github.com/userf8a2c4/centinel-engine/actions/workflows/codeql.yml)
[![Deploy Dashboard](https://github.com/userf8a2c4/centinel-engine/actions/workflows/deploy-dashboard.yml/badge.svg)](https://github.com/userf8a2c4/centinel-engine/actions/workflows/deploy-dashboard.yml)

## Descripción breve

Es un sistema técnico independiente y open-source para observar y auditar datos electorales **públicos** en Honduras. Genera evidencia verificable (hashes, diffs, snapshots, metadatos) sin interpretar resultados ni sustituir a ninguna autoridad. Opera de forma cívica, defensiva y no intrusiva.

## Características principales

- Evidencia técnica reproducible con hashes y snapshots encadenados.
- Trazabilidad histórica para comparar cambios en datos públicos.
- Reglas de análisis configurables para detectar eventos anómalos.
- Operación neutral, cívica y no intrusiva.
- Configuración centralizada en [`command_center/`](/command_center/).
- Dashboard de demostracion en [Streamlit](https://centinel-dashboard.streamlit.app/)

## Estado actual del proyecto

**AUDIT ACTIVE** | En desarrollo activo | Preparado para polling cada 5 minutos en período electoral | Snapshots con hashing SHA-256 encadenado.

## Quick Start

```bash
poetry install
poetry run python scripts/bootstrap.py
poetry run python scripts/run_pipeline.py --once
make pipeline
```

## Enlaces importantes / Documentación

| Documentación | Operación y seguridad |
| --- | --- |
| [Índice de documentación](docs/README.md) | [Manual de operación](docs/manual.md) |
| [Arquitectura](docs/architecture.md) | [Flujo operativo y cadencia](docs/OPERATIONAL-FLOW-AND-CADENCE.md) |
| [Metodología](docs/methodology.md) | [Límites legales y operativos](docs/LEGAL-AND-OPERATIONAL-BOUNDARIES.md) |
| [Principios operativos](docs/operating_principles.md) | [Seguridad](docs/security.md) |
| [Reglas](docs/rules.md) | [Secretos y respaldos](docs/SECRETS_BACKUP.md) |
| [Resiliencia operativa y tolerancia a fallos (configs)](docs/resilience.md) | [Circuit breaker y low-profile](docs/resilience.md#circuit-breaker-y-low-profile) |

<details>
<summary><strong>Detalles operativos</strong></summary>

- **Legalidad y límites**: acceso a datos públicos, sin datos personales, sin interferencia. Ver [manual](docs/manual.md) y [principios operativos](docs/operating_principles.md).
- **Flujo operativo**: captura → hashing encadenado → normalización → reglas → reportes reproducibles. Ver Ver [metodología](docs/methodology.md) .
- **Control centralizado**: toda configuración editable está en [`command_center/`](/command_center/) para evitar ambigüedad.
- **Cadencia**: mantenimiento mensual, monitoreo 24–72h, elección activa 5–15 min. Ver [manual](docs/manual.md).
- **Arbitrum (opcional)**: anclaje L2 para sellar integridad de snapshots. Ver [guía de anclaje](docs/ANCHOR_SETUP_GUIDE.md).
</details>

## Descargo
- Este repositorio procesa únicamente datos públicos publicados por el CNE y otras fuentes oficiales; documenta hechos técnicos verificables (hashes, diffs, metadatos) sin interpretación política ni partidaria.

## CI Fixes / Correcciones de CI

### [EN]
Recent hardening addresses `exit code 1` failures in collector/audit jobs:
- Added resilient collector (`scripts/collector.py`) with retry policy, HTTP/JSON exception handling, and schema validation for expected 96 JSON snapshots.
- Added robust hash snapshot module (`scripts/hash.py`) and unified pipeline entrypoint (`scripts/snapshot.py`) with timestamped chained records.
- Added workflow diagnostics and Poetry cache in `.github/workflows/pipeline.yml` to improve reliability and debugging speed.
- Added `make collect` and `make audit` targets with log capture (`tee`) for local reproducibility.

### [ES]
Se endureció el pipeline para resolver fallos `exit code 1` en jobs de collector/audit:
- Se agregó colector resiliente (`scripts/collector.py`) con política de reintentos, manejo de excepciones HTTP/JSON y validación de esquema para 96 snapshots esperados.
- Se agregó módulo robusto de hash (`scripts/hash.py`) y un entrypoint unificado (`scripts/snapshot.py`) con registros encadenados y timestamp.
- Se agregaron diagnósticos en workflow y cache de Poetry en `.github/workflows/pipeline.yml` para mejorar confiabilidad y velocidad de depuración.
- Se añadieron targets `make collect` y `make audit` con captura de logs (`tee`) para reproducibilidad local.
