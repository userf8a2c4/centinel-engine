---
Version: 1.1
Date: 2026-05-20
Status: Active
Audience: Grant evaluators · OTF · NED · NDI · IRI · Mozilla Foundation · Carter Center · UPNFM
---

# Autonomous Operations Capability / Capacidad de Operación Autónoma

---

## The core claim / El argumento central

**EN:** Centinel can monitor a national election from fork to final report with **a single human action at setup**: creating a GitHub Personal Access Token. Everything else — infrastructure provisioning, endpoint discovery, data capture, cryptographic chaining, anomaly detection, failure recovery, and public data publication — runs without operator intervention.

This is verifiable. Every claim below maps to a specific file and workflow in this repository.

---

**ES:** Centinel puede monitorear una elección nacional desde el fork hasta el reporte final con **una sola acción humana en el setup**: crear un Personal Access Token de GitHub. Todo lo demás — aprovisionamiento de infraestructura, descubrimiento de endpoints, captura de datos, encadenamiento criptográfico, detección de anomalías, recuperación de fallos y publicación pública de datos — corre sin intervención del operador.

Esto es verificable. Cada afirmación a continuación apunta a un archivo y workflow específico en este repositorio.

---

## Phase 1 — Fork and deployment / Fase 1 — Fork y despliegue

**(≤ 10 minutes, 1 human action / ≤ 10 minutos, 1 acción humana)**

### What the system does automatically / Lo que el sistema hace solo

| Action / Acción | Implementation / Implementación | Trigger / Disparador |
|--------|---------------|---------|
| Detects new fork environment / Detecta que es un fork nuevo | `setup-wizard.yml` state check | First push to `main` / Primer push a `main` |
| Opens GitHub Issue with exact setup instructions / Abre Issue con instrucciones exactas | `setup-wizard.yml` → `github-script` | Token missing / Token ausente |
| Provides direct link to pre-scoped token creation page / Link directo a creación de token preconfigurado | Issue body with `?scopes=repo` URL | Token missing / Token ausente |
| Retries hourly if operator added token but forgot to re-run wizard / Reintenta cada hora si el operador añadió el token pero olvidó re-ejecutar el wizard | `schedule: '0 * * * *'` | Always / Siempre |
| Creates `centinel-data` public repo via GitHub API / Crea `centinel-data` via API | `setup-wizard.yml` → curl POST | Token present, repo absent / Token presente, repo ausente |
| Initializes directory structure in `centinel-data` / Inicializa estructura de directorios | `push_file()` in wizard | Repo just created / Repo recién creado |
| Deploys IPFS-pin and weekly-backup workflows / Despliega workflows de pin IPFS y backup semanal | `push_file()` in wizard | Repo just created / Repo recién creado |
| Enables GitHub Pages via API / Activa GitHub Pages vía API | `setup-wizard.yml` → curl POST | Setup complete / Setup completo |
| Opens fallback Issue if Pages auto-enable fails / Abre Issue si Pages no se activa solo | `github-script` with deduplication | Pages API returns non-2xx |
| Updates README with real links / Actualiza README con links reales | `sed` + `git commit` in wizard | Setup complete / Setup completo |
| Transforms fork README from "deploy guide" to "live instance" / Transforma el README de guía a estado operativo | Python regex replace in wizard | Setup complete / Setup completo |
| Closes setup Issue automatically / Cierra el Issue de setup automáticamente | `github-script` on `state=ready` | Token + repo verified / Token + repo verificados |

### What requires a human / Lo que requiere un humano

**EN:** One action: creating a GitHub Personal Access Token. GitHub's security policy prohibits any external system from creating tokens on behalf of a user. This is not a limitation of Centinel — it is a GitHub platform constraint with no exception. The wizard opens an Issue with a direct link to the pre-scoped token creation page. The operator clicks, copies, pastes. That is the full extent of required human action for a standard deployment.

**ES:** Una acción: crear un Personal Access Token de GitHub. La política de seguridad de GitHub prohíbe que cualquier sistema externo cree tokens en nombre del usuario. Esto no es una limitación de Centinel — es una restricción de la plataforma de GitHub sin excepción. El wizard abre un Issue con un link directo a la página de creación de token preconfigurado. El operador hace clic, copia, pega. Eso es todo lo que se requiere del humano en un despliegue estándar.

---

## Phase 2 — Endpoint discovery / Fase 2 — Descubrimiento de endpoints

**EN:** Electoral authorities frequently use Angular or React SPAs that construct API URLs at runtime — invisible in source code. Centinel handles this in two layers:

**ES:** Las autoridades electorales frecuentemente usan SPAs en Angular o React que construyen las URLs de sus APIs en tiempo de ejecución — invisibles en el código fuente. Centinel lo resuelve en dos capas:

### Layer 1 — Static analysis / Capa 1 — Análisis estático

**EN:** Scans JavaScript bundles and page source for URL patterns matching known electoral API structures. Fast, zero extra dependencies.

**ES:** Escanea los bundles de JavaScript y el código fuente de la página buscando patrones de URL que coincidan con estructuras conocidas de APIs electorales. Rápido, sin dependencias adicionales.

### Layer 2 — Playwright fallback / Capa 2 — Playwright como fallback

**EN:** If static analysis returns zero valid candidates, launches a headless Chromium instance, navigates to the electoral authority URL, and intercepts all XHR/fetch responses in real time. Captures whatever the application actually requests, regardless of how URLs are constructed.

**ES:** Si el análisis estático retorna cero candidatos válidos, lanza una instancia de Chromium headless, navega a la URL de la autoridad electoral e intercepta todas las respuestas XHR/fetch en tiempo real. Captura lo que la aplicación realmente solicita, sin importar cómo se construyan las URLs.

### Validation / Validación (caso CNE Honduras)

**EN:** Each candidate endpoint is validated against:
- Numeric department code in URL path (`/01-/` = Atlántida, `/00-/` = national aggregate, codes 01–18 alphabetically)
- Department field in JSON payload (`departamento`, `department`, `depto` keys)
- Cross-check: if URL says Atlántida and payload says Islas de la Bahía, the candidate is rejected

This prevents a class of silent errors where the system captures a valid endpoint for the wrong geographic unit.

**ES:** Cada endpoint candidato se valida contra:
- Código numérico de departamento en la ruta URL (`/01-/` = Atlántida, `/00-/` = agregado nacional, códigos 01–18 en orden alfabético)
- Campo de departamento en el payload JSON (claves `departamento`, `department`, `depto`)
- Verificación cruzada: si la URL dice Atlántida y el payload dice Islas de la Bahía, el candidato se rechaza

Esto previene una clase de errores silenciosos donde el sistema captura un endpoint válido de la unidad geográfica incorrecta.

**Implementation / Implementación:** `centinel_engine/cne_endpoint_healer.py` — `DEPARTMENT_CODE_MAP`, `_discover_via_playwright()`, `_validate_candidates()`

---

## Phase 3 — Continuous capture and cryptographic chaining / Fase 3 — Captura continua y encadenamiento criptográfico

### Capture cadence / Cadencia de captura

**EN:**
- `scheduler.yml`: every 15 minutes
- `audit.yml`: every 3 hours (configurable to 30 minutes for election night via `workflow_dispatch` input `election_mode`)

**ES:**
- `scheduler.yml`: cada 15 minutos
- `audit.yml`: cada 3 horas (configurable a 30 minutos para noche electoral mediante el input `election_mode` en `workflow_dispatch`)

### Cryptographic guarantees per snapshot / Garantías criptográficas por snapshot

**EN:**
- SHA-256 hash of each data file
- Merkle root across all files in the snapshot
- Hash chain: each snapshot includes the hash of the previous snapshot
- OpenTimestamps anchor in Bitcoin (no cost, no trusted third party)

These properties together mean: any observer can verify, offline, that a specific snapshot existed at a specific time and has not been modified since publication. No institutional trust required.

**ES:**
- Hash SHA-256 de cada archivo de datos
- Raíz de Merkle sobre todos los archivos del snapshot
- Cadena de hashes: cada snapshot incluye el hash del snapshot anterior
- Ancla en Bitcoin vía OpenTimestamps (sin costo, sin tercero de confianza)

Estas propiedades juntas significan: cualquier observador puede verificar, offline, que un snapshot específico existió en un momento específico y no fue modificado desde su publicación. Sin confianza institucional requerida.

### Anomaly detection / Detección de anomalías (automated / automatizada)

**EN:**
- Benford's Law analysis on vote counts
- Statistical deviation detection between consecutive snapshots
- Cross-witness comparison when federation is active
- Results published automatically to `centinel-data` and the visualization panel

**ES:**
- Análisis de la Ley de Benford sobre conteos de votos
- Detección de desviaciones estadísticas anómalas entre snapshots consecutivos
- Comparación entre testigos cuando la federación está activa
- Resultados publicados automáticamente en `centinel-data` y el panel de visualización

---

## Phase 4 — Defense under adversarial conditions / Fase 4 — Defensa bajo condiciones adversariales

**EN:** The system applies layered defense with automatic mode escalation. No operator action required until the system explicitly requests it.

**ES:** El sistema aplica defensa en profundidad con escalada automática de modo. No se requiere acción del operador hasta que el sistema lo solicite explícitamente.

### Automatic escalation / Escalada automática

| Failures / Fallos | Mode / Modo | Capture interval / Intervalo | Action / Acción |
|----------|------|-----------------|--------|
| 0–1 | NORMAL | 30 min | Standard / Estándar |
| 2–3 | CAUTION | 20 min | Increased frequency / Mayor frecuencia |
| 4+ | SURVIVAL | 10 min | Maximum resilience / Máxima resiliencia |

### Specific threats handled automatically / Amenazas específicas manejadas automáticamente

| Threat / Amenaza | Response / Respuesta | Implementation / Implementación |
|--------|----------|---------------|
| Endpoint temporarily unreachable / Endpoint temporalmente inaccesible | Circuit breaker opens; closes on recovery / Circuit breaker abre; cierra al recuperarse | `cne_endpoint_healer.py` |
| Selective blocking by capture pattern / Bloqueo selectivo por patrón de captura | Non-deterministic jitter in intervals / Jitter no determinista en intervalos | `download_and_hash.py` |
| Man-in-the-middle / traffic interception / MITM / interceptación de tráfico | ChaCha20-Poly1305 encryption in transit / Cifrado en tránsito | `core/advanced_security.py` |
| Local state manipulation / Manipulación del estado local | Auto-resync from replicas before resuming / Re-sincronización desde réplicas | `air_gap()` mechanism |
| Active compromise detected / Compromiso activo detectado | Honeypot trigger → freeze → backup → integrity check → resume / Honeypot → congelar → backup → verificar → reanudar | `air_gap()` mechanism |
| Endpoint URL changes / Cambio de URL de endpoint | Healer re-discovers from base URL on next cycle / Healer re-descubre desde URL base en el próximo ciclo | `cne_endpoint_healer.py` |

---

## Phase 5 — Infrastructure failure recovery / Fase 5 — Recuperación de fallos de infraestructura

### git push failure in `audit.yml` / Fallo de git push en `audit.yml`

**EN:** Three-attempt recovery chain, fully automatic:

1. **Normal rebase** — standard `git pull --rebase` + push
2. **fetch + hard-reset + recommit** — discards the merge conflict, applies the captured snapshot on top of `origin/main`, pushes
3. **force-with-lease** — snapshot takes precedence, no data loss

If all three fail: workflow exits with code 0 (never goes red), snapshot is safe on disk, next cycle retries automatically. A `centinel-git-error` Issue opens with exact diagnosis and manual fix commands. It closes automatically when the next cycle succeeds.

**ES:** Cadena de recuperación de 3 intentos, completamente automática:

1. **Rebase normal** — `git pull --rebase` estándar + push
2. **fetch + hard-reset + recomit** — descarta el conflicto de merge, aplica el snapshot capturado sobre `origin/main`, hace push
3. **force-with-lease** — el snapshot local prevalece, sin pérdida de datos

Si los tres fallan: el workflow termina con código 0 (nunca queda en rojo), el snapshot está seguro en disco, el próximo ciclo reintenta automáticamente. Se abre un Issue `centinel-git-error` con diagnóstico exacto y comandos de resolución manual. Se cierra automáticamente cuando el siguiente ciclo tiene éxito.

### Token expiry / Token expirado (401/403)

**EN:** Detected by the wizard on every hourly cycle. On detection:
1. Sends push notification via ntfy.sh if `CENTINEL_NTFY_TOPIC` is configured
2. Opens `centinel-token-error` Issue with direct link to Classic PAT creation page and direct link to Secrets settings
3. Includes explicit warning about Fine-grained PAT incompatibility (silent failure mode)
4. Closes the Issue automatically when the token is valid again

Deduplication: the system checks for an existing open Issue with the same label before creating a new one. Running the wizard 10 times with an expired token produces exactly 1 open Issue.

**ES:** Detectado por el wizard en cada ciclo horario. Al detectarlo:
1. Envía notificación push vía ntfy.sh si `CENTINEL_NTFY_TOPIC` está configurado
2. Abre Issue `centinel-token-error` con link directo a creación de Classic PAT y link directo a Settings → Secrets
3. Incluye advertencia explícita sobre incompatibilidad de Fine-grained PAT (falla silenciosa)
4. Cierra el Issue automáticamente cuando el token vuelve a ser válido

Deduplicación: el sistema verifica si ya existe un Issue abierto con el mismo label antes de crear uno nuevo. Ejecutar el wizard 10 veces con token expirado produce exactamente 1 Issue abierto.

### GitHub Actions outage / Caída de GitHub Actions

**EN:** If GitHub Actions is unavailable, the system cannot self-recover — it has no execution environment. Three local fallback options are documented in `docs/EMERGENCY-PROCEDURES.md`, each requiring a single command:

```bash
# Option 1 — Docker Compose
docker-compose up -d centinel-engine centinel-watchdog

# Option 2 — Python + system cron
echo "*/15 * * * * cd /path && python -m scripts.download_and_hash" | crontab -

# Option 3 — CLI
poetry run centinel cron --interval 15m
```

Data captured locally syncs to `centinel-data` automatically when Actions recovers.

**ES:** Si GitHub Actions no está disponible, el sistema no puede auto-recuperarse — no tiene entorno de ejecución. Tres alternativas de fallback local están documentadas en `docs/EMERGENCY-PROCEDURES.md`, cada una requiere un solo comando:

```bash
# Opción 1 — Docker Compose
docker-compose up -d centinel-engine centinel-watchdog

# Opción 2 — Python + cron del sistema
echo "*/15 * * * * cd /ruta && python -m scripts.download_and_hash" | crontab -

# Opción 3 — CLI
poetry run centinel cron --interval 15m
```

Los datos capturados localmente se sincronizan a `centinel-data` automáticamente cuando Actions vuelve a funcionar.

---

## Phase 6 — Data publication and resilience / Fase 6 — Publicación de datos y resiliencia

### Automatic publication chain / Cadena de publicación automática

```
capture / captura → centinel-engine/data/
                  → push to / push a centinel-data/snapshots/  (each cycle / cada ciclo)
                  → IPFS pin via Pinata                        (each push / cada push, if PINATA_JWT configured / si PINATA_JWT configurado)
                  → weekly GitHub Release archive              (every Sunday 3am UTC / cada domingo 3am UTC)
```

**EN:** Each layer adds a redundancy tier:
- `centinel-data`: public GitHub repo, forkable by any observer
- IPFS: censorship-resistant, survives GitHub takedown
- GitHub Releases: versioned archive with SHA-256 manifest

**ES:** Cada capa agrega un nivel de redundancia:
- `centinel-data`: repo público de GitHub, cualquier observador puede hacerle fork
- IPFS: resistente a censura, sobrevive una eliminación de GitHub
- GitHub Releases: archivo versionado con manifiesto SHA-256

### Verification without running Centinel / Verificación sin ejecutar Centinel

**EN:** Any third party — NDI, Carter Center, a journalist, a citizen — can verify the data without installing anything:

**ES:** Cualquier tercero — NDI, Carter Center, un periodista, un ciudadano — puede verificar los datos sin instalar nada:

```bash
git clone https://github.com/OPERADOR/centinel-data.git
sha256sum centinel-data/snapshots/TIMESTAMP/results.json
# Compare with / Comparar con:
cat centinel-data/hashes/TIMESTAMP.sha256
```

**EN:** The cryptographic chain is self-contained in the data repository.

**ES:** La cadena criptográfica es autocontenida en el repositorio de datos.

---

## What requires human intervention — complete list / Lo que requiere intervención humana — lista exhaustiva

**EN:** This section is exhaustive. If a situation is not listed here, the system handles it autonomously.

**ES:** Esta sección es exhaustiva. Si una situación no está listada aquí, el sistema la maneja de forma autónoma.

| Situation / Situación | Why it cannot be automated / Por qué no se puede automatizar | Mitigation / Mitigación |
|-----------|---------------------------|------------|
| Creating a GitHub PAT / Crear un PAT de GitHub | GitHub platform security policy — no API exists for this / Política de seguridad de GitHub — no existe API para esto | Wizard opens Issue with direct pre-scoped link / Wizard abre Issue con link directo preconfigurado |
| Renewing an expired token / Renovar un token expirado | Same reason / Misma razón | Wizard detects 401/403, opens Issue with direct link, sends ntfy alert / Wizard detecta 401/403, abre Issue con link directo, envía alerta ntfy |
| Endpoints behind authentication / Endpoints con autenticación | Cannot authenticate without credentials / No puede autenticarse sin credenciales | Manual DevTools discovery + config paste, documented in `SETUP-GUIDE.md` §9 / Descubrimiento manual con DevTools + pegar en config, documentado en `SETUP-GUIDE.md` §9 |
| Endpoint architecture completely redesigned / Arquitectura de endpoints rediseñada completamente | Healer needs the new base URL / El healer necesita la nueva URL base | Operator re-runs wizard with new URL / Operador re-ejecuta el wizard con la nueva URL |
| GitHub Actions fully unavailable / GitHub Actions completamente caído | No execution environment / Sin entorno de ejecución | Three one-command local fallbacks in `EMERGENCY-PROCEDURES.md` / Tres fallbacks locales de un solo comando en `EMERGENCY-PROCEDURES.md` |
| Election night cadence / Cadencia de noche electoral | Cron cannot change itself dynamically / El cron no puede cambiarse solo | `election_mode` input in `workflow_dispatch`, or edit cron and push / Input `election_mode` en `workflow_dispatch`, o editar cron y hacer push |
| P2P federation peer discovery / Descubrimiento de peers P2P | No automatic peer registry exists / No existe registro automático de peers | Operators register peers manually / Operadores registran peers manualmente |
| Public escalation / Escalada pública | Editorial and political judgment required / Requiere juicio editorial y político | Operator decides when and how to communicate findings / Operador decide cuándo y cómo comunicar hallazgos |
| Academic validation / Validación académica | Requires institutional engagement / Requiere compromiso institucional | UPNFM partnership in progress / Alianza con UPNFM en curso (ver `docs/ACADEMIC_ACCESS.md`) |

---

## What this means operationally / Lo que esto significa operacionalmente

**EN:** A civil society organization with no technical staff can:

1. Fork the repository
2. Follow one Issue (create a token, paste it)
3. Run the wizard once with the electoral authority URL
4. Leave it running

The system captures, verifies, and publishes data for the full electoral cycle. If something breaks, it either fixes itself or opens an Issue explaining exactly what to do. The operator does not need to monitor logs, check dashboards, or intervene unless explicitly notified.

This is not a claim about the political impact of the tool. It is a precise statement about operational burden: one person, one afternoon of setup, zero ongoing technical maintenance under normal conditions.

---

**ES:** Una organización de sociedad civil sin personal técnico puede:

1. Hacer fork del repositorio
2. Seguir un Issue (crear un token, pegarlo)
3. Ejecutar el wizard una vez con la URL de la autoridad electoral
4. Dejarlo correr

El sistema captura, verifica y publica datos durante todo el ciclo electoral. Si algo falla, o se repara solo o abre un Issue explicando exactamente qué hacer. El operador no necesita monitorear logs, revisar dashboards ni intervenir a menos que sea notificado explícitamente.

Esto no es una afirmación sobre el impacto político de la herramienta. Es una declaración precisa sobre la carga operativa: una persona, una tarde de setup, cero mantenimiento técnico continuo en condiciones normales.

---

## Current limitations / Limitaciones actuales (honest assessment / evaluación honesta)

**EN:**
- **v0.1 pre-pilot.** Core cryptographic engine is stable and tested (499 passing tests). Field validation with real electoral data is pending (2–3 municipalities, Honduras, target Q3 2026).
- **Authenticated endpoints** are not yet handled automatically. Planned for v0.2 with Playwright credential injection.
- **Fine-grained PAT incompatibility** with GitHub API v3 is a current footgun. The wizard warns explicitly; Classic PAT requirement is documented.
- **Academic validation** is in progress at UPNFM (Honduras). No independent peer review published yet.
- **Federation** is architecturally designed but not field-tested with multiple independent operators.

**ES:**
- **v0.1 pre-piloto.** El núcleo criptográfico es estable y está probado (499 tests pasando). La validación de campo con datos electorales reales está pendiente (2–3 municipios, Honduras, objetivo Q3 2026).
- **Endpoints con autenticación** no están manejados automáticamente aún. Planificado para v0.2 con inyección de credenciales en Playwright.
- **Incompatibilidad de Fine-grained PAT** con la API v3 de GitHub es un problema conocido. El wizard advierte explícitamente; el requisito de Classic PAT está documentado.
- **Validación académica** está en curso en UPNFM (Honduras). No hay revisión por pares publicada aún.
- **Federación** está diseñada arquitectónicamente pero no probada en campo con múltiples operadores independientes.

---

## References / Referencias

- [ARCHITECTURE.md](ARCHITECTURE.md) — cryptographic theorems T1–T4 and system design / teoremas criptográficos T1–T4 y diseño del sistema
- [SECURITY-REVIEW.md](SECURITY-REVIEW.md) — threat model and dependency audit / modelo de amenazas y auditoría de dependencias
- [METHODOLOGY.md](METHODOLOGY.md) — statistical detection methods / métodos de detección estadística
- [EMERGENCY-PROCEDURES.md](EMERGENCY-PROCEDURES.md) — local fallback procedures / procedimientos de fallback local
- [OPERATOR-RUNBOOKS.md](OPERATOR-RUNBOOKS.md) — ntfy.sh setup and auto-Issue reference / configuración de ntfy.sh y referencia de Issues automáticos
- [SETUP-GUIDE.md](SETUP-GUIDE.md) — full wizard documentation including authenticated endpoints / documentación completa del wizard incluyendo endpoints con autenticación
- [DATA-REPOS.md](DATA-REPOS.md) — code/data separation architecture / arquitectura de separación código/datos
- [BUDGET_NARRATIVE.md](BUDGET_NARRATIVE.md) — OTF grant narrative ($95K / 12 months) / narrativa para grant OTF ($95K / 12 meses)
