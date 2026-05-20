# Centinel

[![CI](https://github.com/userf8a2c4/centinel-engine/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/userf8a2c4/centinel-engine/actions/workflows/ci.yml)
[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-2b6cb0.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-2b6cb0.svg)](pyproject.toml)
[![Tests](https://img.shields.io/badge/tests-526%20passing-2f855a.svg)](#estado-de-validación)
[![Security](https://img.shields.io/badge/dependencies-audited-2f855a.svg)](docs/SECURITY-REVIEW.md)

**Infraestructura de auditoría electoral verificable, sin confianza institucional.**

Centinel permite que cualquier ciudadano verifique, de forma independiente y
reproducible, la integridad de los datos electorales publicados por una
autoridad — sin confiar en esa autoridad, sin infraestructura dedicada y sin
coste operativo. Un solo operador puede auditar una elección nacional desde una
computadora portátil.

> *Independent, trustless election-integrity verification. A single operator can
> audit a national election from a laptop — no institutional dependency, no
> dedicated infrastructure, zero operating cost.*

<!-- INSTANCE-STATUS-START -->
---

## Desplegar esta instancia / Deploy this instance

En menos de 10 minutos, sin instalar nada.

**1. Habilitar workflows**
→ Pestaña **[Actions](../../actions)** de tu fork → clic en **"I understand my workflows, go ahead and enable them"**
↳ *GitHub los desactiva en todos los forks por seguridad — es inevitable, son dos segundos.*

**2. Ejecutar el Setup Wizard**
→ **[Actions → Setup Wizard](../../actions/workflows/setup-wizard.yml)** → "Run workflow" → "Run workflow"
↳ *Si el token ya está configurado, el setup termina aquí — salta al paso 4.*
↳ *Si falta el token, el wizard abre un Issue — continúa en el paso 3.*

**3. Crear y conectar el token** *(solo si el wizard abrió un Issue)*
→ Sigue los dos links del Issue: uno abre la página para crear el token, el otro para guardarlo
↳ *Único paso que GitHub no permite automatizar.*
↳ *El Issue tiene un link directo para continuar en el paso 4 cuando termines.*

**4. Re-ejecutar el wizard**
→ Usa el link del Issue, o directamente: **[Setup Wizard](../../actions/workflows/setup-wizard.yml)** → "Run workflow"
↳ *Automático: crea centinel-data, activa GitHub Pages, despliega el panel.*
↳ *Automático: actualiza este README con los links reales, cierra el Issue.*

<details>
<summary>¿El panel no aparece después del setup?</summary>

→ **[Settings → Pages](../../settings/pages)** → Source: **GitHub Actions** → Save

El panel estará disponible en el siguiente push a `main`.
</details>

<!-- INSTANCE-STATUS-END -->

---

## Qué resuelve

Las autoridades electorales publican resultados que la ciudadanía debe aceptar
por confianza. Centinel elimina esa confianza requerida: captura los datos
publicados, los encadena criptográficamente y permite que cualquier tercero
verifique —de forma reproducible y offline— que no fueron alterados después de
su publicación.

| Propiedad | Garantía |
|---|---|
| **Reproducibilidad** | Cadena SHA-256 + raíz de Merkle, verificable offline por cualquiera |
| **Independencia** | El operador no necesita permiso ni cooperación de la autoridad |
| **Resiliencia** | Federación P2P; ningún punto único de fallo o captura |
| **Inmutabilidad temporal** | Anclaje en Bitcoin vía OpenTimestamps, sin coste |
| **Neutralidad** | Reporta hechos verificables. No interpreta intención política |

---

## Principios de diseño

Tres decisiones de diseño son innegociables, porque determinan si la herramienta
sigue siendo útil bajo presión:

- **Coste cero.** Cualquier persona —estudiante, periodista, organización
  civil— puede operarlo sin presupuesto ni autorización.
- **Resiliencia.** Sin punto central que confiscar, bloquear o sobornar.
- **Supervivencia.** El protocolo persiste y se replica aunque su autor
  desaparezca; la licencia y la documentación lo garantizan.

---

## Operación

```bash
poetry install

make wizard                  # Configuración interactiva guiada (recomendado)
centinel panel show          # Estado del sistema
centinel snapshot            # Captura y verificación puntual
centinel cron --interval 30s # Captura continua automática
```

Un operador, una máquina. Sin servidores dedicados, sin coordinación institucional.

---

## Arquitectura de defensa

Centinel aplica defensa en profundidad: cada capa mitiga una clase distinta de
amenaza a la integridad o disponibilidad de la auditoría.

| Capa | Función | Amenaza mitigada |
|---|---|---|
| Atestación distribuida | Confirmación cruzada entre testigos | Testigo único comprometido |
| Cifrado en tránsito | ChaCha20-Poly1305 | Interceptación / MITM |
| Temporización no determinista | Jitter en la captura | Predicción y bloqueo selectivo |
| Auto-regeneración | Resincronización desde réplicas | Manipulación local del estado |
| Interruptor de seguridad | Congelación ante ataque activo | Compromiso en tiempo real |

→ [Especificación de defensas](docs/ANIMAL-DEFENSES-ES.md) ·
[Arquitectura y teoremas T1–T4](docs/ARCHITECTURE.md)

---

## Estado de validación

| Eje | Estado |
|---|---|
| Auditoría criptográfica (teoremas T1–T4) | Completa — verificable en el código |
| Suite de pruebas | 499 / 499 |
| Validación académica independiente | En curso (UPNFM, Honduras) |
| Piloto con datos reales | Pendiente (2–3 municipios) |

Versión **0.1 — pre-piloto.** Núcleo criptográfico estable; pendiente prueba de
campo y dictamen académico independiente.

---

## Arquitectura de Datos

Centinel separa el código (este repositorio) de los datos electorales capturados (centinel-data). Los datos se publican automáticamente en un repositorio independiente en cada captura, garantizando que cualquier auditor pueda verificarlos sin ejecutar el motor.

**Repositorio de datos:** <!-- CENTINEL_DATA_URL -->*(se configura automáticamente al hacer fork)*<!-- /CENTINEL_DATA_URL -->

**Panel de visualización:** <!-- CENTINEL_PAGES_URL -->*(se activa automáticamente al hacer fork)*<!-- /CENTINEL_PAGES_URL -->

El sistema se configura solo: al hacer fork, el wizard detecta qué falta y abre un Issue con instrucciones exactas. Normalmente es un solo paso.

→ [Arquitectura de separación código/datos](docs/DATA-REPOS.md) · [Guía de setup](docs/SETUP-GUIDE.md) · [Panel de visualización](docs/PAGES-GUIDE.md)

---

## Documentación

| Documento | Audiencia |
|---|---|
| [QUICKSTART.md](docs/QUICKSTART.md) | Operadores — primeros pasos |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Revisores técnicos — diseño y teoremas |
| [SECURITY-REVIEW.md](docs/SECURITY-REVIEW.md) | Auditores — modelo de amenazas |
| [METHODOLOGY.md](docs/METHODOLOGY.md) | Académicos — fundamento metodológico |
| [OPERATOR-RUNBOOKS.md](docs/OPERATOR-RUNBOOKS.md) | Operadores — procedimientos |
| [LEGAL-AND-OPERATIONAL-BOUNDARIES.md](docs/LEGAL-AND-OPERATIONAL-BOUNDARIES.md) | Marco legal y límites operativos |

---

## Licencia

**GNU AGPL-3.0.** Software libre, auditable y de redistribución garantizada:
cualquier derivado debe permanecer abierto. Esta licencia es deliberada —
asegura que Centinel no pueda ser capturado, cerrado ni privatizado por ningún
actor, público o privado.

---

**Centinel** · Auditoría electoral como derecho ciudadano, no como privilegio
institucional · `userf8a2c4`

<!-- FORK-GUIDE-START -->
---

## ¿Quieres tu propia instancia? / Want your own instance?

Haz fork de este repositorio — el sistema se despliega solo en menos de 10 minutos.

**1.** Botón **Fork** arriba a la derecha → crea tu copia

**2.** En tu fork: pestaña **[Actions](../../actions)** → **"I understand my workflows, go ahead and enable them"**

**3.** **[Actions → Setup Wizard](../../actions/workflows/setup-wizard.yml)** → "Run workflow" → "Run workflow"

**4.** Sigue el Issue que se abre — tiene links directos para cada acción. El resto es automático.

Tu instancia incluye repositorio de datos público (`centinel-data`), panel de visualización
en GitHub Pages y captura continua verificable — sin servidores, sin costo operativo.

Para más detalles: [docs/SETUP-GUIDE.md](docs/SETUP-GUIDE.md)

<!-- FORK-GUIDE-END -->
