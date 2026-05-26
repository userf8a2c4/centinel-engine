# Release Checklist (Mandatory Gate)

## Español
1. Lockfile íntegro:
   - Ejecutar `poetry lock --check` (o fallback `poetry check --lock` según versión de Poetry).
2. SBOM versionado por release:
   - Generar `sbom.<release_version>.cyclonedx.json`.
3. Gate de gobernanza:
   - Ejecutar `scripts/release_gate.py` y exigir `release_gate=PASS`.
4. Publicación de artefactos:
   - Adjuntar SBOM versionado y `artifacts/release_gate_<release_version>.json`.

## English
1. Lockfile integrity:
   - Run `poetry lock --check` (or `poetry check --lock` fallback depending on Poetry version).
2. Release-versioned SBOM:
   - Generate `sbom.<release_version>.cyclonedx.json`.
3. Governance gate:
   - Run `scripts/release_gate.py` and require `release_gate=PASS`.
4. Artifact publication:
   - Attach the versioned SBOM and `artifacts/release_gate_<release_version>.json`.
