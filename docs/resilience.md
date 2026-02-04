# Resiliencia operativa y tolerancia a fallos / Operational Resilience and Fault Tolerance

## Introducción formal / Formal introduction

**ES:** La resiliencia en auditoría electoral digital asegura continuidad, integridad y verificabilidad del monitoreo cuando las fuentes públicas presentan **rate-limits, timeouts, fingerprinting o bloqueos temporales**. En CENTINEL, el pipeline consulta JSON públicos del CNE con cadencia típica de **cada 5 minutos** en elección activa. La estrategia es defensiva y proporcional: **reintentos controlados, backoff con jitter, rotación de proxies y watchdogs** reducen presión sobre la fuente, documentan fallos y preservan evidencia reproducible para observadores internacionales (OEA, Carter Center, NED, Luminate).

**EN:** Resilience in digital electoral auditing preserves continuity, integrity, and verifiability when public sources face **rate limits, timeouts, fingerprinting, or temporary blocks**. In CENTINEL, the pipeline polls public CNE JSON on a typical **5-minute cadence** during active elections. The approach is defensive and proportional: **controlled retries, backoff with jitter, proxy rotation, and watchdog thresholds** reduce pressure on the source, document failures, and preserve reproducible evidence for international observers (OAS, Carter Center, NED, Luminate).

**Enlaces internos / Internal links:**
- [README principal / Main README](../README.md)
- [Índice de documentación / Documentation index](README.md)
- [Arquitectura / Architecture](architecture.md)
- [Reglas de auditoría / Audit rules](rules.md)
- [Principios operativos / Operating principles](operating_principles.md)

---

## 1) `retry_config.yaml` — Reintentos, backoff y jitter / Retries, backoff, and jitter

### Parámetros y valores recomendados / Parameters and recommended values

| Parámetro | Descripción | Default | Recomendado | Escenario |
| --- | --- | --- | --- | --- |
| `default.max_attempts` | ES: Límite general de reintentos. EN: Global retry cap. | `5` | `5` | Elección activa / Active election |
| `default.backoff_base` | ES: Base del backoff exponencial. EN: Base for exponential backoff. | `2` | `2` | Elección activa / Active election |
| `default.backoff_multiplier` | ES: Multiplicador por intento. EN: Multiplier per attempt. | `2` | `2–3` | Mantenimiento / Maintenance |
| `default.max_delay` | ES: Espera máxima entre reintentos (s). EN: Maximum delay between retries (s). | `300` | `600–900` | Mantenimiento / Maintenance |
| `default.jitter` | ES: Jitter fijo (0–1). EN: Fixed jitter (0–1). | `0.25` | `0.2–0.3` | Elección activa / Active election |
| `per_status."429".max_attempts` | ES: Reintentos ante rate-limit. EN: Retries for rate-limit. | `20` | `10–20` | Elección activa / Active election |
| `per_status."429".jitter.max` | ES: Tope de jitter para 429. EN: Jitter upper bound for 429. | `0.3` | `0.3–0.4` | Low-profile |
| `per_status."403".action` | ES: Acción ante bloqueo. EN: Action on forbidden/blocked. | `alert_only` | `alert_only` | Todos / All |
| `per_status."401".action` | ES: Credenciales inválidas. EN: Invalid credentials. | `alert_only` | `alert_only` | Todos / All |
| `per_status."5xx".max_attempts` | ES: Reintentos por errores del servidor. EN: Retries for server errors. | `8` | `6–8` | Elección activa / Active election |
| `other_status.max_attempts` | ES: Regla para códigos no listados. EN: Default for unlisted codes. | `3` | `2–3` | Mantenimiento / Maintenance |
| `per_exception.ReadTimeout.max_attempts` | ES: Reintentos por timeout. EN: Retries on timeout. | `6` | `4–6` | Elección activa / Active election |
| `timeout_seconds` | ES: Timeout por request. EN: Per-request timeout. | `30` | `20–30` | Low-profile |
| `failed_requests_path` | ES: Registro de fallos definitivos. EN: Failed requests log. | `failed_requests.jsonl` | Sin cambio / No change | Todos / All |
| `recent_snapshot_seconds` | ES: Idempotencia (evita duplicados). EN: Idempotency (avoid duplicates). | `300` | `300–600` | Mantenimiento / Maintenance |
| `idempotency_mode` | ES: Modo de idempotencia. EN: Idempotency mode. | `timestamp` | `timestamp` | Todos / All |
| `log_payload_bytes` | ES: Tamaño máximo del payload en logs. EN: Max payload bytes in logs. | `2000` | `2000` | Todos / All |

**Notas / Notes:**
- **ES:** `retry_on_status_codes` se deriva operativamente de `per_status` y `other_status`. Limitar reintentos en 401/403/400 para no amplificar bloqueos. 
- **EN:** `retry_on_status_codes` is operationally derived from `per_status` and `other_status`. Limit retries on 401/403/400 to avoid amplifying blocks.

### Escenarios recomendados / Recommended scenarios

**ES:**
- **Elección activa (cada 5–15 min):** mantener `max_attempts` moderado, backoff conservador y `jitter` para evitar sincronización.
- **Mantenimiento:** reducir reintentos y aumentar `max_delay` para minimizar presión sobre la fuente.

**EN:**
- **Active election (every 5–15 min):** keep moderate `max_attempts`, conservative backoff, and `jitter` to avoid synchronization.
- **Maintenance:** reduce retries and increase `max_delay` to minimize source pressure.

### Ejemplo comentado (elección activa) / Commented example (active election)

```yaml
# """
# ES: Configuración estándar para polling cada 5 minutos.
# EN: Standard configuration for 5-minute polling.
# """

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
  # Jitter fijo (0-1).
  # Fixed jitter (0-1).
  jitter: 0.25

per_status:
  "429":
    # Rate limit: más intentos y backoff lento.
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
log_payload_bytes: 2000
```

### Ejemplo comentado (mantenimiento) / Commented example (maintenance)

```yaml
# """
# ES: Modo mantenimiento para minimizar huella y presión.
# EN: Maintenance mode to minimize footprint and pressure.
# """

default:
  max_attempts: 3
  backoff_base: 3
  backoff_multiplier: 3
  max_delay: 900
  jitter: 0.3

per_status:
  "429":
    max_attempts: 10
    backoff_base: 10
    backoff_multiplier: 2
    max_delay: 900
    jitter:
      min: 0.2
      max: 0.4
  "403":
    max_attempts: 1
    action: "alert_only"

other_status:
  max_attempts: 2
  backoff_base: 3
  max_delay: 180
  jitter: 0.25

timeout_seconds: 25
recent_snapshot_seconds: 600
```

---

## 2) `watchdog.yaml` — Umbrales de actividad y reinicios / Activity thresholds and restarts

### Parámetros y valores recomendados / Parameters and recommended values

| Parámetro | Descripción | Default | Recomendado | Escenario |
| --- | --- | --- | --- | --- |
| `check_interval_minutes` | ES: Intervalo de chequeo (equivale a `heartbeat_interval`). EN: Check interval (equivalent to `heartbeat_interval`). | `3` | `3–5` | Mantenimiento / Maintenance |
| `max_inactivity_minutes` | ES: Máxima inactividad (equivale a `max_missed_heartbeats` sobre el intervalo). EN: Maximum inactivity (equivalent to `max_missed_heartbeats`). | `30` | `30–45` | Elección activa / Active election |
| `heartbeat_timeout` | ES: Timeout del heartbeat (s). EN: Heartbeat timeout (s). | `10` | `10–15` | Low-profile |
| `failure_grace_minutes` | ES: Ventana de gracia antes de actuar (equivale a `grace_period`). EN: Grace period before action (`grace_period`). | `6` | `6–10` | Elección activa / Active election |
| `action_cooldown_minutes` | ES: Enfriamiento entre acciones. EN: Cooldown between actions. | `10` | `10–15` | Mantenimiento / Maintenance |
| `restart_timeout_seconds` | ES: Espera máxima del reinicio (equivale a `restart_delay` operativo). EN: Max restart wait (`restart_delay`). | `30` | `30–45` | Elección activa / Active election |
| `lock_timeout_minutes` | ES: Locks considerados atascados. EN: When locks are considered stuck. | `30` | `30–45` | Mantenimiento / Maintenance |
| `max_log_growth_mb_per_min` | ES: Umbral de crecimiento de logs. EN: Log growth threshold. | `30` | `30` | Todos / All |
| `alert_urls` | ES: Destinos de alertas. EN: Alert endpoints. | `[]` | Configurar según operación / Operational | Todos / All |
| `heartbeat_path` | ES: Ruta del heartbeat. EN: Heartbeat path. | `data/heartbeat.json` | Sin cambio / No change | Todos / All |
| `pipeline_command` | ES: Comando de reinicio. EN: Restart command. | ver archivo | Ajustar a entorno | Todos / All |

### Ejemplo comentado / Commented example

```yaml
# """
# ES: Watchdog con umbrales conservadores para elecciones activas.
# EN: Watchdog with conservative thresholds for active elections.
# """

check_interval_minutes: 3
max_inactivity_minutes: 30
heartbeat_timeout: 10
failure_grace_minutes: 6
action_cooldown_minutes: 10
aggressive_restart: false
alert_urls: []
log_path: "logs/centinel.log"
max_log_growth_mb_per_min: 30
lock_files:
  - "data/temp/pipeline.lock"
lock_timeout_minutes: 30
heartbeat_path: "data/heartbeat.json"
pipeline_command:
  - "python"
  - "scripts/run_pipeline.py"
restart_timeout_seconds: 30
```

---

## 3) `proxies.yaml` — Rotación de proxies y validación / Proxy rotation and validation

### Parámetros y valores recomendados / Parameters and recommended values

| Parámetro | Descripción | Default | Recomendado | Escenario |
| --- | --- | --- | --- | --- |
| `mode` | ES: Modo del rotador. EN: Rotator mode. | `proxy_rotator` | `proxy_rotator` | Todos / All |
| `rotation_strategy` | ES: Estrategia de rotación. EN: Rotation strategy. | `round_robin` | `round_robin` | Todos / All |
| `rotation_every_n` | ES: Rotar cada N requests. EN: Rotate every N requests. | `1` | `1–2` | Low-profile |
| `proxy_timeout_seconds` | ES: Timeout de prueba. EN: Proxy test timeout. | `15` | `10–15` | Elección activa / Active election |
| `test_url` | ES: Endpoint de validación (HEAD). EN: Validation endpoint (HEAD). | `https://httpbin.org/ip` | Endpoint estable | Todos / All |
| `proxies[]` | ES: Lista de proxies (http/socks5). EN: Proxy list (http/socks5). | (ejemplo) | 2–5 proxies validados | Elección activa / Active election |

### Ejemplo comentado / Commented example

```yaml
# """
# ES: Lista de proxies con validación y rotación round-robin.
# EN: Proxy list with validation and round-robin rotation.
# """

mode: proxy_rotator
rotation_strategy: round_robin
rotation_every_n: 1
proxy_timeout_seconds: 15
test_url: https://httpbin.org/ip
proxies:
  # Formato: esquema://[user:pass@]ip:port
  # Format: scheme://[user:pass@]ip:port
  - "http://user:pass@ip:port"
  - "socks5://ip:port"
```

### Validación, rotación y fallback / Validation, rotation, and fallback

**ES:** Validar cada proxy con una solicitud **HEAD** a `test_url` y registrar latencia. Usar rotación **round-robin** para distribuir carga. Si todos fallan, activar **fallback** a conexión directa con alertas y reducir cadencia para evitar presión sobre la fuente.

**EN:** Validate each proxy with a **HEAD** request to `test_url` and record latency. Use **round-robin** rotation to distribute load. If all fail, enable **fallback** to direct connection with alerts and reduce cadence to avoid source pressure.

---

## 4) `rules.yaml` — Reglas de anomalías / Anomaly rules

### Parámetros y valores recomendados / Parameters and recommended values

| Parámetro | Descripción | Default | Recomendado | Escenario |
| --- | --- | --- | --- | --- |
| `reglas_auditoria[].nombre` | ES: Identificador estable. EN: Stable rule identifier. | ver archivo | Mantener estable | Todos / All |
| `reglas_auditoria[].descripcion` | ES: Propósito de la regla. EN: Rule purpose. | ver archivo | Describir criterio estadístico | Todos / All |
| `reglas_auditoria[].thresholds` | ES: Umbrales porcentuales. EN: Percentage thresholds. | (opcional) | Documentar por elección | Elección activa / Active election |
| `resiliencia.retry_max` | ES: Reintentos sugeridos (documentación). EN: Suggested retry cap. | `5` | `3–5` | Low-profile |
| `resiliencia.backoff_factor` | ES: Backoff sugerido. EN: Suggested backoff factor. | `2` | `2–3` | Low-profile |
| `resiliencia.chi2_p_critical` | ES: Umbral crítico chi-cuadrado. EN: Chi-square critical threshold. | `0.01` | `0.01` | Todos / All |
| `resiliencia.benford_min_samples` | ES: Mínimo de muestras Benford. EN: Minimum samples for Benford. | `10` | `10–20` | Elección activa / Active election |

### Ejemplo comentado / Commented example

```yaml
# """
# ES: Reglas básicas con umbrales y ejemplos de entrada/salida.
# EN: Baseline rules with thresholds and input/output examples.
# """

reglas_auditoria:
  - nombre: "apply_benford_law"
    # Evalúa primer dígito con Ley de Benford.
    # Evaluates first digit with Benford's Law.
    descripcion: "Evalúa primer dígito con Ley de Benford y prueba chi-cuadrado."

  - nombre: "check_distribution_chi2"
    # Compara distribución partido/departamento.
    # Compares party/department distribution.
    descripcion: "Compara distribución partido/departamento contra esperados proporcionales."
    thresholds:
      percent_deviation: 0.12

resiliencia:
  retry_max: 5
  backoff_factor: 2
  chi2_p_critical: 0.01
  benford_min_samples: 10
```

### Cómo agregar nuevas reglas / How to add new rules

**ES:** Añadir una nueva entrada en `reglas_auditoria` con `nombre`, `descripcion`, ejemplos de entrada/salida y `thresholds`. Mantener la nomenclatura estable para trazabilidad y registrar la regla en [docs/rules.md](rules.md).

**EN:** Add a new entry in `reglas_auditoria` with `nombre`, `descripcion`, input/output examples, and `thresholds`. Keep naming stable for traceability and register the rule in [docs/rules.md](rules.md).

---

<a id="circuit-breaker-y-low-profile"></a>
## Circuit breaker y low-profile / Circuit breaker and low-profile

**ES:** El circuito de corte (circuit breaker) limita la insistencia cuando la fuente pública responde con fallos persistentes (p. ej. 429 o 5xx). Se recomienda pausar o espaciar el polling cuando se superan umbrales de fallo consecutivo, registrando el evento en logs y `failed_requests.jsonl`. El modo **low-profile** complementa este enfoque ajustando `max_attempts`, `max_delay` y `jitter` para reducir la huella operativa sin perder evidencia técnica.

**EN:** The circuit breaker limits retries when the public source returns persistent failures (e.g., 429 or 5xx). It is recommended to pause or space polling when consecutive failure thresholds are exceeded, recording the event in logs and `failed_requests.jsonl`. **Low-profile** mode complements this by tuning `max_attempts`, `max_delay`, and `jitter` to reduce operational footprint without losing technical evidence.

---

## Mejores prácticas y escenarios operativos / Best practices and operational scenarios

### Elección activa (cadencia 5–15 min) / Active election (5–15 min cadence)

**ES:**
- Usar backoff conservador con `jitter` para evitar sincronización de solicitudes.
- Limitar reintentos en `401/403/400` y activar alertas tempranas para mitigar bloqueos.
- Validar proxies al inicio del turno y usar rotación round-robin; si hay degradación, aplicar fallback con cadencia reducida.
- Mantener watchdog con intervalos cortos para detectar inactividad sin reinicios agresivos.

**EN:**
- Use conservative backoff with `jitter` to avoid request synchronization.
- Limit retries on `401/403/400` and trigger early alerts to mitigate blocks.
- Validate proxies at the start of the shift and use round-robin rotation; if degraded, apply fallback with reduced cadence.
- Keep the watchdog on short intervals to detect inactivity without aggressive restarts.

### Mantenimiento / Maintenance

**ES:**
- Incrementar `max_inactivity_minutes` y `action_cooldown_minutes` para minimizar reinicios.
- Reducir `rotation_every_n` o desactivar proxies si no hay necesidad operativa.
- Mantener `timeout_seconds` moderados para liberar recursos de forma limpia.

**EN:**
- Increase `max_inactivity_minutes` and `action_cooldown_minutes` to minimize restarts.
- Reduce `rotation_every_n` or disable proxies when not operationally required.
- Keep `timeout_seconds` moderate to release resources cleanly.

### Low-profile / Low-profile

**ES:**
- Reducir `max_attempts` y aumentar `max_delay` para disminuir la huella.
- Evitar patrones previsibles en la cadencia, combinando `jitter` y ventanas de ejecución.

**EN:**
- Reduce `max_attempts` and increase `max_delay` to lower footprint.
- Avoid predictable cadence patterns by combining `jitter` and execution windows.

---

## Seguridad y confidencialidad / Security and confidentiality

**ES:**
- No exponer credenciales de proxies en repositorios públicos; usar variables de entorno o secretos externos.
- Limitar el acceso a logs que incluyan IPs de salida o rutas internas.
- Versionar cambios de configuración con mensajes claros para trazabilidad.

**EN:**
- Do not expose proxy credentials in public repositories; use environment variables or external secrets.
- Restrict access to logs that include egress IPs or internal paths.
- Version configuration changes with clear messages for traceability.

---

## Troubleshooting y evidencias / Troubleshooting and evidence

**ES:**
- Revisar `failed_requests.jsonl` para fallos definitivos, códigos HTTP y payloads truncados.
- Verificar `logs/centinel.log` y `data/heartbeat.json` para detectar inactividad o reinicios del watchdog.
- Si hay bloqueos recurrentes, reducir `max_attempts`, aumentar `max_delay` y habilitar alertas tempranas.

**EN:**
- Review `failed_requests.jsonl` for definitive failures, HTTP codes, and truncated payloads.
- Check `logs/centinel.log` and `data/heartbeat.json` to detect inactivity or watchdog restarts.
- If recurring blocks occur, reduce `max_attempts`, increase `max_delay`, and enable early alerts.

---

**Configuración clave / Key configuration**
- `chaos.level`: severidad (`low`, `medium`, `high`) con límites conservadores.
- `chaos.duration_minutes`: duración total del ejercicio.
- `chaos.failure_probability`: probabilidad de fallo por request (0–1).
- `chaos.scenarios_enabled`: escenarios CNE habilitados (429, 503, JSON inválido, hash alterado, proxy fail, watchdog, respuesta lenta).
- `chaos.max_recovery_seconds`: umbral máximo de recuperación para validar continuidad.

**Ejecución manual / Manual run**
```bash
python scripts/chaos_test.py --config chaos_config.yaml.example --level low
```

**ES:** La resiliencia documentada aporta **reproducibilidad** (parámetros explícitos, registros de fallos, cadencias declaradas) y **trazabilidad** (hashes y snapshots verificables), lo que facilita auditorías independientes y fortalece la confianza de observadores internacionales en la neutralidad y consistencia técnica del monitoreo.

**EN:** Documented resilience provides **reproducibility** (explicit parameters, failure logs, declared cadences) and **traceability** (verifiable hashes and snapshots), enabling independent audits and strengthening international observers’ confidence in the neutrality and technical consistency of the monitoring.
