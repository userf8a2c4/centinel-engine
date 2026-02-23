# Preparación institucional para observadores multilaterales

## Contexto
Esta nota resume qué puede presentar hoy C.E.N.T.I.N.E.L. en conversaciones de alto nivel con entes como OEA/UE/Carter Center, y qué reforzar para aumentar confianza externa.

## Lo que ya está listo

1. **Alcance técnico y neutralidad claros**
   - El proyecto se posiciona como auditoría cívica técnica, no partidaria, reproducible, basada en datos electorales públicos.
   - La metodología prioriza trazabilidad, reproducibilidad y no intrusión.

2. **Paquete de evidencia reproducible para terceros**
   - Existe un modelo de verification bundle (SHA-256 por archivo + Merkle root) y verificación determinista PASS/FAIL.
   - También existe una vía de verificación externa 1-click que combina snapshot, hash record, reglas, versión de pipeline y firmas.

3. **Límites legales y operativos documentados**
   - Se documenta base legal, operación no intrusiva y límites explícitos (solo fuentes públicas, no interferencia, sin tratamiento de datos personales).

4. **Línea base de seguridad y gobernanza activa**
   - Controles de gobernanza con release gates, SBOM y checklist de seguridad.
   - Postura de seguridad con mínimo privilegio, controles de integridad e higiene de secretos.

5. **Resiliencia con evidencia continua en CI**
   - Controles activos: rate limiting, rotación proxy/user-agent, fallbacks y backup seguro.
   - Reportería de resiliencia por release, con score y métricas de recuperación.

## Mejoras priorizadas (sin incluir reglas analíticas)

1. **Observer pack institucional por corrida**
   - Estandarizar paquete por corrida: snapshot + artefactos hash + verificación bundle + metadatos de release + resumen ejecutivo corto.
   - Publicar en español e inglés.

2. **Ejercicios externos de replicabilidad**
   - Ejecutar simulacros periódicos con colaboradores no core y publicar resultados (tasa PASS, fallas frecuentes, remediaciones).

3. **Cierre formal del hardening de gobernanza** ✅
   - Se incorpora plan y bitácora verificable en `docs/GOVERNANCE-HARDENING-CLOSURE.md`.
   - Incluye checklist de cierre, evidencia mínima y estado auditable por fecha.

4. **Tablero de transparencia operativa para métricas de confianza** ✅
   - Se agrega script reproducible `scripts/institutional_transparency_report.py` para consolidar métricas institucionales por release y tendencia.
   - Cobertura con prueba automatizada en `tests/test_institutional_transparency_report.py`.

5. **SLA de publicación de evidencia y disciplina de cadena de custodia** ✅
   - Se publica política operativa en `docs/EVIDENCE-PUBLICATION-SLA.md`.
   - Se define manifiesto de publicación y ventanas mínimas de retención verificable.

6. **Ciclo de atestación técnica independiente**
   - Institucionalizar revisiones técnicas externas recurrentes sobre reproducibilidad, postura de seguridad y controles operativos (separado de la validación estadística que lleva UPNFM).

## Plan sugerido de 60 días

- **Días 1–15:** publicar template oficial de observer pack + resumen ejecutivo bilingüe.
- **Días 16–30:** correr primer simulacro externo de replicabilidad con al menos un actor independiente.
- **Días 31–45:** cerrar y publicar evidencia del hardening de gobernanza.
- **Días 46–60:** publicar el primer dashboard institucional de transparencia y fijar calendario de atestación.

---

# Institutional Readiness for Multilateral Observation Partners

## Context
This note summarizes what C.E.N.T.I.N.E.L. can already present in serious conversations with organizations such as OAS/EU/Carter Center, and what should be strengthened to raise external confidence.

## What is already ready

1. **Clear technical scope and neutrality**
   - The project positions itself as a technical, non-partisan, reproducible civic audit system based on public electoral data.
   - The methodology explicitly prioritizes traceability, reproducibility, and non-intrusion.

2. **Reproducible evidence package for third parties**
   - There is a defined verification bundle model (file-level SHA-256 + Merkle root) and deterministic pass/fail checks.
   - There is also a one-click external verification path combining snapshot, hash record, rules, pipeline version, and signature requirements.

3. **Operational and legal boundaries documented**
   - The project documents legal basis, non-intrusive operation, and explicit limits (public sources only, no interference, no personal data processing).

4. **Security and governance baseline exists**
   - Governance controls include release gates, SBOM checks, and security checklists.
   - Security posture includes least privilege, integrity controls, and secrets hygiene baseline.

5. **Resilience controls and evidence in CI**
   - Active controls include rate limiting, proxy/user-agent rotation, fallback strategies, and secure backups.
   - Resilience reporting (including release-level scoring) is documented as part of CI evidence.

## Priority improvements (excluding analytic rules)

1. **Institution-facing observer pack per run**
2. **External reproducibility drills**
3. **Formal governance hardening closure**
4. **Operational transparency dashboard for confidence metrics**
5. **Evidence publication SLA and chain-of-custody discipline**
6. **Independent technical attestation cycle**
