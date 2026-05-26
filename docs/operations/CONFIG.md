# Configuration validation and auditability (Validación de configuración y auditabilidad)

## Overview (Resumen)
This guide explains how to validate `config.yaml` and `rules.yaml`, plus how versioned history is stored for audit trails. (Esta guía explica cómo validar `config.yaml` y `rules.yaml`, además de cómo se guarda el historial versionado para auditoría.)

## Manual validation (Validación manual)
Use the CLI or Python one-liners to validate the YAML schemas. (Usa el CLI o comandos Python para validar los esquemas YAML.)

### Validate the main config (Validar la configuración principal)
```bash
poetry run python -c "from centinel.utils.config_loader import load_config; load_config()"
```

### Validate the rules config (Validar la configuración de reglas)
```bash
poetry run python -c "from centinel.utils.config_loader import load_rules_config; load_rules_config()"
```

### Dry-run command center (Command center en modo dry-run)
```bash
poetry run command-center --dry-run
```

## Config versioning (Versionado de configuraciones)
Each successful load archives the raw YAML files under `command_center/configs/history/` with UTC timestamps. (Cada carga exitosa archiva los YAML crudos en `command_center/configs/history/` con timestamps UTC.)

## Valid YAML example (Ejemplo YAML válido)
```yaml
retry_max: 5
backoff_factor: 2
security:
  encrypt_enabled: true
  log_sensitive: false
  rate_limit_rpm: 10
rules:
  benford_first_digit:
    rule_name: "benford_first_digit"
    threshold: 0.05
    enabled: true
    parameters:
      min_samples: 50
```

## Invalid YAML example (Ejemplo YAML inválido)
Missing required fields like `rule_name` or `threshold` will raise a validation error. (Faltan campos requeridos como `rule_name` o `threshold`, lo que genera error de validación.)
```yaml
rules:
  benford_first_digit:
    threshold: 0.05
```
