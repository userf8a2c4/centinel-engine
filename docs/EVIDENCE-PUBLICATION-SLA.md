# SLA de Publicación de Evidencia y Cadena de Custodia

## Propósito
Definir compromisos operativos medibles para publicar evidencia técnica por corrida y preservar custodia verificable a lo largo del tiempo.

## Alcance
Aplica a cada corrida que genere como mínimo:
- snapshot
- hash record
- reglas activas por versión
- verification bundle
- reporte técnico resumido

## SLA de publicación

| Nivel | Compromiso |
|---|---|
| Publicación de evidencia primaria | <= 30 minutos tras cierre de corrida |
| Publicación de bundle/verificación | <= 45 minutos tras cierre de corrida |
| Publicación de resumen ejecutivo | <= 2 horas tras cierre de corrida |
| Corrección de artefacto defectuoso detectado | <= 4 horas desde detección |

## Retención mínima e inmutabilidad

| Tipo de artefacto | Retención mínima | Requisito de inmutabilidad |
|---|---|---|
| Snapshots y hash records | 24 meses | Almacenamiento append-only o versión inmutable |
| Verification bundles | 24 meses | Hash publicado y verificable públicamente |
| Reportes técnicos | 24 meses | Versión fechada + huella SHA-256 |
| Logs de publicación y custodia | 36 meses | Trazabilidad de actor, timestamp y checksum |

## Manifiesto de publicación por corrida (obligatorio)

```json
{
  "schema_version": "1.0",
  "run_id": "2026-02-15T18-00-00Z",
  "published_at_utc": "2026-02-15T18:21:03Z",
  "artifacts": [
    {"type": "snapshot", "path": "data/snapshots/snapshot_...json", "sha256": "..."},
    {"type": "hash_record", "path": "hashes/snapshot_....sha256", "sha256": "..."},
    {"type": "bundle", "path": "artifacts/evidence_bundle.json", "sha256": "..."},
    {"type": "report", "path": "artifacts/report_...json", "sha256": "..."}
  ],
  "sla": {
    "primary_publication_minutes": 30,
    "bundle_publication_minutes": 45,
    "executive_summary_minutes": 120
  }
}
```

## Reglas de custodia
1. Cada artefacto debe tener checksum SHA-256 publicado.
2. Cualquier corrección posterior se publica como **nueva versión**, nunca reemplazo silencioso.
3. Todo evento de publicación/corrección debe incluir `timestamp_utc`, `actor`, `reason`, `old_sha256`, `new_sha256`.
4. En incidentes, preservar snapshot original y adjuntar bitácora de remediación.

## Indicadores de cumplimiento del SLA
- `% de corridas con publicación primaria <= 30 min`.
- `% de corridas con bundle <= 45 min`.
- `% de corridas con resumen <= 2 h`.
- `# correcciones fuera de SLA`.

Estos indicadores deben exponerse en el reporte institucional de transparencia por release.
