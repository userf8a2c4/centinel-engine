# Dev Diary - 202602 - SecurityCiHardening - 01

**Fecha aproximada / Approximate date:** 23-feb-2026 / February 23, 2026  
**Fase / Phase:** Endurecimiento de CI y pruebas de seguridad en dev-v9 / CI hardening and security-test stabilization in dev-v9  
**Versión interna / Internal version:** v0.1.x (ciclo dev-v9)  
**Rama / Branch:** dev-v9  
**Autor / Author:** userf8a2c4

**Contexto de esta entrada / Entry context:**  
Retomamos el diario después de `dev-diary-202602-ReadmeAllGreen-01.md` con una intención muy concreta: proteger la credibilidad del “verde” que ya habíamos conseguido. Esta vez no se trató de añadir una funcionalidad llamativa, sino de limpiar fricciones reales en el pipeline de seguridad, estabilizar pruebas que se rompían por imports no protegidos y ajustar dependencias para que el resultado sea repetible.

---

## [ES] Diario narrativo desde la última publicación

### 1) Qué cambió y por qué ahora
Desde la última entrada, vimos que parte del valor ganado en estabilidad se estaba erosionando por fallos en rutas de seguridad e integración. El problema no era solo “un test rojo”: era la posibilidad de que un estado aparentemente sano ocultara fragilidad de entorno.

Por eso priorizamos tres frentes:
- corregir pruebas de seguridad/integración que fallaban por imports y dependencias opcionales,
- alinear lockfile y reglas de CI para reducir ruido entre ramas,
- y reforzar higiene del repo para que artefactos locales no contaminaran señales de calidad.

### 2) Decisiones de implementación
El enfoque fue deliberadamente pragmático:
- **Imports más seguros y perezosos donde correspondía**, para evitar romper flujos completos por componentes no críticos.
- **Regenerar y normalizar `poetry.lock`**, porque la reproducibilidad de dependencias es parte del contrato de calidad.
- **Ajustar comportamiento de CI por tipo de rama**, evitando bloquear iteración en ramas de desarrollo por validaciones que no aportaban señal útil en ese contexto.
- **Fortalecer `.gitignore` para artefactos de cobertura y SBOM**, reduciendo ruido en commits y revisiones.

### 3) Impacto operativo
Este trabajo tiene un impacto menos “visible” que una feature, pero más estratégico:
- menos falsos negativos en seguridad/integración,
- menor intermitencia en pipelines,
- mejor trazabilidad de qué falló realmente cuando algo cae,
- y más confianza para iterar sin romper la base.

En términos prácticos: se protege la narrativa de calidad que venimos construyendo desde dev-v7, ahora trasladada al ritmo de dev-v9.

### 4) Aprendizaje de ciclo
La lección principal se repite, pero ahora con evidencia reciente: la estabilidad no se conserva sola. Hay que mantenerla activamente en cada capa (código, dependencias, CI, documentación y disciplina de commits).

---

## [EN] Narrative diary since the previous publication

### 1) What changed and why now
After the previous diary entry, we identified reliability erosion around security and integration pipelines. This was not just “a red test”; it was a trust issue where green status could become misleading under certain environment conditions.

So we prioritized three workstreams:
- fixing security/integration tests affected by unguarded imports and optional dependency behavior,
- aligning lockfile and CI rules to reduce branch-specific noise,
- and tightening repo hygiene so local artifacts stop polluting quality signals.

### 2) Implementation choices
We intentionally chose practical, repeatable fixes:
- **Safer/lazy import paths where appropriate** to prevent non-critical components from collapsing broader flows.
- **Lockfile normalization (`poetry.lock`)** as a reproducibility baseline.
- **Branch-aware CI behavior** to keep dev iteration fluid without diluting meaningful checks.
- **Expanded `.gitignore` hygiene for coverage and SBOM artifacts** to reduce review noise.

### 3) Operational impact
This cycle delivered less flashy but highly strategic outcomes:
- fewer false negatives in security/integration checks,
- lower CI flakiness,
- clearer failure attribution when incidents occur,
- and stronger confidence to keep shipping without destabilizing the baseline.

In short: we preserved the quality narrative built earlier and translated it into a more resilient dev-v9 delivery loop.

### 4) Cycle takeaway
Recent work confirms the core principle: stability does not sustain itself. It must be continuously maintained across code, dependencies, CI workflows, docs, and commit hygiene.

---

## Cierre de entrada / Entry close
Seguimos con la misma filosofía: cambios pequeños, razones explícitas y mejoras acumulativas que sí se sostienen en el tiempo.
