# Governance Document — Centinel Engine
## Documento de Gobernanza

**Version:** 1.1 | **Date:** 2026-05-18 | **Status:** Active

---

## Español

### Propósito

Este documento define quién controla el proyecto Centinel Engine, cómo se toman las
decisiones, la política de conflicto de intereses, y cómo se incorporan nuevos
contribuyentes. Es un requisito estándar de organizaciones como NDI, Carter Center y EU EOM
para cualquier solicitud de grant.

---

### Estructura de Decisión

#### Rol de Mantenedor Principal

El mantenedor principal es responsable de:

- Decisiones de arquitectura técnica del núcleo criptográfico y estadístico
- Aprobación de contribuciones que afecten la cadena de hashes o las reglas estadísticas
- Comunicación con organizaciones de observación electoral y partners académicos
- Gestión de divulgación responsable de vulnerabilidades de seguridad

**Criterio de selección:** Competencia técnica demostrable en criptografía aplicada,
estadística electoral y sistemas distribuidos. Sin afiliación a partido político o
candidatura electoral activa en los países donde el sistema opera.

#### Comité Técnico Asesor (en formación)

Compuesto por representantes de:

- **UPNFM** (Universidad Pedagógica Nacional Francisco Morazán) — revisión de métodos
  estadísticos
- **Observadores independientes** — uso operativo del sistema en contexto electoral
- **Comunidad open source** — revisión de código y seguridad

---

### Política de Conflicto de Intereses

#### Prohibiciones absolutas

Los mantenedores y contribuyentes del proyecto NO pueden:

1. **Usar Centinel Engine para favorecer a un candidato o partido específico**
   — el sistema es 100% agnóstico a candidatos y partidos
2. **Integrar nombres de candidatos reales en código, tests o documentación**
   — usar siempre placeholders neutros ("Candidato A", "Partido X")
3. **Compartir datos electorales privados** obtenidos para validación técnica con terceros
   sin autorización escrita explícita
4. **Recibir remuneración de partidos políticos o candidatos** simultáneamente a trabajar
   en el proyecto
5. **Publicar interpretaciones políticas** de los resultados del sistema sin coordinación
   con la entidad legal responsable

#### Declaración requerida

Todo mantenedor y contribuyente con acceso al repositorio principal debe declarar:

- Si tiene afiliación activa con algún partido político o candidato en los países donde
  opera el sistema
- Si tiene relación contractual con el CNE u órgano electoral equivalente
- Cualquier conflicto potencial que pudiera afectar la imparcialidad del sistema

#### Proceso de divulgación

Si un mantenedor identifica un conflicto de intereses:
1. Declararlo inmediatamente al mantenedor principal o al comité técnico
2. Abstenerse de tomar decisiones sobre componentes relacionados con el conflicto
3. El comité técnico puede solicitar inhibición temporal del rol

---

### Proceso de Contribución

#### Para contribuciones de código

1. Fork del repositorio → rama de feature → Pull Request
2. El PR debe pasar CI (tests, linting, type checking)
3. Revisión por al menos 1 mantenedor
4. Para cambios en reglas estadísticas o núcleo criptográfico: revisión por UPNFM
   o revisor técnico independiente

#### Para contribuciones de documentación

1. Las traducciones y mejoras de documentación son bienvenidas sin revisión técnica formal
2. Los cambios en METHODOLOGY.md, THEORY_OF_CHANGE.md e INCIDENT_RESPONSE.md requieren
   revisión del mantenedor principal

#### Para reporte de seguridad

Ver `SECURITY.md`. Nunca publicar vulnerabilidades sin coordinación con el equipo.

---

### Política de Divulgación Responsable

Si el sistema detecta una anomalía significativa durante un proceso electoral real:

1. El operador preserva evidencia y notifica al coordinador técnico
2. El coordinador técnico verifica la anomalía técnicamente
3. **No se publican resultados públicos sin validación técnica independiente**
4. La misión de observación presente (OEA, UE, NDI) es notificada antes de cualquier
   comunicación pública
5. Los medios de comunicación solo son contactados con coordinación de la entidad legal

Esta política protege la credibilidad del sistema: una falsa alarma publicada prematuramente
daña tanto al proyecto como al proceso electoral que se intenta proteger.

---

### Licenciamiento y Uso

**Licencia principal:** AGPL-3.0

Todo código del proyecto está bajo AGPL-3.0, lo que requiere que cualquier modificación
sea publicada como código abierto. Esto garantiza que no puede existir una versión privada
del sistema con capacidades adicionales o reducidas sin transparencia.

**Uso gubernamental:** Los organismos electorales gubernamentales que deseen adaptar el
sistema pueden solicitar una licencia especial que permita modificaciones internas sin
obligación de publicación, condicionada a:
- Que las modificaciones no reduzcan las capacidades de verificación pública
- Que el código original permanezca accesible
- Que se notifique al mantenedor principal sobre el deployment

---

### Entidad Legal

Para efectos de recepción de grants y contratos, el proyecto opera bajo la supervisión
académica de:

**Universidad Pedagógica Nacional Francisco Morazán (UPNFM)**
- País: Honduras
- Contacto institucional: En coordinación con el equipo del proyecto
- Rol: Fiscal sponsor para grants internacionales, revisión académica de métodos

*(Esta sección se actualizará una vez que la relación formal con UPNFM esté establecida)*

---

### Historial de Revisiones

| Versión | Fecha | Cambios |
|---------|-------|---------|
| 1.0 | 2025-05-17 | Documento inicial |

---

## English

### Purpose

This document defines who controls the Centinel Engine project, how decisions are made,
the conflict of interest policy, and how new contributors are incorporated. It is a
standard requirement for organizations such as NDI, Carter Center, and EU EOM for any
grant application.

---

### Conflict of Interest Policy

**Absolute prohibitions** — maintainers and contributors may NOT:

1. Use Centinel Engine to favor a specific candidate or party
2. Include real candidate names in code, tests, or documentation
3. Share private electoral data obtained for technical validation with third parties
4. Receive remuneration from political parties or candidates while working on the project
5. Publish political interpretations of system results without coordination with the legal entity

**Required disclosure:** All maintainers with access to the main repository must declare
any active affiliation with political parties or candidates in countries where the system
operates.

---

### Responsible Disclosure Policy

If the system detects a significant anomaly during a real electoral process:

1. The operator preserves evidence and notifies the technical coordinator
2. The technical coordinator verifies the anomaly independently
3. **No public results are published without independent technical validation**
4. Present observation missions (OAS, EU, NDI) are notified before any public communication
5. Media are only contacted with coordination of the legal entity

---

### Licensing

**Primary license:** AGPL-3.0

All project code is under AGPL-3.0, requiring any modifications to be published as open
source. This ensures no private version of the system can exist with additional or reduced
capabilities without transparency.

---

*Last revision: 2025-05-17*
*See also: [THEORY_OF_CHANGE.md](THEORY_OF_CHANGE.md) | CODE_OF_CONDUCT.md | SECURITY.md*
