# Seguridad y gestión de secretos | Security and Secrets Management

## Español

### Propósito
Define prácticas de seguridad para C.E.N.T.I.N.E.L., incluyendo manejo de secretos, cifrado, logging seguro y backups. Complementa [README](../README.md) y [docs/SECRETS_BACKUP.md](SECRETS_BACKUP.md).

### Gestión de secretos
- **Variables de entorno:** usar `.env`/`.env.local` con `python-dotenv` para separar secretos del código.
- **Cifrado de claves sensibles:** utilizar `scripts/encrypt_secrets.py` para cifrar valores sensibles (ej. `ARBITRUM_KEY`).
- **Ubicación de configuración:** mantener secretos y parámetros operativos en `command_center/.env` y `command_center/config.yaml`.

### Cifrado y protección de datos
- **Hashing criptográfico:** snapshots y diffs se protegen con hashes encadenados para integridad.
- **No almacenar datos personales:** únicamente datos públicos agregados.
- **Principio de mínimo privilegio:** limitar acceso a secretos solo a procesos necesarios.

### Logging seguro
- **Evitar datos sensibles:** no registrar llaves ni secretos en logs.
- **Logs rotativos:** habilitar rotación para reducir exposición y consumo.
- **Trazabilidad técnica:** registrar hashes, métricas agregadas y metadatos relevantes.

### Backups y resguardo
- **Procedimientos de respaldo:** seguir la guía de [SECRETS_BACKUP.md](SECRETS_BACKUP.md).
- **Separación de medios:** almacenar copias cifradas en ubicaciones distintas.
- **Pruebas periódicas de restauración:** validar que los respaldos funcionen.

### Auditoría y cumplimiento
- **Escaneos de vulnerabilidades:** ejecutar `make scan-security` (requiere GitHub CLI).
- **Revisión de configuraciones:** verificar que los secretos estén fuera del control de versiones.
- **Trazabilidad reproducible:** alinear con la metodología en [METHODOLOGY.md](METHODOLOGY.md).

### Enlaces relacionados
- [README](../README.md)
- [METHODOLOGY.md](METHODOLOGY.md)
- [LEGAL-AND-OPERATIONAL-BOUNDARIES.md](LEGAL-AND-OPERATIONAL-BOUNDARIES.md)
- [OPERATIONAL-FLOW-AND-CADENCE.md](OPERATIONAL-FLOW-AND-CADENCE.md)
- [SECRETS_BACKUP.md](SECRETS_BACKUP.md)

---

## English

### Purpose
Defines security practices for C.E.N.T.I.N.E.L., including secrets handling, encryption, safe logging, and backups. It complements the [README](../README.md) and [docs/SECRETS_BACKUP.md](SECRETS_BACKUP.md).

### Secrets management
- **Environment variables:** use `.env`/`.env.local` with `python-dotenv` to keep secrets out of code.
- **Encrypt sensitive keys:** use `scripts/encrypt_secrets.py` to encrypt sensitive values (e.g., `ARBITRUM_KEY`).
- **Configuration location:** keep secrets and operational parameters in `command_center/.env` and `command_center/config.yaml`.

### Encryption and data protection
- **Cryptographic hashing:** snapshots and diffs are protected with chained hashes for integrity.
- **No personal data storage:** only aggregated public data.
- **Principle of least privilege:** limit secret access to required processes only.

### Safe logging
- **Avoid sensitive data:** do not log keys or secrets.
- **Rotating logs:** enable rotation to reduce exposure and storage overhead.
- **Technical traceability:** record hashes, aggregate metrics, and relevant metadata.

### Backups and safekeeping
- **Backup procedures:** follow [SECRETS_BACKUP.md](SECRETS_BACKUP.md).
- **Media separation:** store encrypted copies in distinct locations.
- **Periodic restore tests:** validate that backups are usable.

### Auditing and compliance
- **Vulnerability scans:** run `make scan-security` (requires GitHub CLI).
- **Configuration review:** ensure secrets remain out of version control.
- **Reproducible traceability:** align with [METHODOLOGY.md](METHODOLOGY.md).

### Related links
- [README](../README.md)
- [METHODOLOGY.md](METHODOLOGY.md)
- [LEGAL-AND-OPERATIONAL-BOUNDARIES.md](LEGAL-AND-OPERATIONAL-BOUNDARIES.md)
- [OPERATIONAL-FLOW-AND-CADENCE.md](OPERATIONAL-FLOW-AND-CADENCE.md)
- [SECRETS_BACKUP.md](SECRETS_BACKUP.md)
