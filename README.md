# Proyecto C.E.N.T.I.N.E.L. 

## Descripción breve
Es un sistema técnico independiente y open-source para observar y auditar datos electorales **públicos** en Honduras. Genera evidencia verificable (hashes, diffs, snapshots, metadatos) sin interpretar resultados ni sustituir a ninguna autoridad. Opera de forma cívica, defensiva y no intrusiva.

## Características principales
- Evidencia técnica reproducible con hashes y snapshots encadenados.
- Trazabilidad histórica para comparar cambios en datos públicos.
- Reglas de análisis configurables para detectar eventos anómalos.
- Operación neutral, cívica y no intrusiva.
- Configuración centralizada en [`command_center/`](command_center/).

## Estado actual del proyecto
**En desarrollo**.

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

<details>
<summary><strong>Detalles operativos / Operational details</strong></summary>

- **Legalidad y límites**: acceso a datos públicos, sin datos personales, sin interferencia. Ver [manual](docs/manual.md) y [principios operativos](docs/operating_principles.md).
- **Flujo operativo**: captura → hashing encadenado → normalización → reglas → reportes reproducibles. Ver Ver [metodología](docs/methodology.md) .
- **Control centralizado**: toda configuración editable está en `command_center/` para evitar ambigüedad.
- **Cadencia**: mantenimiento mensual, monitoreo 24–72h, elección activa 5–15 min. Ver [manual](docs/manual.md).
- **Arbitrum (opcional)**: anclaje L2 para sellar integridad de snapshots. Ver [guía de anclaje](docs/ANCHOR_SETUP_GUIDE.md).
</details>

## Disclaimer / Descargo
- Este repositorio procesa únicamente datos públicos publicados por el CNE y otras fuentes oficiales; documenta hechos técnicos verificables (hashes, diffs, metadatos) sin interpretación política ni partidaria.
