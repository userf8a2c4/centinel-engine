# C.E.N.T.I.N.E.L.
**Centinela Electrónico Neutral Transparente Íntegro Nacional Electoral Libre**
**Electronic Neutral Transparent Integral National Electoral Sentinel**

C.E.N.T.I.N.E.L. es un sistema técnico independiente para observar y auditar datos electorales públicos en Honduras, con evidencia reproducible y trazable.
C.E.N.T.I.N.E.L. is an independent technical system to observe and audit public electoral data in Honduras, producing reproducible, traceable evidence.
Opera de forma cívica, defensiva y no intrusiva, sin sustituir a autoridades ni interpretar resultados.
It operates in a civic, defensive, non-intrusive manner, without replacing authorities or interpreting outcomes.

**Estado actual / Current status:** **AUDIT ACTIVE**

![Licencia MIT](https://img.shields.io/github/license/userf8a2c4/centinel-engine)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Último commit / Last commit](https://img.shields.io/github/last-commit/userf8a2c4/centinel-engine)

## Quick Start (4 comandos / 4 commands)
```bash
poetry install
poetry run python scripts/bootstrap.py
poetry run python scripts/run_pipeline.py --once
make pipeline
```

## Enlaces clave / Key links
- **[`/docs/README.md`](docs/README.md)** — índice completo de documentación. / documentation index.
- **[`/docs/manual.md`](docs/manual.md)** — operación, límites legales, cadencia recomendada. / operations, legal boundaries, recommended cadence.
- **[`/docs/methodology.md`](docs/methodology.md)** — metodología de auditoría y reglas. / audit methodology and rules.
- **[`/docs/architecture.md`](docs/architecture.md)** — arquitectura técnica. / technical architecture.
- **[`/docs/operating_principles.md`](docs/operating_principles.md)** — principios de neutralidad y alcance. / neutrality and scope principles.
- **[`/docs/ANCHOR_SETUP_GUIDE.md`](docs/ANCHOR_SETUP_GUIDE.md)** — anclaje opcional en Arbitrum L2. / optional Arbitrum L2 anchoring.
- **[`/docs/SECRETS_BACKUP.md`](docs/SECRETS_BACKUP.md)** — respaldo y resguardo de secretos. / secrets backup.
- **[`/command_center/`](command_center/)** — fuente de verdad operativa. / single operational source of truth.
- **[`/docs/security.md`](docs/security.md)** — seguridad y disclosure. / security and disclosure.
- **[`/docs/quickstart.md`](docs/quickstart.md)** — guía ampliada. / extended quick start.
- **[`/docs/contributing.md`](docs/contributing.md)** — contribución. / contributing.
- **[`/docs/roadmap.md`](docs/roadmap.md)** — roadmap técnico. / technical roadmap.
- **[`/LICENSE`](LICENSE)** — licencia del proyecto. / project license.

<details>
<summary><strong>Detalles operativos / Operational details</strong></summary>

- **Legalidad y límites**: acceso a datos públicos, sin datos personales, sin interferencia. / public data only, no personal data, no interference. Ver [`/docs/manual.md`](docs/manual.md) y [`/docs/operating_principles.md`](docs/operating_principles.md).
- **Flujo operativo**: captura → hashing encadenado → normalización → reglas → reportes reproducibles. / capture → chained hashing → normalization → rules → reproducible reports. Ver [`/docs/methodology.md`](docs/methodology.md).
- **Control centralizado**: toda configuración editable está en [`/command_center/`](command_center/) para evitar ambigüedad. / all editable configuration lives in [`/command_center/`](command_center/) to avoid ambiguity.
- **Cadencia**: mantenimiento mensual, monitoreo 24–72h, elección activa 5–15 min. / monthly maintenance, 24–72h monitoring, 5–15 min active election. Ver [`/docs/manual.md`](docs/manual.md).
- **Arbitrum (opcional)**: anclaje L2 para sellar integridad de snapshots. / optional L2 anchoring for snapshot integrity. Ver [`/docs/ANCHOR_SETUP_GUIDE.md`](docs/ANCHOR_SETUP_GUIDE.md).
</details>

## Disclaimer / Descargo
Este repositorio procesa únicamente datos públicos publicados por el CNE y otras fuentes oficiales; documenta hechos técnicos verificables (hashes, diffs, metadatos) sin interpretación política ni partidaria.
This repository processes only public data published by the CNE and other official sources; it documents verifiable technical facts (hashes, diffs, metadata) without political or partisan interpretation.
