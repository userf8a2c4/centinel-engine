---
Version: 1.0
Date: 2026-05-19
Status: Active
Audience: Operadores / Fork users
---

# Panel de Visualización — Guía

> **ES:** El panel se despliega y mantiene solo. Esta guía es para quienes quieren entender qué ocurre o necesitan configurar opciones avanzadas.
>
> **EN:** The dashboard deploys and maintains itself. This guide is for those who want to understand the process or configure advanced options.

---

## Qué hace el sistema automáticamente / What the system does automatically

Al hacer fork y activar el primer push a `main`, el setup wizard:

1. Detecta si GitHub Pages está habilitado en el repositorio.
2. Si no lo está, intenta activarlo vía GitHub API con el token automático del workflow.
3. Actualiza el `README.md` con el link real al panel (`https://{tu-usuario}.github.io/centinel-engine/`).
4. A partir de ahí, cada push a `main` que modifique `web/**` redespliega el panel automáticamente.

El panel incluye datos de simulación por defecto. Los datos reales se publican cuando el motor corre.

---

## Si el wizard no pudo activar Pages / If the wizard couldn't enable Pages

El wizard abre un Issue en tu repositorio con un link directo. El único paso:

1. Ve a **[Settings → Pages](../../settings/pages)** de tu repositorio
2. En **"Source"**, selecciona: **GitHub Actions**
3. Clic en **Save**

El panel estará disponible en `https://{tu-usuario}.github.io/centinel-engine/` en el siguiente push.

---

## Credenciales de acceso — Supabase (opcional) / Access credentials — Supabase (optional)

El panel funciona completamente sin Supabase. Los datos electorales son públicos y se cargan desde `snapshot.json`.

Supabase solo se usa para el área de login de `/academico/` (sandbox de simulación). Si no lo configuras, esa sección muestra los datos de simulación incluidos directamente, sin autenticación.

Si quieres autenticación real para el sandbox académico:

<details>
<summary>Configurar Supabase (3 pasos)</summary>

**Paso 1** — Crea un proyecto gratuito:
→ [https://supabase.com](https://supabase.com) → New project

**Paso 2** — Obtén las credenciales:
→ En tu proyecto Supabase: **Settings → API**
- Copia **Project URL** (`https://xxx.supabase.co`)
- Copia **anon/public key** (empieza con `eyJ...`)

**Paso 3** — Guárdalas en el repositorio:
→ [Settings → Secrets → Actions → New secret](../../settings/secrets/actions/new)

| Name | Value |
|------|-------|
| `SUPABASE_URL` | La Project URL copiada |
| `SUPABASE_ANON_KEY` | La anon key copiada |

Luego actualiza `web/config.js` con esos valores y haz push. El workflow redespliega automáticamente.

</details>

---

## Dominio personalizado (opcional) / Custom domain (optional)

<details>
<summary>Configurar dominio propio</summary>

1. Ve a **Settings → Pages** de tu repositorio
2. En **"Custom domain"**, escribe tu dominio (ej. `centinel.tudominio.org`)
3. En tu proveedor DNS, añade un registro CNAME: `centinel.tudominio.org → {tu-usuario}.github.io`
4. Activa **"Enforce HTTPS"** una vez que el dominio esté verificado

El wizard actualizará el placeholder `CENTINEL_PAGES_URL` en README.md con el dominio personalizado si detecta que está configurado.

</details>

---

## ¿Qué contiene el panel? / What does the dashboard contain?

| Sección | Descripción |
|---------|-------------|
| **Inicio** (`/`) | Hub central — acceso al panel y al sandbox |
| **Panel** (`/panel/`) | Dashboard electoral: KPIs, mapa, análisis de Benford, detectores forenses |
| **Académico** (`/academico/`) | Sandbox con 576 snapshots de simulación para análisis forense |
| **Replay** (`/replay/`) | Reproducción cronológica de capturas |
| **Verificador** (`/verifier/`) | Verificación de integridad de snapshots individuales |
| **Reportes** (`/reports/`) | Reportes HTML generados automáticamente |

Los datos se regeneran en cada push: calibración, series temporales, snapshots.

---

## Referencias / References

- [DATA-REPOS.md](DATA-REPOS.md) — Separación código/datos
- [SETUP-GUIDE.md](SETUP-GUIDE.md) — Setup wizard completo
- [RESILIENCE.md](RESILIENCE.md) — Resiliencia y federación
