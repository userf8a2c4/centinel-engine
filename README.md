# Proyecto C.E.N.T.I.N.E.L. / C.E.N.T.I.N.E.L. Project

[Quick Start](#quick-start) • [Documentación completa / Full docs](/docs/README.md) • [Metodología / Methodology](/docs/methodology.md) • [Contribuir / Contributing](/docs/contributing.md) • [Licencia / License](/LICENSE)

[![Licencia: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
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
- Rate-limiting agresivo del lado cliente (token-bucket) + rotación de proxies y User-Agent pool (50+).
- Respaldo cifrado AES-256 automático a múltiples destinos (local, Dropbox, S3).
- [Matriz de cumplimiento legal](/docs/legal_compliance_matrix.md) con referencias a legislación hondureña vigente.
- Configuración centralizada en [`command_center/`](/command_center/) y dashboard de demostración en [Streamlit](https://centinel-dashboard.streamlit.app/).
- Validación metodológica continua con revisión externa de reglas matemáticas junto a especialistas de la UPNFM para elevar precisión analítica y respaldo académico.

### Estado
**EN DESARROLLO** · Preparación operativa continua · Cadencia objetivo de polling electoral: 5 minutos.

## English

Open-source technical system to monitor and audit **public** election data in Honduras. It produces verifiable evidence (hashes, diffs, snapshots, metadata) without political interpretation and without replacing official authorities.

### Features
- Reproducible evidence chain with linked SHA-256 hashing.
- Configurable anomaly rules and historical change traceability.
- Scraped data organization by department and source.
- Operational homeostasis (vital signs) to adapt scrape cadence within ethical bounds.
- Security hardening with production-focused zero-trust controls.
- Aggressive client-side rate limiting (token-bucket) + proxy rotation and User-Agent pool (50+).
- AES-256 encrypted automatic backup to multiple destinations (local, Dropbox, S3).
- [Legal compliance matrix](/docs/legal_compliance_matrix.md) with references to current Honduran legislation.
- Centralized configuration in [`command_center/`](/command_center/) plus a demo [Streamlit dashboard](https://centinel-dashboard.streamlit.app/).
- Ongoing methodological validation with external review of mathematical rules alongside UPNFM specialists to improve analytical precision and academic backing.

### Status
**IN DEVELOPMENT** · Continuous operational hardening · Election polling target cadence: every 5 minutes.

## Núcleo congelado (feb 2026) - Listo para revisión de 6 meses

**ES:** El núcleo queda congelado con flujo mínimo y verificable: **scrape → rate-limit → proxy/UA → hash → backup cifrado → reglas básicas**.

**EN:** The core is frozen with a minimal and verifiable flow: **scrape → rate-limit → proxy/UA → hash → encrypted backup → basic rules**.

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
| [Matriz legal / Legal matrix](docs/legal_compliance_matrix.md) | [Security audit](SECURITY_AUDIT.md) |

## Descargo / Disclaimer

Este repositorio procesa únicamente datos públicos del CNE y otras fuentes oficiales; documenta hechos técnicos verificables sin interpretación política ni partidaria.

This repository processes only public CNE and official-source data; it documents technically verifiable facts without political or partisan interpretation.

## Cumplimiento Legal – Feb 2026

- Matriz oficial: [docs/legal_compliance_matrix.md](docs/legal_compliance_matrix.md).
- Declaración obligatoria de reportes: **"Datos solo de fuentes públicas CNE, conforme Ley Transparencia 170-2006. Agnóstico político."**
