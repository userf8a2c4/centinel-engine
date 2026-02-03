# [ES] Reordenamiento de documentación de resiliencia – Circuit breaker y reintentos 2026

  /dev: Notas del parche: Versión: v0.0.43 (commit por definir)



# [ES] Notas de Parche – C.E.N.T.I.N.E.L.

**Versión:** v0.0.43  
**Fecha:** 03-feb-2026  
**Autor:** userf8a2c4

### Resumen
Se reordena la documentación de resiliencia para hacerla más accesible y accionable: el README queda más limpio, y los detalles de circuit breaker, low-profile y reintentos pasan a una guía dedicada con enlaces directos a archivos de configuración y código.

### Cambios principales
- **Mejora:** Guía de resiliencia dedicada (`docs/resilience.md`) con explicación completa de circuit breaker, low-profile y reintentos
  - **Por qué:** En 0.0.42 la información vivía dispersa en el README; era útil pero difícil de expandir sin sobrecargar la portada
  - **Impacto:** La lectura es más clara, se puede profundizar por tema y la documentación ahora escala sin perder visibilidad

- **Mejora:** Enlaces nuevos en el README hacia la guía de resiliencia y sus secciones clave
  - **Por qué:** Mantener el README como mapa rápido sin perder acceso a la información crítica
  - **Impacto:** Onboarding más rápido; cualquier operador llega a la documentación correcta en un clic

- **Mejora:** Referencias directas a `command_center/config.yaml`, `retry_config.yaml` y los flujos de descarga
  - **Por qué:** Un sistema resiliente es inútil si no se entiende dónde se ajusta; los puntos de configuración debían quedar explícitos
  - **Impacto:** Menos ambigüedad al ajustar el pipeline y menor riesgo de malinterpretar el comportamiento ante fallos

### Cambios técnicos
- Nuevo documento `docs/resilience.md` con secciones, enlaces y ejemplo de uso de `RETRY_CONFIG_PATH`
- README ajustado para enlazar a la guía de resiliencia y al apartado de circuit breaker

### Notas adicionales
- La guía se diseñó para crecer con nuevos escenarios de falla sin volver a inflar el README
- Se recomienda revisar la configuración de resiliencia antes de cada ciclo electoral

**Objetivo de C.E.N.T.I.N.E.L.:** Monitoreo independiente, neutral y transparente de datos electorales públicos. Solo números. Solo hechos. Código abierto AGPL-3.0 para el pueblo hondureño.


-------------


# [EN] Patch Notes – C.E.N.T.I.N.E.L.

**Version:** v0.0.43  
**Date:** February 03, 2026  
**Author:** userf8a2c4

### Summary
Resilience documentation has been reorganized to make it easier to follow: the README stays lightweight, while circuit breaker, low-profile, and retry details live in a focused guide with direct links to config and code.

### Main Changes
- **Improvement:** Dedicated resilience guide (`docs/resilience.md`) explaining circuit breaker, low-profile, and retry behavior
  - **Why:** In 0.0.42 the details were embedded in the README, which was useful but hard to expand without clutter
  - **Impact:** Cleaner navigation and a scalable home for operational knowledge

- **Improvement:** New README links pointing to the resilience guide and its key section
  - **Why:** Keep the README as a quick map without losing access to critical details
  - **Impact:** Faster onboarding and immediate access to the right reference

- **Improvement:** Explicit references to `command_center/config.yaml`, `retry_config.yaml`, and download flows
  - **Why:** Resilience only works if operators know exactly where to tune it
  - **Impact:** Less ambiguity when adjusting pipeline behavior and fewer misconfigurations under failure conditions

### Technical Changes
- Added `docs/resilience.md` with structured sections and a `RETRY_CONFIG_PATH` usage example
- Updated README to link directly to resilience documentation and circuit breaker guidance

### Additional Notes
- The guide is structured to grow as new failure scenarios are documented
- Reviewing resilience settings before each election cycle is recommended

**C.E.N.T.I.N.E.L. Goal:** Independent, neutral and transparent monitoring of public electoral data. Only numbers. Only facts. AGPL-3.0 open-source for the Honduran people.
