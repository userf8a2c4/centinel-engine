# Dev Diary - 202601 - RulesModularization - 01

**Fecha aproximada / Approximate date:** 11-ene-2026 / January 11, 2026  
**Fase / Phase:** Modularización de reglas y reglas forenses / Rule modularization & forensic rules  
**Versión interna / Internal version:** v0.0.31  
**Rama / Branch:** main (dev-6)  
**Autor / Author:** userf8a2c4

**Resumen de avances / Summary of progress:**
- Modularización completa de reglas de análisis en `centinel/core/rules/`.  
  Full modularization of analysis rules under `centinel/core/rules/`.
- Nuevas reglas forenses (trend shift, processing speed, irreversibility).  
  New forensic rules (trend shift, processing speed, irreversibility).
- Orquestador configurable en `scripts/analyze_rules.py` con reglas habilitables por config.  
  Configurable orchestrator in `scripts/analyze_rules.py` with config-driven rule toggles.
- Pruebas de orquestación y ajustes de configuración en `config.yaml`.  
  Orchestrator tests and configuration updates in `config.yaml`.

---
# [ES] Refactor modular de reglas + nuevas reglas forenses

  /dev: Notas del parche: Versión: v0.0.31 (commit ae6296f)



# [ES] Notas de Parche – C.E.N.T.I.N.E.L.

**Versión:** v0.0.31  
**Fecha:** 11-ene-2026  
**Autor:** userf8a2c4.

### Resumen
Se modularizaron las reglas de análisis y se añadieron nuevas reglas forenses para detección de fraude en tiempo real.

### Cambios principales
- **Mejora/Fix:** Modularización completa de reglas en `centinel/core/rules/`.  
  - **Por qué:** Facilitar mantenimiento, pruebas unitarias y activación selectiva por configuración.  
  - **Impacto:** Mayor claridad y trazabilidad en la ejecución de reglas por snapshot.  

- **Mejora/Fix:** Nuevas reglas forenses (trend shift, processing speed, irreversibility).  
  - **Por qué:** Detectar desviaciones de tendencia, velocidades no humanas y resultados estadísticamente irreversibles.  
  - **Impacto:** Alertas más precisas para auditoría en tiempo real durante TREP.  

- **Mejora/Fix:** Orquestador configurable en `scripts/analyze_rules.py`.  
  - **Por qué:** Desacoplar reglas del flujo de análisis y permitir habilitar/deshabilitar desde `config.yaml`.  
  - **Impacto:** Flexibilidad operativa y ajustes rápidos sin cambios de código.  

### Cambios técnicos
- Se creó el paquete `centinel/core/rules/` con helpers y reglas individuales (Benford, ML outliers, diffs básicos, participación, trend shift, processing speed, irreversibility).
- `scripts/analyze_rules.py` ahora usa `run_all_rules` y una lista `RULES` para ejecutar únicamente las reglas habilitadas.
- Se añadieron parámetros de configuración bajo `rules` en `config.yaml` y `config.example.yaml`.
- Se incluyeron pruebas del orquestador en `tests/test_rules_orchestrator.py`.

### Notas adicionales
- Las reglas siguen docstrings bilingües y manejo robusto de errores (datos nulos o timestamps inválidos).
- Las alertas se consolidan en `analysis_results.json` y `anomalies_report.json`.

**Objetivo de C.E.N.T.I.N.E.L.:** Monitoreo independiente, neutral y transparente de datos electorales públicos. Solo números. Solo hechos. Código abierto MIT para el pueblo hondureño.


-------------


# [EN] Patch Notes – C.E.N.T.I.N.E.L.

**Version:** v0.0.31  
**Date:** January 11, 2026  
**Author:** userf8a2c4.

### Summary
The analysis rules were modularized and new forensic rules were added for real-time fraud detection.

### Main Changes
- **Improvement/Fix:** Full rule modularization under `centinel/core/rules/`.  
  - **Why:** Improve maintainability, unit testing, and rule-level enable/disable controls.  
  - **Impact:** Clearer, traceable rule execution per snapshot.  

- **Improvement/Fix:** New forensic rules (trend shift, processing speed, irreversibility).  
  - **Why:** Detect trend deviations, non-human processing speeds, and statistically irreversible outcomes.  
  - **Impact:** More precise alerts for real-time TREP auditing.  

- **Improvement/Fix:** Configurable orchestrator in `scripts/analyze_rules.py`.  
  - **Why:** Decouple rules from the analysis flow and allow configuration-based toggles.  
  - **Impact:** Operational flexibility and rapid adjustments without code changes.  

### Technical Changes
- Added `centinel/core/rules/` package with helpers and individual rules (Benford, ML outliers, basic diffs, participation, trend shift, processing speed, irreversibility).
- `scripts/analyze_rules.py` now uses `run_all_rules` and a `RULES` list to run only enabled rules.
- Added rule configuration under `rules` in `config.yaml` and `config.example.yaml`.
- Included orchestrator tests in `tests/test_rules_orchestrator.py`.

### Additional Notes
- Rules include bilingual docstrings and robust error handling for null data or invalid timestamps.
- Alerts are consolidated into `analysis_results.json` and `anomalies_report.json`.

**C.E.N.T.I.N.E.L. Goal:** Independent, neutral and transparent monitoring of public electoral data. Only numbers. Only facts. MIT open-source for the Honduran people.
