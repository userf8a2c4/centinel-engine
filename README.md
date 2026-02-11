# Proyecto C.E.N.T.I.N.E.L.

[Quick Start](#quick-start) • [Documentación completa](/docs/README.md) • [Metodología](/docs/methodology.md) • [Contribuir](/docs/contributing.md) • [Licencia](/LICENSE)

[![Licencia: AGPL v3](https://img.shields.io/badge/Licencia-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue)](https://www.python.org/)
[![Último commit](https://img.shields.io/github/last-commit/userf8a2c4/centinel-engine/dev-v6)](https://github.com/userf8a2c4/centinel-engine/commits/dev-v6)
[![Lint](https://github.com/userf8a2c4/centinel-engine/actions/workflows/lint.yml/badge.svg?branch=dev-v6)](https://github.com/userf8a2c4/centinel-engine/actions/workflows/lint.yml)
[![Tests](https://github.com/userf8a2c4/centinel-engine/actions/workflows/test.yml/badge.svg?branch=dev-v6)](https://github.com/userf8a2c4/centinel-engine/actions/workflows/test.yml)
[![Security](https://github.com/userf8a2c4/centinel-engine/actions/workflows/security.yml/badge.svg?branch=dev-v6)](https://github.com/userf8a2c4/centinel-engine/actions/workflows/security.yml)

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
