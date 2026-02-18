# Centinel Engine

Auditoría continua, ética y técnica de datos públicos del CNE con evidencia verificable.

## Estado actual

`dev-v9` está enfocado en refactorización hacia simplicidad, claridad y mantenibilidad, sin perder capacidades operativas.

## Objetivo del proyecto

Mantener un pipeline de auditoría continua para 2029 que sea:
- Reproducible.
- Agnóstico políticamente.
- Legal y éticamente defensable.

## Flujo principal

```text
scheduler
  -> scrape
  -> normalize
  -> hash (SHA-256 encadenado)
  -> rules
  -> secure backup (multi-destino cifrado)
```

## Ejecutar localmente

```bash
poetry install
poetry run python -m centinel_engine.vital_signs
poetry run python scripts/run_pipeline.py --once
```

Configuración centralizada en:
- `config/prod/`
- `config/dev/`
- `config/secrets/`

## Arquitectura (resumen)

- `centinel_engine/`: lógica core (rate limiting, proxy/UA rotation, vital signs, secure backup, config loader).
- `scripts/`: ejecución operacional y utilidades CLI.
- `tests/`: unit, integration y chaos.
- `docs/`: metodología, seguridad, resiliencia y marco legal.
- `data/`: artefactos operativos y evidencia.

## Legal & Ético

Ver: [docs/legal_compliance_matrix.md](docs/legal_compliance_matrix.md).

## Extensiones futuras (desactivadas)

- Arbitrum.
- Telegram.
- Cloudflare hooks.
- Integración UPNFM avanzada.

Estas extensiones existen como puntos de evolución, pero están desactivadas en el flujo core actual.
