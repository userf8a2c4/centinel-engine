# Roadmap

## Fases priorizadas (impacto y ejecución)

### Fase 1 — Verificabilidad pública (Top prioridad)
- Entregar verificación externa de 1 click con `scripts/verify_snapshot_bundle.py`.
- Publicar por corrida los artefactos mínimos: snapshot, hashchain, reglas activadas y reporte.
- Mantener checklist corto de replicación para terceros no técnicos.

### Fase 2 — Refuerzo criptográfico
- Firmar digitalmente artefactos de salida por versión de pipeline.
- Estado actual: hash records firmables desde `scripts/hash.py` y verificables en `verify_snapshot_bundle.py`.
- Anclar opcionalmente raíces Merkle de corridas críticas.
- Operar doble canal de verificación: hash local + evidencia pública.

### Fase 3 — Core estable vs reglas experimentales
- Separar `core_rules` (deterministas) y `research_rules` (flag explícito).
- Estado actual: separación operativa habilitada con `rules.enable_research_rules` (default: `false`).
- Definir gate de promoción `research -> core` basado en evidencia reproducible.
- Mantener trazabilidad de cambios por regla y versión.

### Fase 4 — Resiliencia demostrable
- Ejecutar suite de resiliencia en CI y publicar cobertura de fallos recuperados.
- Estado actual: CI genera `resilience_report.json` y `resilience_score` por release.
- Reportar MTTR, eventos 429/503, retries efectivos y recoveries de watchdog.
- Introducir `resilience_score` por release.

### Fase 5 — Gobernanza y supply-chain
- Cerrar lockfile íntegro y hashes de artefactos en entorno conectado.
- Convertir release checklist en gate obligatorio.
- Estado actual: CI ejecuta `release_gate.py` + SBOM versionado por release.
- Publicar SBOM versionado por release.

### Fase 6 — Métricas de precisión auditables
- Exponer métricas por regla (FP/FN revisables históricamente).
- Estado actual: métricas por regla automatizadas vía `scripts/rule_quality_metrics.py`.
- Publicar rúbrica de confianza de anomalías.
- Hacer validación cruzada con revisión manual de casos etiquetados.

### Fase 7 — Endurecimiento de seguridad en producción
- Validación estricta de JSON como bloqueo operativo.
- Estado actual: validación JSON estricta en hashing + gate de auditoría de secretos en CI.
- Redacción obligatoria de datos sensibles en logs.
- Auditoría periódica de secretos y política de rotación.

---

# Roadmap (English)

## Prioritized phases (impact-first delivery)

### Phase 1 — Public verifiability (Top priority)
- Deliver one-click external verification with `scripts/verify_snapshot_bundle.py`.
- Publish per-run minimum artifacts: snapshot, hashchain, enabled rules, and report.
- Keep a short reproducibility checklist for non-technical third parties.

### Phase 2 — Cryptographic hardening
- Digitally sign output artifacts per pipeline version.
- Current status: hash records are signable from `scripts/hash.py` and verifiable in `verify_snapshot_bundle.py`.
- Optionally anchor critical run Merkle roots.
- Operate dual-channel verification: local hash + public evidence.

### Phase 3 — Stable core vs experimental rules
- Separate `core_rules` (deterministic) and `research_rules` (explicit flag).
- Current status: operational separation enabled with `rules.enable_research_rules` (default: `false`).
- Define a promotion gate `research -> core` based on reproducible evidence.
- Keep per-rule/per-version traceability.

### Phase 4 — Demonstrable resilience
- Run resilience suite in CI and publish recovered-failure coverage.
- Current status: CI publishes `resilience_report.json` and release-level `resilience_score`.
- Report MTTR, 429/503 events, effective retries, and watchdog recoveries.
- Introduce a release-level `resilience_score`.

### Phase 5 — Governance and supply-chain
- Close lockfile integrity and artifact hashing in a connected environment.
- Turn release checklist into a mandatory gate.
- Current status: CI runs `release_gate.py` + release-versioned SBOM.
- Publish release-versioned SBOMs.

### Phase 6 — Third-party meaningful quality metrics
- Expose per-rule quality metrics (historically reviewable FP/FN).
- Current status: automated per-rule metrics via `scripts/rule_quality_metrics.py`.
- Publish anomaly confidence rubric.
- Perform cross-validation with manually reviewed labeled cases.

### Phase 7 — Stricter production security
- Enforce strict JSON validation as an operational gate.
- Current status: strict JSON validation in hashing + secrets audit gate in CI.
- Mandate sensitive-data redaction in logs.
- Run periodic secrets audits and rotation policy.
