# Resiliencia operativa y tolerancia a fallos / Operational Resilience and Fault Tolerance

## Introducción bilingüe / Bilingual Introduction

**ES:** La resiliencia operativa en auditoría electoral consiste en mantener la continuidad, integridad y verificabilidad del monitoreo aun cuando la fuente pública experimente **rate-limits, timeouts, bloqueos temporales o degradación**. En el caso de Honduras 2029, el pipeline de CENTINEL consulta JSON públicos del CNE con una cadencia típica de **cada 5 minutos** durante elección activa. Esto exige **reintentos controlados, backoff con jitter, rotación de proxies y watchdogs** que reduzcan presión sobre la fuente sin sacrificar trazabilidad. El objetivo es defensivo: evitar sobrecarga, documentar fallos y preservar evidencia reproducible para observadores técnicos (OEA, Carter Center, academia).

**EN:** Operational resilience in electoral audits means keeping monitoring **continuous, verifiable, and auditable** even when public sources face **rate limits, timeouts, temporary blocks, or service degradation**. For Honduras 2029, CENTINEL polls public CNE JSON at a **~5-minute cadence** during active elections. This requires **controlled retries, backoff with jitter, proxy rotation, and watchdog thresholds** that reduce pressure on the source while preserving traceability. The intent is defensive: minimize load, document failures, and preserve reproducible evidence for technical observers (OAS, Carter Center, academia).

---

## 1) `retry_config.yaml` — Reintentos, backoff y jitter / Retries, backoff, and jitter

### Parámetros clave / Key parameters

| Parámetro | Descripción (ES) | Description (EN) | Recomendado / Recommended |
| --- | --- | --- | --- |
| `default.max_attempts` | Límite general de reintentos. | Global retry cap. | `5` |
| `default.backoff_multiplier` | Factor de crecimiento exponencial. | Exponential growth factor. | `2` |
| `default.jitter` | Aleatoriza espera para evitar sincronización. | Randomizes delay to avoid sync. | `0.25` |
| `per_status."429"` | Rate-limit: más intentos y backoff lento. | Rate-limit: more attempts & slower backoff. | `max_attempts: 20`, `backoff_base: 8` |
| `per_exception.ReadTimeout` | Timeouts: reintentos moderados. | Timeouts: moderate retries. | `max_attempts: 6` |
| `timeout_seconds` | Timeout por request. | Per-request timeout. | `30` |
| `recent_snapshot_seconds` | Idempotencia: evita duplicados. | Idempotency: avoid duplicates. | `300` |

### Ejemplo comentado / Commented example

```yaml
# Configuración de reintentos y resiliencia para descargas C.E.N.T.I.N.E.L.
# Retry & resilience configuration for downloads.

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

per_status:
  "429":
    # Rate limit: más intentos y backoff más lento.
    # Rate limit: more attempts and slower backoff.
    max_attempts: 20
    backoff_base: 8
    backoff_multiplier: 2
    max_delay: 900
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
    # Bloqueo: alertar sin insistir.
    # Forbidden/block: alert without heavy retry.
    max_attempts: 2
    action: "alert_only"

per_exception:
  ReadTimeout:
    # Timeout de lectura: reintentos moderados.
    # Read timeout: moderate retries.
    max_attempts: 6
    backoff_base: 2
    backoff_multiplier: 2
    max_delay: 120
    jitter: 0.2

timeout_seconds: 30
failed_requests_path: failed_requests.jsonl
recent_snapshot_seconds: 300
idempotency_mode: "timestamp"
```

---

## 2) `watchdog.yaml` — Umbrales de actividad y reinicios / Activity thresholds and restarts

### Parámetros clave / Key parameters

| Parámetro | Descripción (ES) | Description (EN) | Recomendado / Recommended |
| --- | --- | --- | --- |
| `check_interval_minutes` | Frecuencia de chequeo. | Watchdog check interval. | `3` |
| `max_inactivity_minutes` | Máxima inactividad permitida. | Maximum allowed inactivity. | `30` |
| `failure_grace_minutes` | Ventana de gracia antes de actuar. | Grace period before action. | `6` |
| `action_cooldown_minutes` | Cooldown entre acciones. | Cooldown between actions. | `10` |
| `max_log_growth_mb_per_min` | Umbral de crecimiento de logs. | Log growth threshold. | `30` |
| `lock_timeout_minutes` | Locks considerados “stuck”. | When locks are considered stuck. | `30` |

### Ejemplo comentado / Commented example

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
# Locks a monitorear.
# Locks to monitor.
lock_files:
  - "data/temp/pipeline.lock"
  - "data/temp/stuck.lock"
# Timeout de locks (min).
# Lock timeout (min).
lock_timeout_minutes: 30
```

---

## 3) `proxies.yaml` — Rotación de proxies y validación / Proxy rotation and validation

### Parámetros clave / Key parameters

| Parámetro | Descripción (ES) | Description (EN) | Recomendado / Recommended |
| --- | --- | --- | --- |
| `rotation_strategy` | Estrategia de rotación. | Rotation strategy. | `round_robin` |
| `rotation_every_n` | Rotar cada N requests. | Rotate every N requests. | `1` |
| `proxy_timeout_seconds` | Timeout de prueba. | Proxy test timeout. | `15` |
| `test_url` | Endpoint de validación. | Validation endpoint. | `https://httpbin.org/ip` |
| `proxies[]` | Lista con esquema y credenciales opcionales. | List with scheme and optional credentials. | `http://user:pass@ip:port` |

### Ejemplo comentado / Commented example

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

---

## 4) `rules.yaml` — Reglas básicas de anomalías / Baseline anomaly rules

### Parámetros clave / Key parameters

| Parámetro | Descripción (ES) | Description (EN) | Recomendado / Recommended |
| --- | --- | --- | --- |
| `reglas_auditoria[].nombre` | Regla auditora activada. | Enabled audit rule. | `apply_benford_law`, `check_distribution_chi2` |
| `resiliencia.retry_max` | Reintentos sugeridos en reglas. | Suggested retry cap in rules. | `5` |
| `resiliencia.backoff_factor` | Backoff sugerido en reglas. | Suggested backoff factor in rules. | `2` |
| `resiliencia.chi2_p_critical` | Umbral crítico chi-cuadrado. | Chi-square critical threshold. | `0.01` |
| `resiliencia.benford_min_samples` | Mínimo de muestras para Benford. | Minimum samples for Benford. | `10` |

### Ejemplo comentado / Commented example

```yaml
reglas_auditoria:
  - nombre: "apply_benford_law"
    # Evalúa primer dígito con Ley de Benford y prueba chi-cuadrado.
    # Evaluates first digit with Benford's Law and chi-square test.
    descripcion: "Evalúa primer dígito con Ley de Benford y prueba chi-cuadrado."
  - nombre: "check_distribution_chi2"
    # Compara distribución partido/departamento contra esperados proporcionales.
    # Compares party/department distribution against proportional expectations.
    descripcion: "Compara distribución partido/departamento contra esperados proporcionales."

resiliencia:
  # Parámetros sugeridos de resiliencia (documentación).
  # Suggested resilience parameters (documentation).
  retry_max: 5
  backoff_factor: 2
  max_json_presidenciales: 19
  chi2_p_critical: 0.01
  benford_min_samples: 10
```

---

## Circuit breaker y low-profile

**ES:** El circuito breaker y el modo low-profile reducen riesgos de bloqueo cuando la fuente pública muestra degradación. El breaker cambia a **OPEN** tras fallos continuos, baja la cadencia y evita insistencia; en **HALF-OPEN** prueba recuperación con pocas solicitudes antes de volver a **CLOSED**. El modo low-profile incrementa intervalos base, añade jitter y reduce headers para minimizar huella.

**EN:** The circuit breaker and low-profile mode reduce blocking risk when the public source degrades. The breaker switches to **OPEN** after repeated failures, lowers cadence, and avoids repeated hits; in **HALF-OPEN** it probes recovery with a few requests before returning to **CLOSED**. Low-profile mode increases base intervals, adds jitter, and reduces headers to minimize footprint.

---

## Mejores prácticas / Best practices

### Modo low-profile (elección activa) / Low-profile mode (active election)

**ES:**
- Prioriza **backoff más lento** (`backoff_base: 3–8`) y `jitter` moderado para evitar picos concurrentes.
- Reduce la **agresividad de reintentos** en `403/401` y activa alertas tempranas.
- Usa **rotación de proxies** y valida la salida antes de iniciar polling continuo.
- Mantén `watchdog` con **intervalos cortos** para detectar inactividad sin reinicios frecuentes.

**EN:**
- Prefer **slower backoff** (`backoff_base: 3–8`) and moderate `jitter` to avoid concurrency spikes.
- Reduce **retry aggressiveness** on `403/401` and trigger early alerts.
- Use **proxy rotation** and validate egress before continuous polling.
- Keep `watchdog` on **shorter intervals** to detect inactivity without frequent restarts.

### Modo mantenimiento (mensual) / Maintenance mode (monthly)

**ES:**
- Incrementa `max_inactivity_minutes` y `action_cooldown_minutes` para minimizar reinicios.
- Mantén `timeout_seconds` bajos para liberar recursos de forma limpia.
- Desactiva proxies si no hay necesidad operativa y reduce `rotation_every_n`.

**EN:**
- Increase `max_inactivity_minutes` and `action_cooldown_minutes` to minimize restarts.
- Keep `timeout_seconds` low to release resources cleanly.
- Disable proxies when not operationally required and reduce `rotation_every_n`.

---

## Referencias y credibilidad / References and credibility

**ES:** Estas configuraciones documentadas favorecen la **reproducibilidad**, porque cualquier auditor externo puede recrear condiciones de captura (cadencias, umbrales, backoff) y validar que el sistema operó de forma neutral y defensiva. Al publicar parámetros y ejemplos comentados, CENTINEL facilita el escrutinio técnico de organizaciones como la **OEA** o el **Carter Center** y refuerza la neutralidad del pipeline.

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
