# Methodology / Metodología

## Scope / Alcance

Centinel procesa únicamente datos públicos del CNE para producir evidencia técnica reproducible.
Centinel processes only public CNE data to produce reproducible technical evidence.

## Active methodology / Metodología activa

1. **Scrape**: consulta endpoints públicos con límites éticos de frecuencia.
2. **Normalize**: homogeniza estructura para comparación histórica.
3. **Hash chain**: aplica SHA-256 encadenado para integridad temporal.
4. **Rules**: ejecuta `config/prod/rules.yaml` para validaciones determinísticas.
5. **Backup**: cifra y replica artefactos críticos a destinos configurados.

## Current rules focus / Enfoque actual de reglas

`rules.yaml` mantiene reglas base para:
- Consistencia básica de totales.
- Detección de saltos o cambios atípicos de snapshot.
- Validaciones de estructura y claves obligatorias.

## UPNFM extension point / Punto de extensión UPNFM

La revisión académica de reglas con UPNFM se mantiene como extensión controlada.
The academic rule-review collaboration with UPNFM remains an explicit extension point.

El core actual no depende de esa extensión para operar el pipeline principal.
The current core does not depend on that extension to run the main pipeline.
