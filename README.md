# C.E.N.T.I.N.E.L. — auditoría cívica de datos electorales públicos

## Descripción breve (2–4 líneas)
C.E.N.T.I.N.E.L. es un sistema técnico independiente y open-source para observar y auditar datos electorales **públicos** en Honduras. Genera evidencia verificable (hashes, diffs, snapshots, metadatos) sin interpretar resultados ni sustituir a ninguna autoridad. Opera de forma cívica, defensiva y no intrusiva.

## ¿Qué es C.E.N.T.I.N.E.L.?
**C.E.N.T.I.N.E.L.** significa:
- **C** — Centinela / Centinela
- **E** — Electrónica / Electrónico
- **N** — Neutral
- **T** — Transparente
- **I** — Íntegro / Integral
- **N** — Nacional
- **E** — Electoral
- **L** — Libre

Versión expandida recomendada: **Centinela Electrónico Neutral Transparente Íntegro Nacional Electoral Libre**.

## Características principales
- Evidencia técnica reproducible con hashes y snapshots encadenados.
- Trazabilidad histórica para comparar cambios en datos públicos.
- Reglas de análisis configurables para detectar eventos anómalos.
- Operación neutral, cívica y no intrusiva.
- Configuración centralizada en [`command_center/`](command_center/).

## Estado actual del proyecto
**AUDIT ACTIVE**.

## Quick Start (4–6 comandos)
```bash
poetry install
poetry run python scripts/bootstrap.py
poetry run python scripts/run_pipeline.py --once
make pipeline
```

## Arquitectura y componentes clave
- Motor y orquestación en Python, con configuración en [`command_center/`](command_center/).
- Documentación técnica en [`/docs/README.md`](docs/README.md).
- Arquitectura: [`/docs/architecture.md`](docs/architecture.md).
- Metodología: [`/docs/methodology.md`](docs/methodology.md).
- Principios operativos: [`/docs/operating_principles.md`](docs/operating_principles.md).
- **Avanzado (opcional):** anclaje de integridad en Arbitrum L2 (ver [`/docs/ANCHOR_SETUP_GUIDE.md`](docs/ANCHOR_SETUP_GUIDE.md)).

## Seguridad y gestión de secretos
- Política de seguridad: [`/docs/security.md`](docs/security.md).
- Respaldo y manejo de secretos: [`/docs/SECRETS_BACKUP.md`](docs/SECRETS_BACKUP.md).
- Buenas prácticas y límites de operación en [`/docs/SECURITY-AND-SECRETS.md`](docs/SECURITY-AND-SECRETS.md).

## Cadencia operativa recomendada
- Mantenimiento/desarrollo: 1 vez al mes.
- Monitoreo normal: cada 24–72 horas.
- Elección activa: cada 5–15 minutos.

## Legalidad y límites
C.E.N.T.I.N.E.L. procesa únicamente datos **públicos** publicados por el CNE de Honduras y otras fuentes oficiales. No procesa datos personales, no interfiere con sistemas oficiales y no interpreta resultados ni emite juicios políticos. 
**Disclaimer:** este proyecto documenta evidencia técnica verificable, no conclusiones electorales.

## Enlaces importantes / Documentación

| Documentación | Operación y seguridad |
| --- | --- |
| [Índice de documentación](docs/README.md) | [Manual de operación](docs/manual.md) |
| [Arquitectura](docs/architecture.md) | [Flujo operativo y cadencia](docs/OPERATIONAL-FLOW-AND-CADENCE.md) |
| [Metodología](docs/methodology.md) | [Límites legales y operativos](docs/LEGAL-AND-OPERATIONAL-BOUNDARIES.md) |
| [Principios operativos](docs/operating_principles.md) | [Seguridad](docs/security.md) |
| [Reglas](docs/rules.md) | [Secrets/backup](docs/SECRETS_BACKUP.md) |

## Licencia
MIT — ver [`LICENSE`](LICENSE).

## Contribuir
Ver [`/docs/contributing.md`](docs/contributing.md).
