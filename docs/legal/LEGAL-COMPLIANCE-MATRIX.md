# Legal Compliance Matrix — Centinel (Feb 2026)

> **Scope / Alcance:** This matrix documents legal-operational controls for Centinel over public CNE data only.  
> **Disclaimer / Descargo:** This is a technical compliance artifact, not legal advice.

| Requisito Legal | Cumplimiento en Centinel | Referencia Legal Exacta | Evidencia Técnica | Notas/Riesgo Residual |
|---|---|---|---|---|
| Acceso a datos públicos agregados del CNE | **OK (Cumple).** Centinel consume únicamente fuentes públicas publicadas por el CNE, sin autenticación ni intrusión. | **Ley de Transparencia y Acceso a la Información Pública (Decreto 170-2006)**, arts. **3** y **13** (publicidad y acceso a información pública). | Configuración de scraping y pipeline orientada a endpoints públicos; controles de trazabilidad en hash chain y logs. | Riesgo residual bajo: cambios regulatorios o de endpoint deben monitorearse y documentarse en changelog.
| Agnosticismo político y neutralidad operativa | **OK (Cumple).** Proceso técnico, reproducible y no partidario; solo evidencia verificable. | Decreto 170-2006 (principio de acceso e interés público), marco constitucional de libertad de información pública. | README y reportes incluyen disclaimer explícito de neutralidad y uso de datos públicos CNE. | Riesgo residual reputacional: terceros pueden politizar hallazgos; mitigación mediante evidencia reproducible y método abierto.
| Ausencia de Ley de Protección de Datos Personales vigente (feb 2026) | **OK (Cumple).** No se procesan datos personales; solo agregados electorales. | Estado normativo nacional a feb-2026: anteproyecto en socialización, sin promulgación en La Gaceta. | Estructuras de datos y snapshots centradas en totales agregados; sin campos de PII. | Riesgo residual normativo: si se promulga una ley, se debe actualizar matriz y controles de retención.
| Rate-limits éticos + pausas reactivas para no degradar infraestructura pública | **OK (Cumple).** Token bucket cliente: burst 3, 1 token/10s configurable (mínimo 8s), y homeostasis con delay crítico 1800s. | Buenas prácticas de uso responsable de servicios públicos; Decreto 170-2006 (buena fe y finalidad pública). | `centinel_engine/rate_limiter.py`, `centinel_engine/vital_signs.py`, y pruebas hostiles (`tests/test_hostile_scenarios.py`). | Riesgo residual: cambios en política anti-bot del CNE; mitigación con reducción de cadencia y fallback.
| Integridad/no repudio técnico (zero-trust, hashing encadenado, Cloudflare/homeostasis) | **OK (Cumple).** Evidencia inmutable y verificable con hash chain + respaldos cifrados + modo crítico automático. | Principios de cadena de custodia digital y preservación de evidencia técnica aplicables a auditoría electoral ciudadana. | `centinel_engine/secure_backup.py`, `src/centinel/core/hashchain.py`, controles de seguridad en auditoría y pipeline. | Riesgo residual medio-bajo: depende de disciplina operativa (rotación de claves, backups y verificación periódica). |

## Mandatory operational statement / Leyenda operativa obligatoria

**Datos solo de fuentes públicas CNE, conforme Ley Transparencia 170-2006. Agnóstico político.**
