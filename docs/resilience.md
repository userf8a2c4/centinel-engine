# Resiliencia y Configuraciones de Tolerancia a Fallos / Resilience and Fault-Tolerance Configurations

Este documento explica los tres archivos YAML principales que controlan la resiliencia del sistema CENTINEL frente a fallos de red, límites de tasa y bloqueos del CNE.

## 1) retry_config.yaml

**Qué hace / What it does**
- **ES:** Define el mecanismo de reintentos con backoff exponencial y jitter, con reglas por estado HTTP y por excepción para ajustar tolerancia y alertas.
- **EN:** Defines the retry mechanism with exponential backoff and jitter, with per-HTTP-status and per-exception rules to tune tolerance and alerts.

**Contenido actual comentado / Commented current content**

```yaml
# Configuración de reintentos y resiliencia para descargas C.E.N.T.I.N.E.L.
# Retry & resilience configuration for downloads.

# Valores por defecto para cualquier request.
# Default values for any request.
default:
  # Intentos máximos por solicitud.
  # Maximum attempts per request.
  max_attempts: 5
  # Base del backoff exponencial.
  # Base for exponential backoff.
  backoff_base: 2
  # Multiplicador por intento.
  # Multiplier per attempt.
  backoff_multiplier: 2
  # Espera máxima entre reintentos (s).
  # Maximum delay between retries (s).
  max_delay: 300
  # Jitter fijo (0-1) o rango min/max.
  # Fixed jitter (0-1) or min/max range.
  jitter: 0.25

# Reglas específicas por status HTTP.
# Specific rules by HTTP status.
per_status:
  "429":
    # Rate limit: más intentos y backoff más lento.
    # Rate limit: more attempts and slower backoff.
    max_attempts: 20
    backoff_base: 8
    backoff_multiplier: 2
    max_delay: 900
    # Jitter como rango.
    # Jitter as a range.
    jitter:
      min: 0.1
      max: 0.3
  "5xx":
    # Errores del servidor: reintentos moderados.
    # Server errors: moderate retries.
    max_attempts: 8
    backoff_base: 3
    backoff_multiplier: 2
    max_delay: 300
    jitter: 0.2
  "403":
    # Bloqueo/forbidden: alertar sin insistir.
    # Forbidden/block: alert without heavy retry.
    max_attempts: 2
    action: "alert_only"
  "401":
    # No autorizado: alertar y detener.
    # Unauthorized: alert and stop.
    max_attempts: 2
    action: "alert_only"
  "400":
    # Bad request: pocos intentos y alerta.
    # Bad request: few attempts and alert.
    max_attempts: 3
    action: "alert_only"
  "404":
    # Recurso no encontrado: pocos reintentos.
    # Not found: minimal retries.
    max_attempts: 2
    backoff_base: 2
    max_delay: 60
    jitter: 0.2

# Otros códigos no listados arriba.
# Other status codes not listed above.
other_status:
  # Reintentos conservadores por defecto.
  # Conservative default retries.
  max_attempts: 3
  backoff_base: 2
  max_delay: 120
  jitter: 0.2

# Reglas específicas por excepción.
# Specific rules by exception.
per_exception:
  ConnectionError:
    # Fallo de conexión: backoff moderado.
    # Connection failure: moderate backoff.
    max_attempts: 6
    backoff_base: 2
    backoff_multiplier: 2
    max_delay: 120
    jitter: 0.2
  ReadTimeout:
    # Timeout de lectura: reintentos moderados.
    # Read timeout: moderate retries.
    max_attempts: 6
    backoff_base: 2
    backoff_multiplier: 2
    max_delay: 120
    jitter: 0.2
  SSLError:
    # Error SSL: reintentos limitados.
    # SSL error: limited retries.
    max_attempts: 5
    backoff_base: 2
    backoff_multiplier: 2
    max_delay: 120
    jitter: 0.2
  JSONDecodeError:
    # Parsing fallido: pocos reintentos.
    # Parsing failure: few retries.
    max_attempts: 3
    backoff_base: 2
    backoff_multiplier: 2
    max_delay: 60
    jitter: 0.15

# Timeout por request (segundos).
# Request timeout (seconds).
timeout_seconds: 30

# Archivo donde se registran fallos definitivos.
# File where definitive failures are recorded.
failed_requests_path: failed_requests.jsonl

# Idempotencia: evita descargas duplicadas si existe snapshot reciente.
# Idempotency: avoid duplicate downloads if a recent snapshot exists.
recent_snapshot_seconds: 300
# Modo de idempotencia basado en timestamp.
# Timestamp-based idempotency mode.
idempotency_mode: "timestamp"

# Tamaño máximo del payload en logs para errores de parsing.
# Max payload size in logs for parsing errors.
log_payload_bytes: 2000
```

**Ejemplo 1: configuración conservadora / Conservative configuration**

```yaml
# Conservador: backoff lento, máximo 5 intentos.
# Conservative: slow backoff, max 5 attempts.
default:
  max_attempts: 5
  backoff_base: 3
  backoff_multiplier: 2
  max_delay: 600
  jitter: 0.1
```

**Ejemplo 2: configuración agresiva / Aggressive configuration**

```yaml
# Agresivo: backoff rápido, máximo 10 intentos, jitter alto.
# Aggressive: fast backoff, max 10 attempts, high jitter.
default:
  max_attempts: 10
  backoff_base: 1
  backoff_multiplier: 2
  max_delay: 120
  jitter: 0.5
```

## 2) watchdog.yaml

**Qué hace / What it does**
- **ES:** Supervisa la actividad del pipeline, detecta inactividad prolongada, monitorea crecimiento de logs y decide acciones ante fallos críticos (como reinicios).
- **EN:** Monitors pipeline activity, detects prolonged inactivity, watches log growth, and decides actions on critical failures (such as restarts).

**Contenido actual comentado / Commented current content**

```yaml
# Intervalo de chequeo del watchdog (min).
# Watchdog check interval (min).
check_interval_minutes: 3
# Máxima inactividad permitida (min).
# Maximum allowed inactivity (min).
max_inactivity_minutes: 30
# Timeout del heartbeat (s).
# Heartbeat timeout (s).
heartbeat_timeout: 10
# Período de gracia antes de actuar (min).
# Grace period before acting (min).
failure_grace_minutes: 6
# Cooldown entre acciones (min).
# Cooldown between actions (min).
action_cooldown_minutes: 10
# Reinicio agresivo si es true.
# Aggressive restart if true.
aggressive_restart: false
# Webhooks de alerta.
# Alert webhooks.
alert_urls: []
# Directorio de datos base.
# Base data directory.
data_dir: "data"
# Patrón de snapshots.
# Snapshot pattern.
snapshot_glob: "*.json"
# Archivos excluidos de snapshots.
# Snapshot exclusions.
snapshot_exclude:
  - "pipeline_state.json"
  - "heartbeat.json"
  - "alerts.json"
  - "snapshot_index.json"
  - "pipeline_checkpoint.json"
  - "checkpoint.json"
# Ruta del log principal.
# Main log path.
log_path: "logs/centinel.log"
# Tamaño máximo del log (MB).
# Max log size (MB).
max_log_size_mb: 200
# Crecimiento máximo por minuto (MB/min).
# Max growth per minute (MB/min).
max_log_growth_mb_per_min: 30
# Locks a monitorear.
# Locks to monitor.
lock_files:
  - "data/temp/pipeline.lock"
  - "data/temp/stuck.lock"
# Timeout de locks (min).
# Lock timeout (min).
lock_timeout_minutes: 30
# Ruta del heartbeat.
# Heartbeat file path.
heartbeat_path: "data/heartbeat.json"
# Procesos del pipeline a reconocer.
# Pipeline process signatures.
pipeline_process_match:
  - "scripts/run_pipeline.py"
# Comando para reiniciar el pipeline.
# Command to restart the pipeline.
pipeline_command:
  - "python"
  - "scripts/run_pipeline.py"
# Timeout del reinicio (s).
# Restart timeout (s).
restart_timeout_seconds: 30
# Socket de Docker (si aplica).
# Docker socket (if used).
docker_socket_path: "/var/run/docker.sock"
# Nombre del contenedor Docker.
# Docker container name.
docker_container_name: "centinel-engine"
# Estado persistente del watchdog.
# Watchdog persistent state path.
state_path: "data/watchdog_state.json"
```

**Ejemplo 1: timeout corto para pruebas / Short timeout for testing**

```yaml
# Pruebas: detección rápida de inactividad.
# Testing: quick inactivity detection.
check_interval_minutes: 1
max_inactivity_minutes: 5
heartbeat_timeout: 5
```

**Ejemplo 2: timeout largo + reinicio automático / Long timeout + auto restart**

```yaml
# Producción: tolerancia alta con reinicio automático.
# Production: high tolerance with auto restart.
max_inactivity_minutes: 90
aggressive_restart: true
pipeline_command:
  - "python"
  - "scripts/run_pipeline.py"
```

## 3) proxies.yaml

**Qué hace / What it does**
- **ES:** Define cómo agregar y rotar proxies (http/https/socks5), incluyendo estrategia de rotación y timeout de prueba.
- **EN:** Defines how to add and rotate proxies (http/https/socks5), including rotation strategy and test timeout.

**Contenido actual comentado / Commented current content**

```yaml
# Modo del rotador de proxies.
# Proxy rotator mode.
mode: proxy_rotator
# Estrategia de rotación.
# Rotation strategy.
rotation_strategy: round_robin
# Rotar cada N requests.
# Rotate every N requests.
rotation_every_n: 1
# Timeout de prueba del proxy (s).
# Proxy test timeout (s).
proxy_timeout_seconds: 15
# URL para testear la salida del proxy.
# URL to test proxy egress.
test_url: https://httpbin.org/ip
# Lista de proxies.
# Proxy list.
proxies:
  # Formato: esquema://[user:pass@]ip:port
  # Format: scheme://[user:pass@]ip:port
  - "http://user:pass@ip:port"
  - "socks5://ip:port"
```

**Ejemplo 1: 3 proxies públicos + round-robin / 3 public proxies + round-robin**

```yaml
mode: proxy_rotator
rotation_strategy: round_robin
rotation_every_n: 1
proxy_timeout_seconds: 10
test_url: https://httpbin.org/ip
proxies:
  # Lista de proxies públicos (ejemplo).
  # Public proxy list (example).
  - "http://203.0.113.10:8080"
  - "http://203.0.113.11:8080"
  - "socks5://203.0.113.12:1080"
```

**Ejemplo 2: proxies con autenticación básica / Proxies with basic auth**

```yaml
mode: proxy_rotator
rotation_strategy: round_robin
rotation_every_n: 1
proxy_timeout_seconds: 15
test_url: https://httpbin.org/ip
proxies:
  # Formato con credenciales: user:pass@ip:port
  # Credential format: user:pass@ip:port
  - "http://user1:pass1@198.51.100.20:8080"
  - "https://user2:pass2@198.51.100.21:8443"
```

## Recomendaciones generales / General Recommendations

- **ES:** Ajusta el `max_attempts` según el SLA y el impacto en el rate limit; **EN:** Tune `max_attempts` based on SLA and rate-limit impact.
- **ES:** Mantén `proxy_timeout_seconds` bajo en entornos inestables; **EN:** Keep `proxy_timeout_seconds` low in unstable environments.
- **ES:** Usa `alert_urls` para notificar bloqueos repetidos; **EN:** Use `alert_urls` to notify repeated blocks.
- **ES:** Registra los fallos definitivos en `failed_requests_path` y revísalos periódicamente; **EN:** Log definitive failures in `failed_requests_path` and review them regularly.
- **ES:** En producción, combina tiempos de watchdog altos con reinicio automático; **EN:** In production, combine longer watchdog timeouts with auto restart.

## Contexto adicional del pipeline / Additional pipeline context

- **ES:** El pipeline incluye un circuito breaker y un modo low-profile configurables en `command_center/config.yaml`, con transiciones OPEN/HALF-OPEN/CLOSED y logs periódicos en estado OPEN.
- **EN:** The pipeline includes a circuit breaker and a low-profile mode in `command_center/config.yaml`, with OPEN/HALF-OPEN/CLOSED transitions and periodic logs while OPEN.
- **ES:** El modo low-profile aumenta el intervalo base, añade jitter y rota user-agents con headers mínimos (por ejemplo, Accept-Language y Referer).
- **EN:** Low-profile mode increases the base interval, adds jitter, and rotates user-agents with minimal headers (e.g., Accept-Language and Referer).

## 3) Chaos Testing

**Qué hace / What it does**
- **ES:** Ejecuta experimentos de chaos engineering con fallos específicos del CNE (rate-limit 429, timeouts 503, JSON malformado, hashes alterados, fallos de proxy y watchdog). Estos escenarios refuerzan la credibilidad de la auditoría digital en Centroamérica al demostrar recuperación controlada en endpoints agregados.
- **EN:** Runs chaos engineering experiments with CNE-specific failures (429 rate limits, 503 timeouts, malformed JSON, altered hashes, proxy failures, and watchdog triggers). These scenarios strengthen the credibility of the digital audit in Central America by demonstrating controlled recovery on aggregated endpoints.

**Componentes / Components**
- **scripts/chaos_test.py:** Script principal con mocks usando `responses`, métricas de recuperación y reportes JSON.
- **chaos_config.yaml.example:** Niveles de caos (low/mid/high) con duración, probabilidad de fallos y parámetros de reintento.
- **tests/chaos/**: Pruebas unitarias que validan recuperación ante rate-limits.
- **.github/workflows/chaos-test.yml:** Ejecución automática en PRs y pushes.

**Ejecución manual / Manual run**
```bash
python scripts/chaos_test.py --config chaos_config.yaml.example --level low --report chaos_report.json
```

**Notas de credibilidad / Credibility notes**
- **ES:** Los reportes incluyen tiempo de recuperación, banderas de anomalía y placeholders de p-values para análisis estadístico futuro.
- **EN:** Reports include recovery time, anomaly flags, and p-value placeholders for future statistical analysis.
