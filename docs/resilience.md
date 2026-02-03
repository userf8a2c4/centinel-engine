# Resiliencia del pipeline

Esta guía reúne los mecanismos que evitan bloqueos y mejoran la tolerancia a fallas durante la captura de datos públicos.

## Circuit breaker y low-profile

El pipeline incluye un **circuit breaker** y un modo **low-profile** configurables en [`command_center/config.yaml`](../command_center/config.yaml). El breaker abre tras fallas acumuladas en una ventana, pausa el polling cuando está OPEN, registra `"Circuit OPEN – waiting"` cada 5 minutos y solo emite una alerta CRITICAL al abrir. El modo low-profile incrementa el intervalo base, añade jitter y rota user-agents + headers mínimos variables (Accept-Language y Referer). Revisa [`command_center/config.yaml.example`](../command_center/config.yaml.example) para valores recomendados y una lista sugerida de user-agents realistas.

## Retry y configuración de resiliencia

El pipeline usa un esquema de reintentos configurable vía [`retry_config.yaml`](../retry_config.yaml), con políticas diferenciadas por status HTTP y tipo de excepción (429, 5xx, 4xx, timeouts, parsing). Esto permite backoff exponencial y jitter ajustables, límites de intentos por error y acciones de alerta cuando el servidor rechaza la solicitud. Además, se registra un historial de fallos definitivos en `failed_requests.jsonl` y se evita descargar snapshots duplicados si existe un archivo reciente para la misma fuente (idempotencia basada en timestamp). Revisa el flujo de descarga en [`scripts/download_and_hash.py`](../scripts/download_and_hash.py) y [`src/centinel/downloader.py`](../src/centinel/downloader.py) para más detalles.

### Ejemplo de uso

```bash
# Ruta custom para el YAML de reintentos
export RETRY_CONFIG_PATH=retry_config.yaml
poetry run python scripts/run_pipeline.py --once
```

El `run_pipeline` pasa `RETRY_CONFIG_PATH` al subproceso de descarga para que [`scripts/download_and_hash.py`](../scripts/download_and_hash.py) aplique la configuración especificada. La integración se encuentra en [`scripts/run_pipeline.py`](../scripts/run_pipeline.py).
