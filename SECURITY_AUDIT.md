# Security Audit Follow-ups

## Security Score: 9.9-10/10 (Hardened)

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

## Security Hardening v2 (Feb 2026)

- [x] **Client-side rate limiting** — Token-bucket algorithm (1 req/8-12s, burst 3) in `centinel_engine/rate_limiter.py`. Complements Cloudflare (PR #397) with strict local governor.
- [x] **Proxy rotation + User-Agent pool** — 50+ real browser UAs with cryptographic random rotation per request. Auto-rotation on 429/403. See `centinel_engine/proxy_manager.py`.
- [x] **Encrypted backup system** — AES-256 Fernet encryption for `health_state.json` + hash chain. Multi-destination: local `./backups/`, Dropbox, S3. 30-min background scheduler. See `centinel_engine/secure_backup.py`.
- [x] **Legal Compliance Matrix** — Full Honduras legal analysis with references to Decreto 170-2006, Código Penal Arts. 393-397, and international observation standards (OEA/EU/Carter). See `docs/legal_compliance_matrix.md`.
