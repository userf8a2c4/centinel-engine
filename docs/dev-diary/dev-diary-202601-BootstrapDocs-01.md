# Dev Diary - 202601 - BootstrapDocs - 01

**Fecha aproximada / Approximate date:** 22-ene-2026 / January 22, 2026  
**Fase / Phase:** Inicio simplificado y documentación / Simplified bootstrap & documentation  
**Versión interna / Internal version:** v0.0.41 (dev-v5)  
**Rama / Branch:** dev-v5  
**Autor / Author:** userf8a2c4

**Resumen de avances / Summary of progress:**
- Helper de bootstrap y Makefile para estandarizar el arranque.  
  Bootstrap helper and Makefile to standardize startup.
- Actualización de README, QUICKSTART y docs de scripts.  
  Updates to README, QUICKSTART, and scripts documentation.
- Manual operativo ajustado con notas de despliegue.  
  Operational manual updated with deployment notes.

---
# [ES] Inicio simplificado dev-v5 – Bootstrap y documentación 2026

  /dev: Notas del parche: Versión: v0.0.41_-_dev-v5 (commit c5f6585)



# [ES] Notas de Parche – C.E.N.T.I.N.E.L.

**Versión:** v0.0.41_-_dev-v5  
**Fecha:** 22-ene-2026  
**Autor:** userf8a2c4

### Resumen
Se agrega un flujo de inicio más claro con helper de bootstrap, Makefile y documentación ajustada para arrancar rápido en dev-v5.

### Cambios principales
- **Mejora:** Nuevo helper de arranque (`scripts/bootstrap.py`) y Makefile para comandos comunes  
  - **Por qué:** Reducir fricción al configurar el entorno por primera vez y estandarizar pasos de inicio  
  - **Impacto:** Onboarding más rápido, menos errores y guía consistente para devs

- **Mejora:** Actualización de README, QUICKSTART y documentación de scripts  
  - **Por qué:** Alinear la documentación con el flujo real de arranque y aclarar dependencias  
  - **Impacto:** Menos ambigüedad para ejecutar el sistema localmente

- **Mejora:** Manual actualizado con notas operativas  
  - **Por qué:** Registrar pasos importantes y contexto para operación inicial  
  - **Impacto:** Referencia más clara para quienes administran despliegues

### Cambios técnicos
- Nuevos comandos de automatización en `Makefile`
- Script de bootstrap para preparar dependencias y configuración base
- Ajustes en `README.md`, `QUICKSTART.md`, `docs/manual.md` y `scripts/README.md`

### Notas adicionales
- Se recomienda ejecutar el flujo de bootstrap antes del primer arranque para evitar configuraciones incompletas
- Documentación actualizada para reflejar la licencia real del proyecto

**Objetivo de C.E.N.T.I.N.E.L.:** Monitoreo independiente, neutral y transparente de datos electorales públicos. Solo números. Solo hechos. Código abierto AGPL-3.0 para el pueblo hondureño.


-------------


# [EN] Patch Notes – C.E.N.T.I.N.E.L.

**Version:** v0.0.41_-_dev-v5  
**Date:** January 22, 2026  
**Author:** userf8a2c4

### Summary
Adds a clearer startup flow with a bootstrap helper, Makefile, and docs updates to speed up dev-v5 onboarding.

### Main Changes
- **Improvement:** New bootstrap helper (`scripts/bootstrap.py`) and Makefile for common commands  
  - **Why:** Reduce setup friction and standardize startup steps  
  - **Impact:** Faster onboarding, fewer errors, consistent guidance for devs

- **Improvement:** Updates to README, QUICKSTART, and scripts documentation  
  - **Why:** Align documentation with the actual startup flow and clarify dependencies  
  - **Impact:** Less ambiguity when running the system locally

- **Improvement:** Manual updated with operational notes  
  - **Why:** Capture important steps and context for initial operations  
  - **Impact:** Clearer reference for operators

### Technical Changes
- New automation commands in `Makefile`
- Bootstrap script to prepare dependencies and base configuration
- Updates to `README.md`, `QUICKSTART.md`, `docs/manual.md`, and `scripts/README.md`

### Additional Notes
- It is recommended to run the bootstrap flow before first startup to avoid incomplete setup
- Documentation updated to reflect the project’s real license

**C.E.N.T.I.N.E.L. Goal:** Independent, neutral and transparent monitoring of public electoral data. Only numbers. Only facts. AGPL-3.0 open-source for the Honduran people.
