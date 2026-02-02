# Alertas externas accionables

Este documento describe el formato y ejemplos de alertas enviadas por Centinel Engine.

## Configuración

Variables de entorno relevantes:

- `TELEGRAM_BOT_TOKEN`: token del bot de Telegram.
- `TELEGRAM_CHAT_ID`: chat ID o canal de Telegram.
- `ALERT_MIN_LEVEL`: nivel mínimo para enviar alertas (default `WARNING`).
- `CENTINEL_DASHBOARD_URL`: URL del dashboard para incluir en el mensaje.
- `CENTINEL_HASH_DIR`: ruta del directorio de hashes (default `hashes`).
- `ALERT_RATE_LIMIT_SECONDS`: segundos mínimos entre alertas.
- `ALERT_MAX_RETRIES`: número máximo de reintentos.
- `ALERT_REQUEST_TIMEOUT`: timeout del envío en segundos.

## Formato del mensaje

```
[NIVEL] {timestamp} - {message}
Contexto: {json.dumps(context, indent=2)}
```

Si están disponibles, se añaden líneas extra:

- `Dashboard: <url>`
- `Checkpoint hash: <hash>`

## Ejemplos por nivel

### INFO

```
[INFO] 2024-11-05T18:32:10+00:00 - Estado normal importante
Contexto: {
  "source": "monitoring",
  "detail": "pipeline en estado estable"
}
Dashboard: https://centinel.example.org/dashboard
Checkpoint hash: 4a1b9b0b9b...
```

### WARNING

```
[WARNING] 2024-11-05T18:37:41+00:00 - Problema detectado, intentando resolver
Contexto: {
  "source": "healthcheck",
  "diagnostic": "checkpoint_stale"
}
Dashboard: https://centinel.example.org/dashboard
```

### CRITICAL

```
[CRITICAL] 2024-11-05T18:41:20+00:00 - Fallo crítico en checkpoint: checkpoint_write_failed
Contexto: {
  "source": "checkpointing",
  "code": "checkpoint_write_failed",
  "payload": {
    "checkpoint_key": "centinel/checkpoints/v1/run-001/latest.json"
  }
}
Checkpoint hash: 4a1b9b0b9b...
```

### PANIC

```
[PANIC] 2024-11-05T18:45:55+00:00 - MODO PÁNICO ACTIVADO - Reporte: https://s3.example.org/bucket/panic/...
Contexto: {
  "source": "panic_mode",
  "timestamp": "2024-11-05T18:45:55+00:00",
  "report_url": "https://s3.example.org/bucket/panic/...",
  "final_hash": "4a1b9b0b9b..."
}
Checkpoint hash: 4a1b9b0b9b...
```
