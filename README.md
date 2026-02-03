# C.E.N.T.I.N.E.L.
**Centinela Electrónico Neutral Transparente Íntegro Nacional Electoral Libre**
**Electronic Neutral Transparent Integral National Electoral Sentinel**

C.E.N.T.I.N.E.L. es un sistema técnico independiente para observar y auditar datos electorales públicos en Honduras, con evidencia reproducible y trazable.
C.E.N.T.I.N.E.L. is an independent technical system to observe and audit public electoral data in Honduras, producing reproducible, traceable evidence.
Opera de forma cívica, defensiva y no intrusiva, sin sustituir a autoridades ni interpretar resultados.
It operates in a civic, defensive, non-intrusive manner, without replacing authorities or interpreting outcomes.

**Estado actual / Current status:** **AUDIT ACTIVE**

![Licencia AGPL/MIT](https://img.shields.io/badge/license-AGPL%2FMIT-blue)
![Python](https://img.shields.io/badge/python-3.11%2B-informational)
![Último commit / Last commit](https://img.shields.io/badge/last%20commit-recent-brightgreen)

## Quick Start (4 comandos / 4 commands)
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
| [Reglas](docs/rules.md) | [Secrets/backup](docs/SECRETS_BACKUP.md) |

<details>
<summary><strong>Detalles operativos / Operational details</strong></summary>

- **Legalidad y límites**: acceso a datos públicos, sin datos personales, sin interferencia. / public data only, no personal data, no interference. Ver /docs/manual.md y /docs/operating_principles.md.
- **Flujo operativo**: captura → hashing encadenado → normalización → reglas → reportes reproducibles. / capture → chained hashing → normalization → rules → reproducible reports. Ver /docs/methodology.md.
- **Control centralizado**: toda configuración editable está en `command_center/` para evitar ambigüedad. / all editable configuration lives in `command_center/` to avoid ambiguity.
- **Cadencia**: mantenimiento mensual, monitoreo 24–72h, elección activa 5–15 min. / monthly maintenance, 24–72h monitoring, 5–15 min active election. Ver /docs/manual.md.
- **Arbitrum (opcional)**: anclaje L2 para sellar integridad de snapshots. / optional L2 anchoring for snapshot integrity. Ver /docs/ANCHOR_SETUP_GUIDE.md.
</details>

## Disclaimer / Descargo
Este repositorio procesa únicamente datos públicos publicados por el CNE y otras fuentes oficiales; documenta hechos técnicos verificables (hashes, diffs, metadatos) sin interpretación política ni partidaria.
This repository processes only public data published by the CNE and other official sources; it documents verifiable technical facts (hashes, diffs, metadata) without political or partisan interpretation.
