# Security / Seguridad

## Current posture / Postura actual

Centinel opera con enfoque de hardening progresivo y mínimo privilegio.
Centinel operates with progressive hardening and least-privilege principles.

### Zero-trust (partial)
- Validación explícita de configuración crítica.
- Separación de configuración (`config/prod`, `config/dev`, `config/secrets`).
- Controles de cadencia y rotación para reducir superficie operacional.

### Integrity controls
- SHA-256 encadenado para snapshots y continuidad de custodia técnica.
- Backups cifrados para estado crítico y artefactos de hash.

### Defensive optional components
- Honeypot y alertas avanzadas existen como controles desactivables.
- Se recomienda mantenerlos desactivados por defecto fuera de escenarios específicos.

## Security baseline

- No exposición de secretos en repositorio.
- Trazabilidad de eventos relevantes en logs.
- Cumplimiento legal/ético como restricción de diseño, no como accesorio.
