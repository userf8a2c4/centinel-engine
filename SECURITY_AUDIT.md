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

---

## Hardening de Seguridad – Feb 2026 / Security Hardening – Feb 2026

### Nuevos modulos implementados / New modules implemented

- [x] **Config refactor**: Configuraciones movidas de raiz a `config/prod/`, `config/dev/`, `config/secrets/` (gitignored). Cargador centralizado en `centinel_engine/config_loader.py`.
- [x] **Rate-limiting etico agresivo**: `centinel_engine/rate_limiter.py` — Token bucket (capacidad=3, 1 token/10s, minimo 8s). Integrado antes de cada request al CNE.
- [x] **Rotacion de proxies + User-Agent pool (50+)**: `centinel_engine/proxy_manager.py` — Rotacion cada 15 requests o ante 429/403/5xx. Pool de 50+ UAs reales.
- [x] **Backup cifrado multi-destino**: `centinel_engine/secure_backup.py` — AES-256 Fernet. Destinos: local (`backups/encrypted/`), Dropbox, S3 (stub). Cada 30 min o post-scrape exitoso. Nunca interrumpe pipeline principal.
- [x] **Matriz de cumplimiento legal**: `docs/legal_compliance_matrix.md` — Decreto 170-2006, agnosticismo politico, ausencia ley datos personales (feb 2026), controles tecnicos.
- [x] **Tests de escenario hostil**: `tests/test_hostile_scenarios.py` — 50x 429 consecutivos, hash chain rota, pool vacio, bursts bloqueados.
- [x] **Integracion en pipeline**: `scripts/run_pipeline.py` actualizado con rate_limiter.wait() + proxy/UA antes de scrape, backup_critical() post-scrape exitoso.

### Cumplimiento Legal / Legal Compliance

Ver **[Matriz de Cumplimiento Legal](docs/legal_compliance_matrix.md)** para detalles completos sobre:
- Acceso a datos publicos agregados (Decreto 170-2006, Art. 3, 4, 13)
- Ausencia de Ley de Proteccion de Datos Personales vigente (anteproyecto feb 2026)
- Rate-limits eticos + pausas reactivas
- Zero-trust, hashing encadenado, Cloudflare, homeostasis
- Agnosticismo politico absoluto
