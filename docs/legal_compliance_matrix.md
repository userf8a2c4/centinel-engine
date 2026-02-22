# Matriz de Cumplimiento Legal / Legal Compliance Matrix

**Proyecto C.E.N.T.I.N.E.L.** -- Actualizado / Updated: Febrero 2026

> Este documento establece el marco legal bajo el cual opera Centinel y evidencia
> tecnica de cumplimiento. Centinel procesa exclusivamente datos publicos del CNE
> conforme a la Ley de Transparencia y Acceso a la Informacion Publica (Decreto
> 170-2006) vigente en Honduras.
>
> This document establishes the legal framework under which Centinel operates and
> the technical evidence of compliance. Centinel processes exclusively public CNE
> data pursuant to the Transparency and Access to Public Information Act (Decree
> 170-2006) in force in Honduras.

---

## Disclaimer / Descargo de Responsabilidad

**Datos solo de fuentes publicas CNE, conforme Ley de Transparencia 170-2006.
Agnostico politico. Sin interpretacion partidaria.**

**Data only from public CNE sources, pursuant to Transparency Law 170-2006.
Politically agnostic. No partisan interpretation.**

---

## Matriz de Cumplimiento / Compliance Matrix

| # | Requisito Legal / Legal Requirement | Cumplimiento en Centinel / Centinel Compliance | Referencia Legal Exacta / Exact Legal Reference | Evidencia Tecnica / Technical Evidence | Notas/Riesgo Residual / Notes/Residual Risk |
|---|---|---|---|---|---|
| 1 | **Acceso a datos publicos agregados** / Access to aggregated public data | **CUMPLE** / COMPLIANT | Decreto 170-2006, Art. 3 (principio de publicidad), Art. 13 (informacion publica de oficio), Art. 4 (derecho de acceso) | Solo se accede a endpoints publicos del CNE que sirven resultados agregados. No se accede a datos personales de votantes ni a sistemas internos. Ver `src/centinel/config.py`, `command_center/config.yaml`. | Riesgo residual: El CNE podria restringir acceso via Cloudflare/WAF. Centinel respeta cualquier bloqueo sin intentar evasion. |
| 2 | **Ausencia de Ley de Proteccion de Datos Personales** / Absence of Personal Data Protection Law | **NO APLICA** / NOT APPLICABLE | Anteproyecto de Ley de Proteccion de Datos Personales en socializacion (feb 2026), sin promulgacion en La Gaceta ni vigencia legal. | Centinel no procesa datos personales de votantes (nombres, DPI, direcciones). Solo datos agregados por departamento/mesa. Modelo de datos en `src/centinel/core/models.py`: solo `CandidateResult`, `Totals`, `Meta`. | Riesgo residual: Si se promulga en el futuro, sera necesario revisar compliance. Actualmente no hay obligacion legal aplicable. |
| 3 | **Respeto a servidores publicos (rate-limits eticos)** / Respect for public servers (ethical rate-limits) | **CUMPLE** / COMPLIANT | Decreto 170-2006, Art. 4 (acceso no debe afectar funcionamiento de la entidad), principio de buena fe procesal. | Token-bucket rate limiter: max 3 burst, 1 token/10s (min 8s). Vital signs: delay minimo etico de 300s (5 min). Modo critico: delay 1800s (30 min). Pausas reactivas ante 429/5xx. Ver `centinel_engine/rate_limiter.py`, `centinel_engine/vital_signs.py`. | Riesgo residual minimo: Los limites son mas conservadores que el acceso tipico de un navegador web humano. |
| 4 | **Integridad y no repudio de evidencia** / Evidence integrity and non-repudiation | **CUMPLE** / COMPLIANT | Decreto 170-2006, Art. 3 (principio de veracidad), principios generales de prueba documental electronica. | Hashing SHA-256 encadenado (`src/centinel/core/hashchain.py`), firmas Ed25519 por snapshot (`src/centinel/core/custody.py`), anclaje en blockchain Arbitrum (`src/centinel/core/blockchain.py`). Cadena de custodia verificable de extremo a extremo. | Riesgo residual: Blockchain depende de infraestructura externa (Arbitrum). Fallback: hash chain local verificable. |
| 5 | **Zero-trust y seguridad de la plataforma** / Zero-trust and platform security | **CUMPLE** / COMPLIANT | Mejores practicas de seguridad informatica, ISO 27001 (referencial). | Middleware zero-trust en API (`src/centinel/api/middleware.py`), Fernet AES-256 para backups cifrados (`centinel_engine/secure_backup.py`), SBOM CycloneDX en CI, Dependabot, Bandit scanning. | Riesgo residual: Seguridad depende de gestion adecuada de secretos y claves. |
| 6 | **Agnosticismo politico absoluto** / Absolute political agnosticism | **CUMPLE** / COMPLIANT | Principio de neutralidad, Decreto 170-2006 Art. 3, Ley Electoral y de las Organizaciones Politicas (LEOP). | Centinel documenta hechos tecnicos verificables sin interpretacion politica. Las reglas estadisticas (Benford, chi-cuadrado, etc.) son agnosticas: detectan anomalias matematicas sin atribucion partidaria. Ver `src/centinel/core/rules/`. Disclaimer obligatorio en todos los reportes generados. | Riesgo residual minimo: Usuarios externos podrian interpretar resultados con sesgo. Centinel incluye disclaimers explicitamente. |
| 7 | **Licencia open-source compatible** / Compatible open-source license | **CUMPLE** / COMPLIANT | AGPL v3 (GNU Affero General Public License v3.0). | Licencia AGPL v3 garantiza transparencia total del codigo. Cualquier parte interesada puede auditar, verificar y reproducir los resultados. Ver `LICENSE`. | Riesgo residual: Ninguno. AGPL v3 es ampliamente aceptada. |
| 8 | **Determinismo y reproducibilidad** / Determinism and reproducibility | **CUMPLE** / COMPLIANT | Principios de auditoria tecnica y buenas practicas de ingenieria. | Snapshots con metadata canonica (JSON determinista), hashing encadenado reproducible, checkpointing con recovery, chaos testing para validacion de resiliencia. | Riesgo residual: Depende de que los datos del CNE no cambien retroactivamente (fuera de control de Centinel). |
| 9 | **Homeostasis operativa y respeto a infraestructura CNE** / Operational homeostasis and respect for CNE infrastructure | **CUMPLE** / COMPLIANT | Decreto 170-2006, Art. 4, principio de minima interferencia. | Sistema vital_signs con 3 modos (normal/conservative/critical). Backoff exponencial en errores. Circuit breaker con apertura automatica. Watchdog para auto-recovery sin sobrecarga. Ver `centinel_engine/vital_signs.py`, `scripts/run_pipeline.py`, `scripts/circuit_breaker.py`. | Riesgo residual: Ninguno significativo. El sistema se auto-regula agresivamente a la baja ante cualquier senal de estres del servidor. |
| 10 | **Rotacion de proxies y User-Agents etica** / Ethical proxy and User-Agent rotation | **CUMPLE** / COMPLIANT | Mejores practicas de scraping etico, terminos implicitos de acceso publico. | Pool de 50+ User-Agents reales. Rotacion de proxy cada 15 requests o ante 429/403/5xx. Sin evasion de WAF ni anti-bot bypasses agresivos. Ver `centinel_engine/proxy_manager.py`, `src/centinel/proxy_handler.py`. | Riesgo residual: Proxies pueden ser bloqueados. Fallback a conexion directa siempre disponible. |
| 11 | **Backup cifrado y proteccion de evidencia** / Encrypted backup and evidence protection | **CUMPLE** / COMPLIANT | Principios de custodia de evidencia digital, ISO 27001 (referencial). | Backup automatico cifrado AES-256 (Fernet) cada 30 min. Multi-destino: local, Dropbox, S3. Nunca falla el pipeline principal por error de backup. Ver `centinel_engine/secure_backup.py`. | Riesgo residual: Depende de gestion de clave de cifrado. Clave almacenada en `config/secrets/` (gitignored) o variable de entorno. |

---

## Marco Legal Hondureno Aplicable / Applicable Honduran Legal Framework

### Ley de Transparencia y Acceso a la Informacion Publica (Decreto 170-2006)

- **Art. 3**: Principios de publicidad, veracidad y maxima publicidad.
- **Art. 4**: Derecho de toda persona a acceder a informacion publica.
- **Art. 13**: Informacion publica de oficio (datos electorales agregados).
- **Art. 17-19**: Procedimientos de solicitud (no aplicable: datos ya son publicos).

### Ley Electoral y de las Organizaciones Politicas (LEOP)

- Establece el marco del proceso electoral. Centinel no interfiere con ninguna
  funcion del CNE ni sustituye autoridad electoral.

### Proteccion de Datos Personales

- **Status (Feb 2026)**: Anteproyecto en fase de socializacion. No promulgado
  en La Gaceta. Sin vigencia legal. Centinel no procesa datos personales de
  todas formas (solo agregados electorales).

---

## Controles Tecnicos Implementados / Implemented Technical Controls

| Control | Modulo | Efecto |
|---|---|---|
| Rate limiting agresivo | `centinel_engine/rate_limiter.py` | Max 3 burst, 1 req/10s, min 8s |
| Homeostasis operativa | `centinel_engine/vital_signs.py` | 3 modos adaptativos, delay min 300s |
| Circuit breaker | `scripts/circuit_breaker.py` | Apertura automatica tras N fallas |
| Hash chain encadenado | `src/centinel/core/hashchain.py` | SHA-256 determinista, append-only |
| Firmas Ed25519 | `src/centinel/core/custody.py` | No repudio por snapshot |
| Anclaje blockchain | `src/centinel/core/blockchain.py` | Inmutabilidad en Arbitrum |
| Backup cifrado | `centinel_engine/secure_backup.py` | AES-256 Fernet, multi-destino |
| Zero-trust API | `src/centinel/api/middleware.py` | Autenticacion obligatoria |
| Proxy rotation etica | `centinel_engine/proxy_manager.py` | 50+ UAs, rotacion cada 15 req |
| Watchdog + recovery | `scripts/watchdog_daemon.py` | Auto-recovery sin sobrecarga |

---

## Historial de Revisiones / Revision History

| Fecha / Date | Version | Cambio / Change |
|---|---|---|
| 2026-02-18 | 1.0 | Creacion inicial de la matriz de cumplimiento legal / Initial creation of legal compliance matrix |

---

*Documento generado como parte del hardening de seguridad del proyecto C.E.N.T.I.N.E.L.
Datos solo de fuentes publicas CNE, conforme Ley de Transparencia 170-2006. Agnostico politico.*
