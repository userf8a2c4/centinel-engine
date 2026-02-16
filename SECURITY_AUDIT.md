# Security Audit Follow-ups

## Estado de recomendaciones

- [x] Pinar GitHub Actions a SHA de commit (sin `@v4`/`@v5` flotante) en workflows.
- [ ] Regenerar `poetry.lock` con hashes de archivos.
  - Bloqueado temporalmente en este entorno por falta de conectividad a `pypi.org`.
  - Comando sugerido: `poetry lock --no-interaction`.
- [ ] Registrar `centinel` en PyPI para prevenir package squatting.
  - Acción operativa externa (requiere cuenta/propiedad en PyPI).
- [x] Warning en startup cuando Zero Trust está deshabilitado en producción.
- [x] Agregar `requirements.txt` al monitoreo de Dependabot.
- [x] Considerar generación de SBOM en CI.
  - Se agregó generación CycloneDX en workflow de CI.
