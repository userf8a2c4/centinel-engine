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
