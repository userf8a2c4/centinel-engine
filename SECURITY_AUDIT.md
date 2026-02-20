# Security Audit Follow-ups

## Security Score: 9.9-10/10 (Hardened)

## Estado de recomendaciones

- [x] Pinar GitHub Actions a SHA de commit (sin `@v4`/`@v5` flotante) en workflows.
- [ ] Regenerar `poetry.lock` con hashes de archivos.
  - Pendiente operativo: ejecutar en entorno con conectividad a `pypi.org`.
  - Comando objetivo: `poetry lock --no-interaction`.
- [~] Mitigación de package squatting definida en gobernanza de releases.
  - Estado: política y checklist listos; la reserva efectiva en PyPI sigue siendo una acción operativa externa.
- [x] Warning en startup cuando Zero Trust está deshabilitado en producción.
- [x] Agregar `requirements.txt` al monitoreo de Dependabot.
- [x] Considerar generación de SBOM en CI.
  - Se agregó generación CycloneDX en workflow de CI.

## Security Hardening v2 (Feb 2026)

- [x] **Client-side rate limiting** — Token-bucket algorithm (1 req/8-12s, burst 3) in `centinel_engine/rate_limiter.py`. Complements Cloudflare (PR #397) with strict local governor.
- [x] **Proxy rotation + User-Agent pool** — 50+ real browser UAs with cryptographic random rotation per request. Auto-rotation on 429/403. See `centinel_engine/proxy_manager.py`.
- [x] **Encrypted backup system** — AES-256 Fernet encryption for `health_state.json` + hash chain. Multi-destination: local `./backups/`, Dropbox, S3. 30-min background scheduler. See `centinel_engine/secure_backup.py`.
- [x] **Legal Compliance Matrix** — Full Honduras legal analysis with references to Decreto 170-2006, Código Penal Arts. 393-397, and international observation standards (OEA/EU/Carter). See `docs/legal_compliance_matrix.md`.


## Governance baseline (Feb 2026)

- **Licensing consistency** aligned to AGPL-3.0 across repository metadata.
- **Release governance** requires lockfile integrity and signed release checklist.
- **Operational governance** keeps Arbitrum disabled by default outside electoral windows.

## Cumplimiento Legal – Feb 2026

- Matriz oficial: [docs/legal_compliance_matrix.md](docs/legal_compliance_matrix.md).
- Declaración obligatoria de reportes: **"Datos solo de fuentes públicas CNE, conforme Ley Transparencia 170-2006. Agnóstico político."**

## Matriz Red Team (core actual, sin Arbitrum/Telegram/Cloudflare)

> Alcance: componentes `core/*`, flujo de seguridad avanzada y collector/base runtime ya presentes en este repositorio.

| ID | Riesgo | Superficie | Probabilidad | Impacto | Severidad | Evidencia técnica | Escenario de abuso | Recomendación prioritaria |
|---|---|---|---|---|---|---|---|---|
| RT-01 | SSRF por webhooks/config sin allowlist fuerte | Alertas webhook/SMS y resumen externo | Media | Alta | **Alta** | Envíos HTTP a URLs de env/config sin validación de destino (host/IP privada). | Atacante con control de env/config redirige alertas a endpoint interno (`169.254.169.254`, servicios internos) para exfiltrar metadata o pivot interno. | Implementar validación estricta de URL: esquema `https`, bloqueo IP privadas/loopback/link-local, allowlist de dominios y resolución DNS segura antes de cada POST. |
| RT-02 | “Cifrado” degradado silenciosamente a texto plano | Honeypot event logs | Media | Alta | **Alta** | Fallback `Fernet.encrypt()` devuelve bytes sin cifrar cuando falta dependencia. | Operación cree tener logs cifrados; en incidente, los archivos contienen PII/IOC en claro. | Fallar en cerrado: si `honeypot_encrypt_events=true` y no hay cifrado real, abortar arranque y alertar crítico. |
| RT-03 | Path traversal en carga de config por `env` | Config loader | Media | Media/Alta | **Media-Alta** | `Path("config") / env / file_name` sin normalización ni confinamiento a raíz. | Si `env` viene de input controlable, lectura de YAML fuera de `config/` usando `../`. | Canonicalizar con `resolve()`, verificar prefijo de raíz permitida y rechazar separadores/`..` en `env`. |
| RT-04 | Exfiltración accidental de secretos en logs forenses | Attack/honeypot logs | Alta | Media/Alta | **Media-Alta** | Se persisten headers completos (`Authorization`, cookies, tokens potenciales). | Un request con bearer token termina en JSONL y queda disponible en backups/artefactos. | Redactar headers sensibles (allowlist o denylist robusta), truncar tamaños y hash de valores críticos. |
| RT-05 | Anonimización débil por salt estático por defecto | Resúmenes externalizados | Media | Media | **Media** | `ATTACK_LOG_SALT` cae a valor fijo `centinel-default-salt`. | Correlación cross-entorno de IP pseudonimizadas y reversibilidad asistida por diccionario. | Requerir salt aleatorio por despliegue (obligatorio), rotación periódica y versionado de pseudónimos. |
| RT-06 | Exfiltración de backups vía remoto Git controlado por env | Backup provider `github` | Baja/Media | Alta | **Media-Alta** | `git push` a remoto tomado de `BACKUP_GIT_REPO` con `check=False`. | Actor altera env en host y fuerza envío de backups a repositorio atacante sin fallo visible. | Permitir solo remotos firmados/allowlist, `check=True`, y registro auditable de destino + firma del artefacto. |
| RT-07 | Trigger remoto de air-gap (DoS lógico) | Honeypot + dead-man switch | Media | Alta | **Alta** | Eventos de flood/rate-limit disparan `air_gap()` que detiene servicios y duerme minutos aleatorios. | Botnet golpea honeypot y fuerza ciclos repetidos de hibernación defensiva, degradando disponibilidad. | Añadir circuit-breaker anti-abuso: cuotas por ASN/IP, confirmación multi-señal antes de air-gap, y backoff no bloqueante. |
| RT-08 | TLS saliente sin hardening adicional (solo default CA) | SMTP/HTTP alert channels | Media | Media | **Media** | `starttls()`/POST estándar sin pinning, mTLS ni policy fuerte de ciphers. | Entorno comprometido con CA maliciosa/interceptación corporativa puede inspeccionar tráfico sensible de alertas. | Añadir opción de pinning por SPKI/fingerprint y modo estricto de transporte para canales críticos. |
| RT-09 | Falta de control de dominio destino en collector | Ingesta HTTP | Media | Media | **Media** | Validación URL comprueba esquema/netloc pero no allowlist de dominio objetivo. | Config maliciosa apunta a host atacante que entrega payload sesgado o contenido de trampa. | Validar contra `cne_domains` y/o allowlist fuerte, con resolución DNS y bloqueo de redes internas. |
| RT-10 | Riesgo de integridad operativa por silenciamiento de errores en notificaciones | Alerting path | Media | Media | **Media** | Excepciones en envío de resumen se suprimen para no bloquear polling. | Pérdida silenciosa de telemetría de ataque durante incidente; SOC queda ciego. | Mantener no-bloqueante, pero registrar métricas/contador de fallos y escalación local obligatoria. |

### Priorización táctica (orden sugerido)

1. **RT-01, RT-02, RT-07** (cierre inmediato, 24-48h).
2. **RT-03, RT-04, RT-06** (hardening semana 1).
3. **RT-05, RT-08, RT-09, RT-10** (semana 2 + controles de observabilidad).

### Notas metodológicas

- Este corte está enfocado al **core actual** que sí ejecuta lógica local (sin depender de integraciones externas pendientes).
- La severidad combina factibilidad + impacto operacional sobre confidencialidad, integridad y disponibilidad.
