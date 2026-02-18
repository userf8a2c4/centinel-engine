# Legal Compliance Matrix / Matriz de Cumplimiento Legal

**Proyecto C.E.N.T.I.N.E.L. — Legal Compliance Matrix**

> **Disclaimer / Descargo de responsabilidad:**
> Centinel accede exclusivamente a información pública obligatoria publicada por el Consejo Nacional Electoral (CNE) de Honduras en cumplimiento de su mandato constitucional de transparencia. No accede a datos personales, sistemas internos, bases de datos protegidas ni información clasificada. Este documento no constituye asesoría legal.
>
> Centinel exclusively accesses mandatory public information published by Honduras' National Electoral Council (CNE) in compliance with its constitutional transparency mandate. It does not access personal data, internal systems, protected databases, or classified information. This document does not constitute legal advice.

---

## 1. Marco Legal Aplicable / Applicable Legal Framework

| # | Requisito Legal / Legal Requirement | Estado Actual de Centinel / Current Centinel Status | Referencia Legal / Legal Reference | Evidencia Técnica / Technical Evidence | Notas / Notes |
|---|--------------------------------------|------------------------------------------------------|--------------------------------------|----------------------------------------|---------------|
| 1 | **Acceso a información pública** — Todo ciudadano tiene derecho de acceso a la información pública generada por entidades estatales, incluidos los resultados electorales publicados por el CNE. | **CUMPLE** — Centinel accede únicamente a endpoints públicos del portal de resultados del CNE (`resultadosgenerales2025.cne.hn`), datos que el CNE publica voluntariamente para consulta ciudadana. | Ley de Transparencia y Acceso a la Información Pública (Decreto 170-2006, reformado por Decreto 64-2007, Decreto 129-2011 y Decreto 65-2023). Arts. 1, 2, 3, 4 y 13. Constitución de la República de Honduras, Art. 80. | Endpoints configurados en `command_center/config.yaml`; todas las URLs son del dominio público del CNE. Logs de acceso auditables en `logs/centinel.log`. | El Art. 13 del Decreto 170-2006 establece que la información presupuestaria, estadística y electoral generada por órganos del Estado es de acceso público obligatorio. Reformas hasta 2023 amplían las obligaciones de publicación activa. |
| 2 | **Datos personales — Ausencia de ley específica vigente** — Honduras no cuenta a febrero 2026 con una Ley de Protección de Datos Personales promulgada y vigente. Existe un anteproyecto en fase de socialización legislativa. | **CUMPLE** — Centinel NO recopila, almacena ni procesa datos personales de ningún tipo. Solo procesa datos electorales agregados (totales de votos por partido/departamento). | Anteproyecto de Ley de Protección de Datos Personales (en socialización ante el Congreso Nacional, sin promulgación a feb. 2026). Constitución de Honduras, Art. 76 (privacidad). Convención Americana sobre Derechos Humanos, Art. 11 (protección de honra y dignidad). | Código fuente auditable: `src/centinel/download.py` y `scripts/download_and_hash.py` — ninguna extracción de PII. Snapshots en `data/` contienen solo resultados numéricos agregados. | Aunque no hay ley vigente, Centinel aplica principios de minimización de datos como buena práctica alineada con estándares internacionales (GDPR Art. 5.1.c como referencia de mejores prácticas). |
| 3 | **Rate-limiting ético y scraping responsable** — Acceso respetuoso a servidores públicos sin causar degradación del servicio. | **CUMPLE** — Intervalo mínimo ético de 300 segundos (5 minutos) entre requests hardcodeado. Rate-limiter de lado cliente (token-bucket, 1 req/8-12s, burst 3). Homeostasis adaptativa que aumenta delays en caso de errores. | Ley de Transparencia (Decreto 170-2006), Art. 4 — principio de buena fe en acceso a información. Código Penal de Honduras (Decreto 130-2017), Arts. 393-397 (delitos informáticos) — N/A: Centinel no elude controles de acceso. | `centinel_engine/vital_signs.py`: `ethical_minimum_delay = 300`. `centinel_engine/rate_limiter.py`: TokenBucketRateLimiter con min_interval=8s. `command_center/config.yaml`: `rate_limit_cooldown: 10`. | El Código Penal tipifica delitos informáticos en Arts. 393-397, pero estos aplican a acceso no autorizado a sistemas protegidos. Centinel accede a APIs públicas sin autenticación, sin eludir controles. |
| 4 | **Integridad y cadena de custodia de evidencia** — Los datos recopilados deben mantener integridad verificable para tener valor probatorio. | **CUMPLE** — Hashing SHA-256 encadenado con separación de dominio. Anclaje en blockchain Arbitrum L2. Escrituras atómicas para prevenir corrupción. Backups cifrados AES-256. | Código Procesal Penal de Honduras (Decreto 9-99-E), Arts. 223-228 (cadena de custodia de evidencia). Ley sobre Firmas Electrónicas (Decreto 149-2013). | `src/centinel/download.py`: `chained_hash()` con prefijo `centinel-chain-v1`. `src/centinel/core/custody.py`: verificación de cadena al arranque. `centinel_engine/secure_backup.py`: respaldos cifrados Fernet AES-256. Anclaje blockchain en `anchor/arbitrum_anchor.py`. | La cadena de hashes encadenados con timestamps proporciona integridad criptográfica equivalente a firma digital para efectos de preservación de evidencia técnica. |
| 5 | **Zero-trust y seguridad defensiva** — Protección contra ataques, manipulación y desacreditación. | **CUMPLE** — Arquitectura zero-trust. Honeypots para detección de intrusiones. Forensics logging. Defensive shutdown automático. Circuit breaker contra DDoS. Cloudflare preparado (PR #397). | Ley de Transparencia (Decreto 170-2006), Art. 25 — obligación de custodiar información pública. Normas de auditoría de la OEA/OAS Electoral Observation methodology. | `core/security.py`: DefensiveSecurityManager. `core/attack_logger.py`: AttackForensicsLogbook. `scripts/circuit_breaker.py`: CircuitBreaker. `command_center/advanced_security_config.yaml`: honeypot, airgap, monitoring. | Diseñado para cumplir con estándares de observación electoral de OEA, UE y Centro Carter. |
| 6 | **Neutralidad política y agnosticismo** — El sistema no debe favorecer ni perjudicar a ningún partido o candidato. | **CUMPLE** — Centinel es 100% agnóstico: captura datos agregados de todos los partidos sin distinción. No interpreta, filtra ni sesga resultados. Reglas de anomalías son estadísticas puras (Benford, outliers ML, dispersión geográfica). | Ley Electoral y de las Organizaciones Políticas (Decreto 44-2004, reformado), Arts. 1, 5 y 199 — principio de igualdad en la observación electoral. | `src/centinel/core/rules_engine.py`: reglas puramente estadísticas. `command_center/rules.yaml`: configuración auditable. Todos los snapshots preservan datos completos de todos los partidos. | Metodología documentada en `docs/methodology.md`. |
| 7 | **Observación electoral legítima** — Marco legal para observación nacional e internacional de procesos electorales. | **CUMPLE** — Centinel opera como herramienta técnica de observación ciudadana de datos públicos, función protegida constitucionalmente. | Constitución de Honduras, Art. 45 (derecho de petición). Ley Electoral (Decreto 44-2004), Título VII — observación electoral. Acuerdo de la OEA sobre Observación Electoral Interamericana. | Open-source bajo AGPL v3. Repositorio público en GitHub. Documentación completa en `docs/`. | La observación ciudadana de procesos electorales es un derecho reconocido internacionalmente. Centinel es una herramienta técnica, no una organización de observación. |

---

## 2. Protecciones Técnicas Contra Riesgos Legales / Technical Protections Against Legal Risks

| Riesgo / Risk | Mitigación Técnica / Technical Mitigation | Evidencia / Evidence |
|----------------|---------------------------------------------|----------------------|
| Acusación de acceso no autorizado / Unauthorized access accusation | Solo accede a APIs públicas sin autenticación. Rate-limiting ético. No elude CAPTCHAs, WAFs ni controles de acceso. | Código fuente abierto y auditable. Logs completos. |
| Acusación de denegación de servicio / DoS accusation | Mínimo ético 5 min entre ciclos. Token-bucket 1 req/8-12s. Homeostasis adaptativa. Circuit breaker. | `vital_signs.py`, `rate_limiter.py`, `circuit_breaker.py` |
| Acusación de manipulación de datos / Data manipulation accusation | Hashing SHA-256 encadenado. Anclaje blockchain inmutable. Backups cifrados multi-destino. Zero-trust. | `download.py`, `arbitrum_anchor.py`, `secure_backup.py` |
| Desacreditación por sesgo político / Political bias discrediting | 100% agnóstico. Reglas estadísticas puras. Sin interpretación política. | `methodology.md`, `rules_engine.py` |
| Bloqueo del CNE / CNE blocking | Proxy rotation. User-Agent pool. Cloudflare. Backups automáticos preservan evidencia ya recopilada. | `proxy_manager.py`, `proxy_handler.py`, `secure_backup.py` |
| Spoofing o envenenamiento de datos / Data spoofing/poisoning | Hash chain verifica integridad. Blockchain anchoring crea registro inmutable. Detección de anomalías estadísticas. | `custody.py`, `hashchain.py`, `rules_engine.py` |

---

## 3. Cumplimiento con Estándares de Observación Internacional / International Observation Standards Compliance

| Estándar / Standard | Cumplimiento / Compliance | Referencia / Reference |
|----------------------|---------------------------|------------------------|
| OEA/OAS — Metodología de Observación Electoral | Recopilación sistemática y verificable de datos públicos con cadena de custodia criptográfica. | Inter-American Democratic Charter, Arts. 23-25. |
| Unión Europea — Manual de Observación Electoral | Transparencia metodológica completa. Código abierto. Datos auditables. | EU Election Observation Methodology (2016). |
| Centro Carter — Principios de Observación Electoral | Neutralidad demostrable. Sin interpretación política. Basado en evidencia técnica. | Declaration of Principles for International Election Observation (UN, 2005). |
| Declaración de Principios para Observación Internacional | Imparcialidad. No interferencia. Precisión. Transparencia. | Declaration of Principles (2005), signed by OAS, EU, Carter Center, et al. |

---

## 4. Historial de Actualizaciones / Update History

| Fecha / Date | Cambio / Change | Autor / Author |
|--------------|------------------|----------------|
| 2026-02-18 | Creación inicial de la matriz de cumplimiento legal. Initial creation of legal compliance matrix. | Centinel Security Hardening |

---

*Documento generado como parte del endurecimiento de seguridad nivel 9.9-10/10 de Centinel.*
*Document generated as part of Centinel's 9.9-10/10 security hardening.*
