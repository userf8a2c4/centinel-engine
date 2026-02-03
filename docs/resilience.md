# Resiliencia del pipeline

Esta guía reúne los mecanismos que evitan bloqueos y mejoran la tolerancia a fallas durante la captura de datos públicos.

## Circuit breaker y low-profile

El pipeline incluye un **circuit breaker** y un modo **low-profile** configurables en [`command_center/config.yaml`](../command_center/config.yaml). El breaker abre tras fallas acumuladas en una ventana, pausa el polling cuando está OPEN, registra `"Circuit OPEN – waiting"` cada 5 minutos y solo emite una alerta CRITICAL al abrir. El modo low-profile incrementa el intervalo base, añade jitter y rota user-agents + headers mínimos variables (Accept-Language y Referer). Revisa [`command_center/config.yaml.example`](../command_center/config.yaml.example) para valores recomendados y una lista sugerida de user-agents realistas. Los parámetros clave del breaker son:

- `failure_threshold`: número de fallos para abrir el circuito.
- `failure_window_seconds`: ventana temporal sobre la que se cuentan fallos.
- `open_timeout_seconds`: tiempo en estado OPEN antes de volver a evaluar.
- `half_open_after_seconds`: espera antes de transicionar a HALF-OPEN.
- `success_threshold`: éxitos requeridos para cerrar el circuito.
- `open_log_interval_seconds`: intervalo de logs mientras está OPEN.

## Retry y configuración de resiliencia

El pipeline usa un esquema de reintentos configurable vía [`retry_config.yaml`](../retry_config.yaml), con políticas diferenciadas por status HTTP y tipo de excepción (429, 5xx, 4xx, timeouts, parsing). Esto permite backoff exponencial y jitter ajustables, límites de intentos por error y acciones de alerta cuando el servidor rechaza la solicitud. Además, se registra un historial de fallos definitivos en `failed_requests.jsonl` y se evita descargar snapshots duplicados si existe un archivo reciente para la misma fuente (idempotencia basada en timestamp). Revisa el flujo de descarga en [`scripts/download_and_hash.py`](../scripts/download_and_hash.py) y [`src/centinel/downloader.py`](../src/centinel/downloader.py) para más detalles.

## Watchdog de salud del pipeline

El watchdog supervisa que el pipeline siga avanzando y reinicia cuando detecta inactividad prolongada. La configuración vive en [`watchdog.yaml`](../watchdog.yaml) e incluye intervalos de chequeo, tiempos máximos de inactividad, límites de crecimiento de logs y parámetros de reinicio. Ajusta rutas (log, snapshots y locks) si ejecutas la instancia en un directorio distinto.

### Ejemplo de uso

```bash
# Ruta custom para el YAML de reintentos
export RETRY_CONFIG_PATH=retry_config.yaml
poetry run python scripts/run_pipeline.py --once
```

El `run_pipeline` pasa `RETRY_CONFIG_PATH` al subproceso de descarga para que [`scripts/download_and_hash.py`](../scripts/download_and_hash.py) aplique la configuración especificada. La integración se encuentra en [`scripts/run_pipeline.py`](../scripts/run_pipeline.py).

### Ejemplo comentado de configuración (resiliencia)

```yaml
# retry_config.yaml - ejemplo comentado
default:
  max_attempts: 5            # Intentos base por solicitud.
  backoff_base: 2            # Base para el backoff exponencial.
  backoff_multiplier: 2      # Multiplicador por intento.
  max_delay: 300             # Máximo de espera entre reintentos (s).
  jitter: 0.25               # Jitter fijo (0-1) o rango min/max.

per_status:
  "429":
    max_attempts: 20         # Más tolerancia ante rate limits.
    backoff_base: 8
    backoff_multiplier: 2
    max_delay: 900
    jitter:
      min: 0.1
      max: 0.3
  "5xx":
    max_attempts: 8
    backoff_base: 3
    backoff_multiplier: 2
    max_delay: 300
    jitter: 0.2

per_exception:
  ReadTimeout:
    max_attempts: 6
    backoff_base: 2
    backoff_multiplier: 2
    max_delay: 120
    jitter: 0.2

timeout_seconds: 30          # Timeout por request (s).
failed_requests_path: failed_requests.jsonl
recent_snapshot_seconds: 300 # Idempotencia por timestamp.
log_payload_bytes: 2000      # Limite de payload en logs.
```

```yaml
# watchdog.yaml - ejemplo comentado
check_interval_minutes: 3        # Frecuencia de chequeo del watchdog.
max_inactivity_minutes: 30       # Tiempo máximo sin snapshots nuevos.
heartbeat_timeout: 10            # Timeout para heartbeat en segundos.
failure_grace_minutes: 6         # Gracia antes de actuar.
action_cooldown_minutes: 10      # Cooldown entre reinicios.
aggressive_restart: false        # Reinicio agresivo si true.
alert_urls: []                   # Webhooks opcionales.
data_dir: "data"
snapshot_glob: "*.json"
snapshot_exclude:
  - "pipeline_state.json"
  - "heartbeat.json"
log_path: "logs/centinel.log"
max_log_size_mb: 200             # Tamaño máximo del log.
max_log_growth_mb_per_min: 30    # Límite de crecimiento.
lock_files:
  - "data/temp/pipeline.lock"
lock_timeout_minutes: 30
pipeline_command:
  - "python"
  - "scripts/run_pipeline.py"
restart_timeout_seconds: 30
docker_container_name: "centinel-engine"
state_path: "data/watchdog_state.json"
```

```yaml
# command_center/config.yaml - sección de circuito
circuit_breaker:
  failure_threshold: 5          # Fallos necesarios para abrir el circuito.
  failure_window_seconds: 600   # Ventana de tiempo para contar fallos.
  open_timeout_seconds: 1800    # Tiempo en OPEN antes de reevaluar.
  half_open_after_seconds: 600  # Espera antes de pasar a HALF-OPEN.
  success_threshold: 2          # Éxitos requeridos para cerrar.
  open_log_interval_seconds: 300 # Intervalo de log en OPEN.
```
