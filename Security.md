# POLÍTICA DE SEGURIDAD | SECURITY POLICY
### Protocolo de Supervisión de Integridad Automatizado | Automated Integrity Oversight Protocol

---

### [ES] SECCIÓN EN ESPAÑOL

#### 1. REPORTE DE VULNERABILIDADES
Si identifica una vulnerabilidad de seguridad en el motor de auditoría o en la infraestructura de captura de datos, le solicitamos que no la haga pública de inmediato. Por favor, abra un "Issue" técnico con la etiqueta `security-low` o contacte a los administradores del repositorio mediante los canales oficiales para una mitigación coordinada.

#### 2. INTEGRIDAD DEL CÓDIGO
Para garantizar que el sistema no ha sido comprometido:
* **Firmas SHA-256:** Todos los scripts principales cuentan con un hash de integridad registrado en la sección de lanzamientos (Releases) y en el registro histórico de commits.
* **Auditoría de Dependencias:** El sistema minimiza el uso de librerías externas para reducir la superficie de ataque. Las dependencias activas son monitoreadas mediante GitHub Dependabot.

#### 3. SEGURIDAD DE LOS DATOS (ANTI-TAMPERING)
El Proyecto C.E.N.T.I.N.E.L. implementa un protocolo anti-manipulación basado en:
* **Inmutabilidad de Git:** Cada snapshot es commiteado con un timestamp del servidor, creando una cadena de custodia auditable.
* **Verificación Cruzada:** Se recomienda a los auditores independientes realizar sus propias capturas para cotejar los hashes SHA-256 publicados en este repositorio.

#### 4. ALCANCE DE SEGURIDAD
Esta política cubre exclusivamente el código fuente y la estructura de datos contenida en este repositorio. No se tiene control sobre la disponibilidad o veracidad de los servidores de origen del CNE.

#### 5. ENDURECIMIENTO PROACTIVO (SUGERIDO)
* **Secrets cifrados:** Use `scripts/encrypt_secrets.py` para cifrar `ARBITRUM_PRIVATE_KEY` u otros secretos antes de almacenarlos. Mantenga `SECRET_ENCRYPTION_KEY` fuera del repositorio.
* **Validación estricta de JSONs:** Rechace estructuras no válidas y registre solo hashes de verificación.
* **Logging seguro:** Rotación de logs y redacción de valores sensibles para evitar exposición accidental.
* **Rate limiting:** Mantenga límites por IP para mitigar abuso de endpoints públicos.

---

### [EN] ENGLISH SECTION

#### 1. VULNERABILITY REPORTING
If you identify a security vulnerability in the audit engine or data capture infrastructure, we request that you do not disclose it publicly immediately. Please open a technical Issue with the `security-low` label or contact the repository administrators through official channels for coordinated mitigation.

#### 2. CODE INTEGRITY
To ensure the system has not been compromised:
* **SHA-256 Signatures:** All main scripts have an integrity hash registered in the Releases section and within the historical commit log.
* **Dependency Auditing:** The system minimizes the use of external libraries to reduce the attack surface. Active dependencies are monitored via GitHub Dependabot.

#### 3. DATA SECURITY (ANTI-TAMPERING)
Proyecto C.E.N.T.I.N.E.L. implements an anti-tampering protocol based on:
* **Git Immutability:** Every snapshot is committed with a server timestamp, creating an auditable chain of custody.
* **Cross-Verification:** Independent auditors are encouraged to perform their own captures to cross-reference the SHA-256 hashes published in this repository.

#### 4. SECURITY SCOPE
This policy exclusively covers the source code and data structure contained within this repository. There is no control over the availability or veracity of the CNE source servers.

#### 5. PROACTIVE HARDENING (SUGGESTED)
* **Encrypted secrets:** Use `scripts/encrypt_secrets.py` to encrypt `ARBITRUM_PRIVATE_KEY` or other secrets before storage. Keep `SECRET_ENCRYPTION_KEY` out of the repo.
* **Strict JSON validation:** Reject invalid structures and log only verification hashes.
* **Secure logging:** Log rotation and redaction to avoid accidental exposure.
* **Rate limiting:** Keep per-IP limits to mitigate abuse of public endpoints.

---

**SECURITY_STATUS:** ENFORCED | **INTEGRITY_CHECK:** ACTIVE
