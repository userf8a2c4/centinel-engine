# Centro de Comando

## Español

Esta carpeta es el **único lugar** que debes editar para configurar C.E.N.T.I.N.E.L. en producción.
Centraliza la configuración operativa y el panel de control del sistema.

Archivos editables:

1. `config.yaml` → configuración principal de scraping, reglas y fuentes.
2. `.env` → credenciales sensibles (claves, tokens).
3. `security_config.yaml`, `advanced_security_config.yaml`, `attack_config.yaml`, `rules.yaml` → capas opcionales de seguridad y reglas avanzadas (ahora con índice y comentarios bilingües).

### Cadencia operativa recomendada
- **Modo mantenimiento/desarrollo:** scraping y anclaje en L2 **1 vez al mes**.
- **Modo monitoreo normal:** entre **24 y 72 horas**.
- **Modo elección activa:** entre **5 y 15 minutos**.

### Pasos rápidos
1. Copia los ejemplos:
   ```bash
   cp command_center/config.yaml.example command_center/config.yaml
   cp command_center/.env.example command_center/.env
   ```
2. Ajusta valores según tu entorno.
3. Ejecuta los scripts con Poetry:
   ```bash
   poetry run python scripts/download_and_hash.py
   poetry run python scripts/analyze_rules.py
   ```

### Estructura del centro de comando
- `config.yaml` y `.env`: configuración operativa única.
- `settings.py`, `master_switch.py`, `rules_config.py`: primitives del panel de control.
- `endpoints.py` y `rules/`: catálogo de endpoints y reglas activas.

### Reglas
- **No modifiques** archivos fuera de esta carpeta para la configuración operativa.
- Este directorio es la fuente de verdad.

---

## English

This folder is the **only place** you should edit to configure C.E.N.T.I.N.E.L. in production.
It centralizes operational configuration and the system control panel.

Editable files:

1. `config.yaml` → main scraping configuration, rules, and sources.
2. `.env` → sensitive credentials (keys, tokens).
3. `security_config.yaml`, `advanced_security_config.yaml`, `attack_config.yaml`, `rules.yaml` → optional security and advanced-rule layers (now with index and bilingual comments).

### Recommended operating cadence
- **Maintenance/development mode:** scraping and L2 anchoring **once per month**.
- **Normal monitoring mode:** between **24 and 72 hours**.
- **Active election mode:** between **5 and 15 minutes**.

### Quick steps
1. Copy the examples:
   ```bash
   cp command_center/config.yaml.example command_center/config.yaml
   cp command_center/.env.example command_center/.env
   ```
2. Update values for your environment.
3. Run scripts with Poetry:
   ```bash
   poetry run python scripts/download_and_hash.py
   poetry run python scripts/analyze_rules.py
   ```

### Command center structure
- `config.yaml` and `.env`: single operational configuration.
- `settings.py`, `master_switch.py`, `rules_config.py`: control panel primitives.
- `endpoints.py` and `rules/`: endpoint catalog and active rules.

### Rules
- **Do not modify** files outside this folder for operational configuration.
- This directory is the source of truth.
