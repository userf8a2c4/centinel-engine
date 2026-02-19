# Verification Bundle / Bundle de Verificación

## Objetivo
Estandarizar un artefacto reproducible para terceros: manifiesto SHA-256 por archivo + Merkle root del lote.

## Flujo rápido

```bash
python scripts/evidence_bundle.py --input-dir data/snapshots --output artifacts/evidence_bundle.json
python scripts/verify_evidence_bundle.py --bundle artifacts/evidence_bundle.json --base-dir data/snapshots
```

## Qué contiene el bundle
- `schema_version`
- `created_at_utc`
- `file_count`
- `files[]` con `{path, sha256}`
- `merkle_root_sha256`

## Criterio de verificación
- PASS: todos los hashes por archivo y Merkle root coinciden.
- FAIL: cualquier archivo faltante, hash distinto o Merkle root distinto.

## Uso recomendado
- Publicar el bundle junto con reportes y versión del pipeline.
- Conservar bundle por corrida para auditoría externa y reproducibilidad histórica.


## Verificación externa 1-click (snapshot + hash + reglas + versión)

```bash
python scripts/verify_snapshot_bundle.py   --snapshot data/snapshot_2026-01-06_21-40-17.json   --hash-record hashes/snapshot_2026-01-06_21-40-17.sha256   --rules command_center/rules.yaml   --pipeline-version v1.0.0
```

Salida determinista:
- `verification=PASS` si snapshot, hashchain, reglas habilitadas y versión son consistentes.
- `verification=FAIL` + códigos de error si hay desajustes.

## Checklist corto de replicación (periodistas/académicos)
1. Descargar snapshot, hash record, reglas y reporte de la misma corrida.
2. Verificar checksum local del snapshot (`sha256sum`).
3. Ejecutar `verify_snapshot_bundle.py` con los 4 artefactos.
4. Confirmar `verification=PASS`.
5. Registrar versión de pipeline y fecha UTC en nota metodológica.
