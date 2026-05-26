---
Version: 2.0
Date: 2026-05-19
Status: Active
Audience: Desarrolladores · Operadores avanzados
---

# Setup — Referencia técnica completa

> **ES:** Documentación exhaustiva del sistema de configuración automática.
> Para el despliegue rápido, sigue la guía en el README de tu fork.
>
> **EN:** Exhaustive documentation of the automatic configuration system.
> For quick deployment, follow the guide in your fork's README.

---

## 1. Cómo funciona el wizard

El workflow `.github/workflows/setup-wizard.yml` es el núcleo del sistema de autoconfiguración.

### Triggers

```
push: branches: [main]          → corre en cada push al branch principal
workflow_dispatch               → el usuario lo ejecuta manualmente desde Actions
schedule: '0 * * * *'          → corre cada hora si hay un Issue centinel-setup abierto
```

El cron horario existe para un escenario específico: el usuario añadió el secret `DATA_REPO_TOKEN` pero olvidó re-ejecutar el wizard. En lugar de quedarse bloqueado, el sistema lo detecta solo en el siguiente ciclo horario.

### Árbol de decisiones

```
Wizard arranca
       │
       ▼
¿DATA_REPO_TOKEN configurado?
       │
  NO ──┤── ¿Ya existe un Issue centinel-setup abierto?
       │         │
       │    SÍ ──┘── no hace nada (evita duplicar Issues)
       │    NO ──┬── abre Issue con instrucciones exactas y links directos
       │         └── detiene el ciclo hasta el próximo trigger
       │
  SÍ ──┤
       ▼
¿centinel-data existe?
       │
  NO ──┤── crea el repo centinel-data via GitHub API
       │── inicializa estructura de directorios
       │── push ipfs-manifest.json y workflows (ipfs-pin, auto-release)
       │
  SÍ ──┤
       ▼
Estado: ready
  ├── intenta activar GitHub Pages via API
  ├── actualiza CENTINEL_DATA_URL y CENTINEL_PAGES_URL en README
  ├── en forks: actualiza badges de CI, transforma INSTANCE-STATUS a estado vivo
  ├── dispara pages.yml para despliegue inmediato del panel
  └── cierra Issue centinel-setup con URLs finales
```

### Estados del wizard

| Estado | Causa | Acción |
|--------|-------|--------|
| `needs_token` | `DATA_REPO_TOKEN` ausente | Abre Issue con instrucciones |
| `needs_repo` | Token OK, centinel-data no existe | Crea repo + inicializa + continúa a ready |
| `ready` | Todo configurado | Finaliza README, despliega panel, cierra Issues |
| `error_4xx` | Token con permisos insuficientes | No abre Issue (evita spam) — ver Troubleshooting |

---

## 2. DATA_REPO_TOKEN

El único secret necesario para el modo distribuido. Sin él, los datos permanecen en centinel-engine y el sistema funciona igual — solo sin repositorio público separado.

### Por qué GITHUB_TOKEN no es suficiente

`GITHUB_TOKEN` es el token automático que GitHub genera para cada ejecución de workflow. Tiene permisos únicamente sobre el repositorio actual. No puede:

- Crear repositorios en la cuenta del usuario
- Escribir en repositorios externos (`centinel-data`)
- Activar Pages en otro repositorio

Para estas operaciones se necesita un Personal Access Token (PAT) del propietario de la cuenta.

### Classic PAT vs Fine-grained PAT

**Usa siempre Classic PAT.** Esta es la causa de error más frecuente en el setup.

| | Classic PAT | Fine-grained PAT |
|--|-------------|-----------------|
| Crear repositorios via API v3 | ✅ | ❌ |
| Escribir en repos externos | ✅ | ✅ (con config adicional) |
| Compatible con el wizard | ✅ | ❌ |

Los Fine-grained PAT son más seguros en general, pero la API v3 de GitHub que usa el wizard para crear repositorios no los soporta. El wizard falla silenciosamente con un Fine-grained token.

**Scope requerido:** `repo` (acceso completo a repositorios privados y públicos).

### Cómo crear el token

→ **[github.com/settings/tokens/new?scopes=repo](https://github.com/settings/tokens/new?scopes=repo)**

1. **Note:** `centinel-data` (o cualquier nombre descriptivo)
2. **Expiration:** 90 días o "No expiration" (ver sección de renovación)
3. **Select scopes:** confirma que `repo` está marcado
4. Clic en **"Generate token"**
5. **Copia el token** — solo se muestra una vez

### Qué puede hacer el token / qué no puede hacer

**Puede:**
- Crear `centinel-data` en tu cuenta
- Escribir archivos en `centinel-data`
- Verificar si `centinel-data` existe
- Activar GitHub Pages en `centinel-data`

**No puede:**
- Acceder a repositorios de otras cuentas
- Modificar configuración de tu cuenta
- Leer repositorios privados de otros usuarios
- Nada más allá del scope `repo`

### Renovación del token

Cuando el token expira, el wizard falla en silencio (estado `error_4xx`). El sistema no abre un Issue automáticamente porque no puede distinguir un token expirado de uno con permisos insuficientes sin exponer información sensible.

Para renovar:
1. Crea un nuevo Classic PAT con scope `repo`
2. Ve a **[Settings → Secrets → DATA_REPO_TOKEN](../../settings/secrets/actions)** → "Update"
3. Pega el nuevo token → Save
4. El próximo cron horario o push reanuda el funcionamiento normal

---

## 3. centinel-data — estructura y flujo de datos

### Qué escribe cada workflow

| Workflow | Fuente en centinel-engine | Destino en centinel-data |
|----------|--------------------------|--------------------------|
| `audit.yml` | `data/`, `hashes/`, `diffs/`, `reports/` | `snapshots/`, `hashes/`, `diffs/`, `reports/` |
| `scheduler.yml` | `data/` | `snapshots/` |
| `pipeline.yml` | `web/data/snapshot.json` | `snapshots/latest/` |
| `report_publish.yml` | `web/reports/` | `reports/` |
| `emergency-publish.yml` | `web/data/snapshot.json` | `snapshots/emergency/` |
| `observer_pack.yml` | `web/downloads/` | `observer-packs/` |

Todos los workflows tienen degradación graceful: si `DATA_REPO_TOKEN` no está configurado, los datos se quedan en centinel-engine sin error.

### Schema de ipfs-manifest.json

```json
{
  "schema_version": "1.0",
  "last_updated": "2026-05-19T03:00:00Z",
  "snapshots": [
    {
      "cid": "QmXyz...",
      "timestamp": "2026-05-19T03:00:00Z"
    }
  ]
}
```

### Verificación de integridad desde cero

```bash
git clone https://github.com/TU_USUARIO/centinel-data
cd centinel-data
sha256sum snapshots/latest/snapshot.json
# compara con el hash en hashes/latest.sha256
```

### Recuperación si centinel-data se borra accidentalmente

El wizard lo detecta en el próximo ciclo (push o cron) y recrea el repositorio automáticamente con la estructura inicial. Los datos históricos se recuperan desde el historial de `centinel-engine` y los releases de GitHub.

---

## 4. GitHub Pages

### Activación automática

El wizard intenta activar Pages via la GitHub API usando `GITHUB_TOKEN` con permiso `pages: write`:

```
POST /repos/{owner}/{repo}/pages
{"build_type": "workflow"}
```

Esto funciona en la mayoría de casos. Cuando no funciona (ver abajo), el wizard abre un Issue `centinel-pages` con un link directo a Settings → Pages.

### Cuándo falla la activación automática

La API de GitHub puede rechazar la activación automática en:
- Repositorios recién creados (primeras horas)
- Cuentas con restricciones de organización
- Repositorios con configuración de Pages preexistente conflictiva

En estos casos el wizard abre el Issue `centinel-pages` con instrucciones exactas.

### Activación manual

→ **[Settings → Pages](../../settings/pages)**
- **Source:** GitHub Actions
- Clic en **Save**

El panel estará disponible en el siguiente push a `main` que toque `web/**`.

### URL predecible

```
https://{owner}.github.io/centinel-engine/
```

Donde `{owner}` es el nombre de usuario de GitHub del propietario del fork. El wizard actualiza el placeholder `CENTINEL_PAGES_URL` en el README con esta URL exacta.

### Despacho automático al terminar el wizard

Al completar el setup, el wizard hace un `workflow_dispatch` sobre `pages.yml` para que el panel se despliegue sin necesidad de un push manual:

```bash
POST /repos/{owner}/{repo}/actions/workflows/pages.yml/dispatches
{"ref": "main"}
```

---

## 5. IPFS — anclaje descentralizado (opcional)

### Qué garantiza IPFS que GitHub no puede garantizar

GitHub puede eliminar, censurar o bloquear repositorios. IPFS ancla los datos en una red descentralizada donde ningún actor individual puede eliminarlos. Para un sistema de auditoría electoral que puede operar bajo presión política, esta capa adicional es relevante.

### Setup con Pinata

<details>
<summary>Activar anclaje IPFS (3 pasos)</summary>

**Paso 1** — Cuenta gratuita en Pinata:
→ [pinata.cloud](https://pinata.cloud) → Sign up (plan gratuito: 1 GB de pins)

**Paso 2** — Obtener el JWT:
→ En Pinata: API Keys → New Key → Admin → Generate → **copia el JWT**

**Paso 3** — Guardar en centinel-data:
→ **[centinel-data → Settings → Secrets → New](https://github.com/TU_USUARIO/centinel-data/settings/secrets/actions/new)**
- Name: `PINATA_JWT`
- Value: el JWT copiado

A partir del próximo push a centinel-data, cada actualización queda anclada en IPFS y el CID se registra en `ipfs-manifest.json`.

</details>

### Recuperación si GitHub cae

```bash
# Con IPFS CLI instalado:
ipfs get QmCID_DEL_SNAPSHOT

# Via gateways públicos (sin instalar nada):
https://ipfs.io/ipfs/QmCID_DEL_SNAPSHOT
https://cloudflare-ipfs.com/ipfs/QmCID_DEL_SNAPSHOT
https://gateway.pinata.cloud/ipfs/QmCID_DEL_SNAPSHOT
```

Los CIDs están registrados en `centinel-data/ipfs-manifest.json`.

---

## 6. Secrets — referencia completa

| Secret | Repositorio | Función | Requerido | Cómo obtener |
|--------|-------------|---------|-----------|--------------|
| `DATA_REPO_TOKEN` | centinel-engine | Crear y escribir en centinel-data | Opcional* | Classic PAT scope `repo` — ver sección 2 |
| `PINATA_JWT` | centinel-data | Anclaje IPFS en cada push | Opcional | Cuenta Pinata → API Keys → JWT |

*Sin `DATA_REPO_TOKEN` el sistema funciona en modo local: datos en centinel-engine, sin repositorio público separado.

---

## 7. Troubleshooting

### El wizard corrió pero no abrió ningún Issue y centinel-data no existe

**Causa:** los workflows no están habilitados en el fork.

GitHub desactiva los workflows en todos los forks por defecto. El wizard no puede correr hasta que el usuario los habilite manualmente.

**Solución:**
→ **[Actions](../../actions)** → "I understand my workflows, go ahead and enable them"

Luego ejecuta el wizard manualmente: **[Setup Wizard](../../actions/workflows/setup-wizard.yml)** → "Run workflow".

---

### centinel-data no se creó aunque DATA_REPO_TOKEN existe y el wizard corrió sin errores visibles

**Causa más frecuente: usaste un Fine-grained PAT.**

Este es el error de setup más común. Los Fine-grained PAT parecen funcionar pero la API v3 de GitHub que usa el wizard para crear repositorios no los soporta. El wizard falla silenciosamente — no hay mensaje de error visible en el log.

**Cómo confirmar:** ve a Actions → Setup Wizard → el run más reciente → revisa el step "Create centinel-data repo automatically". Si ves un error 4xx en la llamada curl, es el tipo de token.

**Solución:** crea un **Classic PAT** con scope `repo`.
→ **[github.com/settings/tokens/new?scopes=repo](https://github.com/settings/tokens/new?scopes=repo)**

Después de crearlo, actualiza el secret `DATA_REPO_TOKEN` y re-ejecuta el wizard.

---

### Pages no se activó y no apareció ningún Issue centinel-pages

**Causa:** la activación via API funcionó (no hubo error) pero GitHub tarda en propagar el cambio.

**Solución:** espera 2–3 minutos y visita `https://TU_USUARIO.github.io/centinel-engine/`. Si sigue sin aparecer:

→ **[Settings → Pages](../../settings/pages)** → Source: **GitHub Actions** → Save

El panel estará disponible en el siguiente push a `main`.

---

### El wizard muestra error 401 o 403

**Causa:** el token `DATA_REPO_TOKEN` expiró o fue revocado.

**Solución:**
1. Crea un nuevo Classic PAT con scope `repo`
2. **[Settings → Secrets → DATA_REPO_TOKEN](../../settings/secrets/actions)** → "Update" → pega el nuevo token
3. Re-ejecuta el wizard o espera el cron horario

---

### El panel despliega pero muestra datos de otro repositorio o datos de ejemplo

**Causa:** `pages.yml` está usando datos del branch equivocado o los scripts de calibración fallaron.

**Solución:** ejecuta `pages.yml` manualmente desde Actions → el step de calibración regenera los datos desde cero. Si el error persiste, revisa el log del step "Regenerate HND-2025 calibration data" — el error ahí es descriptivo.

---

### Fork de un fork: los badges de CI no apuntan a mi repo

**Causa:** el wizard actualiza los badges reemplazando las referencias al repo original hardcodeado (`userf8a2c4/centinel-engine`). Si forkeaste desde un fork que ya completó el setup, las referencias apuntan al fork intermedio, no al original, y el wizard no las detecta.

**Solución:** en tu fork, edita manualmente las primeras líneas del README y reemplaza el owner en los badges por tu nombre de usuario de GitHub. Es un cambio de una línea.

---

## 8. Escenarios avanzados

### Operación sin GitHub Actions (modo local puro)

El motor puede correr completamente en local sin ningún workflow de GitHub:

```bash
poetry install
make wizard          # configuración interactiva
centinel snapshot    # captura puntual
centinel cron --interval 30s  # captura continua
```

En modo local, los datos se acumulan en `data/`, `hashes/`, `diffs/` dentro del repo. No se publican automáticamente en ningún repositorio externo.

### Fork de un fork

El sistema funciona en cualquier nivel de la cadena. Lo que se hereda automáticamente:
- Toda la lógica del wizard
- La sección `FORK-GUIDE` con instrucciones para el siguiente fork
- Los workflows de captura y publicación

Lo que hay que reconfigurar en cada fork:
- `DATA_REPO_TOKEN` (cada operador necesita su propio token)
- `PINATA_JWT` (opcional, si se quiere IPFS propio)

### Múltiples instancias del mismo operador

Cada fork es una instancia independiente. Para monitorear múltiples elecciones simultáneamente, forkea el repo una vez por elección y configura cada fork con su propio `DATA_REPO_TOKEN` apuntando a su propio `centinel-data`.

### Dominio personalizado para el panel

→ **[Settings → Pages](../../settings/pages)** → Custom domain → escribe tu dominio

En tu DNS, añade un registro CNAME:
```
panel.tudominio.org → TU_USUARIO.github.io
```

Activa "Enforce HTTPS" una vez verificado el dominio.

### DATA_REPO_TOKEN en una organización de GitHub

Si el repositorio está en una organización, el token debe pertenecer a un miembro con permisos de escritura en la organización. El scope `repo` sigue siendo el requerido. Si la organización tiene SSO activado, el token necesita además autorización SSO explícita desde la pantalla de configuración del PAT.

---

## 9. Endpoints con autenticación

Algunas autoridades electorales protegen sus endpoints con autenticación (sesión, Basic Auth, o tokens de sesión). Este escenario es detectable pero no resoluble en su totalidad de forma automatizada sin credenciales.

### Síntoma

- El healer ejecuta correctamente y Playwright carga la web
- La web muestra datos pero el healer retorna 0 endpoints válidos
- Las peticiones capturadas por Playwright devuelven HTTP 401 o 302 (redirect a login)
- El log muestra: `0 candidates after validation`

### Diagnóstico manual

1. Abre la URL en un browser con DevTools → pestaña Network
2. Filtra por XHR/Fetch
3. Navega a la sección de resultados — DevTools mostrará los endpoints reales
4. Observa si alguna petición incluye cabeceras `Authorization`, `Cookie` o similar

### Solución

**Opción A — Endpoint manual (recomendada para elecciones en curso):**

Si identificaste el endpoint en DevTools, agrégalo directamente al config:

```bash
# config/prod/endpoints.yaml
cne:
  presidential_endpoints:
    - https://resultados.cne.hn/api/v1/resultados?nivel=nacional
    - https://resultados.cne.hn/api/v1/resultados?nivel=departamental&depto=01
    # ... resto de departamentos
```

**Opción B — Credenciales como secrets:**

Si la API acepta usuario/contraseña:

1. Añade los secrets en **Settings → Secrets → Actions**:
   - `CNE_USERNAME` — usuario o email
   - `CNE_PASSWORD` — contraseña

2. El healer Playwright los usará automáticamente si están presentes (soporte completo en v0.2).

> **Nota:** Los endpoints descubiertos con sesión autenticada pueden cambiar con cada login. Si el sistema pierde la sesión, el healer fallará silenciosamente hasta la próxima re-autenticación.

### Recursos

- [OPERATOR-RUNBOOKS.md](OPERATOR-RUNBOOKS.md) — Sección "Descubrimiento manual de endpoints"
- [EMERGENCY-PROCEDURES.md](EMERGENCY-PROCEDURES.md) — Procedimientos para noche electoral

---

## Referencias

- [DATA-REPOS.md](DATA-REPOS.md) — Arquitectura de separación código/datos
- [IPFS-RESILIENCE.md](IPFS-RESILIENCE.md) — Resiliencia IPFS en detalle
- [PAGES-GUIDE.md](PAGES-GUIDE.md) — Panel de visualización y credenciales opcionales
- [QUICKSTART.md](QUICKSTART.md) — Primeros pasos para operadores
