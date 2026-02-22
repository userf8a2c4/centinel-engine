# Proyecto C.E.N.T.I.N.E.L. / C.E.N.T.I.N.E.L. Project

[Quick Start](#quick-start) • [Documentación completa / Full docs](/docs/README.md) • [Metodología / Methodology](/docs/methodology.md) • [Contribuir / Contributing](/docs/contributing.md) • [Licencia / License](/LICENSE)

[![Licencia: AGPL v3](https://img.shields.io/badge/Licencia-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue)](https://www.python.org/)
[![Último commit](https://img.shields.io/github/last-commit/userf8a2c4/centinel-engine/main)](https://github.com/userf8a2c4/centinel-engine/commits/main)
[![CI](https://github.com/userf8a2c4/centinel-engine/actions/workflows/ci.yml/badge.svg)](https://github.com/userf8a2c4/centinel-engine/actions/workflows/ci.yml)
[![CodeQL](https://github.com/userf8a2c4/centinel-engine/actions/workflows/codeql.yml/badge.svg)](https://github.com/userf8a2c4/centinel-engine/actions/workflows/codeql.yml)
[![Deploy Dashboard](https://github.com/userf8a2c4/centinel-engine/actions/workflows/deploy-dashboard.yml/badge.svg)](https://github.com/userf8a2c4/centinel-engine/actions/workflows/deploy-dashboard.yml)

## Español

Sistema técnico open-source para observar y auditar datos electorales **públicos** en Honduras. Genera evidencia verificable (hashes, diffs, snapshots, metadatos) sin interpretación política ni sustitución de autoridades.

### Características
- Cadena de evidencia reproducible con hashing SHA-256 encadenado.
- Reglas de análisis configurables y trazabilidad histórica por cambios.
- Organización de datos scrapeados por departamento y fuente.
- Homeostasis operativa (vital signs) para ajustar cadencia de scraping dentro de límites éticos.
- Endurecimiento de seguridad con controles de enfoque zero-trust en producción.
- Configuración centralizada en [`command_center/`](/command_center/) y dashboard de demostración en [Streamlit](https://centinel-dashboard.streamlit.app/).

### Estado
**AUDIT ACTIVE** · Desarrollo activo · Cadencia objetivo de polling electoral: 5 minutos.

## English

Open-source technical system to monitor and audit **public** election data in Honduras. It produces verifiable evidence (hashes, diffs, snapshots, metadata) without political interpretation and without replacing official authorities.

### Features
- Reproducible evidence chain with linked SHA-256 hashing.
- Configurable anomaly rules and historical change traceability.
- Scraped data organization by department and source.
- Operational homeostasis (vital signs) to adapt scrape cadence within ethical bounds.
- Security hardening with production-focused zero-trust controls.
- Centralized configuration in [`command_center/`](/command_center/) plus a demo [Streamlit dashboard](https://centinel-dashboard.streamlit.app/).

### Status
**AUDIT ACTIVE** · Actively developed · Election polling target cadence: every 5 minutes.

## Quick Start

```bash
poetry install
poetry run python scripts/bootstrap.py
poetry run python scripts/run_pipeline.py --once
make pipeline
```

## Enlaces importantes / Key docs

| Documentación / Documentation | Operación y seguridad / Operations & security |
| --- | --- |
| [Índice de documentación](docs/README.md) | [Manual de operación](docs/manual.md) |
| [Arquitectura](docs/architecture.md) | [Operational flow and cadence](docs/OPERATIONAL-FLOW-AND-CADENCE.md) |
| [Metodología](docs/methodology.md) | [Límites legales y operativos](docs/LEGAL-AND-OPERATIONAL-BOUNDARIES.md) |
| [Principios operativos](docs/operating_principles.md) | [Seguridad](docs/security.md) |
| [Reglas](docs/rules.md) | [Secretos y respaldos](docs/SECRETS_BACKUP.md) |
| [Resiliencia (configs)](docs/resilience.md) | [Circuit breaker y low-profile](docs/resilience.md#circuit-breaker-y-low-profile) |

## Cumplimiento Legal – Feb 2026 / Legal Compliance – Feb 2026

Centinel opera exclusivamente sobre datos publicos del CNE conforme a la **Ley de Transparencia y Acceso a la Informacion Publica (Decreto 170-2006)**. No procesa datos personales de votantes. Incluye rate-limiting etico agresivo, pausas reactivas ante errores del servidor, y hashing encadenado SHA-256 para integridad y no repudio.

Centinel operates exclusively on public CNE data pursuant to the **Transparency and Access to Public Information Act (Decree 170-2006)**. It does not process personal voter data. It includes aggressive ethical rate-limiting, reactive pauses on server errors, and chained SHA-256 hashing for integrity and non-repudiation.

Para detalles completos, ver la **[Matriz de Cumplimiento Legal / Legal Compliance Matrix](docs/legal_compliance_matrix.md)**.

## Descargo / Disclaimer

Datos solo de fuentes publicas CNE, conforme Ley de Transparencia 170-2006. Agnostico politico. Sin interpretacion partidaria.

Data only from public CNE sources, pursuant to Transparency Law 170-2006. Politically agnostic. No partisan interpretation.
