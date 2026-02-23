# Governance Hardening Closure / Cierre de hardening de gobernanza

## Objetivo
Cerrar de forma verificable los pendientes de gobernanza reportados en `docs/governance.md` y dejar evidencia auditable por release.

## Pendientes heredados y estado

| Ítem | Estado | Evidencia mínima requerida |
|---|---|---|
| Regeneración/verificación de lockfile en entorno conectado | ✅ En seguimiento operativo con verificación CI activa | `poetry lock --check` o `poetry check --lock` + registro en release notes |
| Reserva formal del nombre de paquete en PyPI | ✅ Gobernanza documental cerrada con control operativo | registro de titularidad + referencia de cuenta custodio + fecha de renovación |

## Controles de cierre implementados

1. **Checklist por release**
   - `poetry check --lock` (o `poetry lock --check` cuando aplique)
   - `python scripts/release_gate.py --config config/prod/config.yaml --release-version <vX.Y.Z>`
   - Validación de SBOM: `sbom.<release_version>.cyclonedx.json`

2. **Evidencia mínima publicada por release**
   - Resultado del gate (PASS/FAIL) con timestamp UTC.
   - Huella SHA-256 del SBOM publicado.
   - Referencia del lockfile verificado.
   - Registro administrativo de custodia del namespace en PyPI.

3. **Cadencia de revisión**
   - Revisión mensual fuera de ventana electoral.
   - Revisión semanal en ventana electoral activa.

## Plantilla rápida de evidencia de cierre

```yaml
release_version: vX.Y.Z
verified_at_utc: "2026-02-15T18:30:00Z"
lockfile_check:
  command: "poetry check --lock"
  status: "pass"
release_gate:
  command: "python scripts/release_gate.py --config config/prod/config.yaml --release-version vX.Y.Z"
  status: "pass"
sbom:
  file: "sbom.vX.Y.Z.cyclonedx.json"
  sha256: "<sha256>"
pypi_namespace_custody:
  owner_account: "<org_or_user>"
  verified_at_utc: "<timestamp>"
  renewal_window_days: 90
```

## Nota operativa
Este documento cierra el pendiente de **gobernanza documental + disciplina de evidencia**. Las validaciones externas administrativas (como titularidad de cuenta) deben mantenerse en expediente operativo privado con hash público de constancia.
