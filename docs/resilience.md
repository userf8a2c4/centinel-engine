# Resiliencia operativa y tolerancia a fallos / Operational Resilience and Fault Tolerance

## Introducción formal / Formal introduction

**ES:** La resiliencia en auditoría electoral digital busca mantener la continuidad, integridad y verificabilidad del monitoreo cuando las fuentes públicas presentan **rate-limits, timeouts, fingerprinting o bloqueos temporales**. En el contexto de CENTINEL, el pipeline consulta JSON públicos del CNE con una cadencia típica de **cada 5 minutos** durante elección activa. La estrategia es defensiva: **reintentos controlados, backoff con jitter, rotación de proxies y watchdogs** minimizan la presión sobre la fuente, documentan fallos y preservan evidencia reproducible para observadores técnicos internacionales (OEA, Carter Center, IDEA, NED, Luminate). 

**EN:** Resilience in digital electoral auditing aims to preserve continuity, integrity, and verifiability when public sources face **rate limits, timeouts, fingerprinting, or temporary blocks**. In CENTINEL, the pipeline polls public CNE JSON with a typical **5-minute cadence** during active elections. The approach is defensive: **controlled retries, backoff with jitter, proxy rotation, and watchdog thresholds** minimize pressure on the source, document failures, and preserve reproducible evidence for international technical observers (OAS, Carter Center, IDEA, NED, Luminate).

**Enlaces internos / Internal links:**
- [README principal / Main README](../README.md)
- [Documentación general / Documentation index](README.md)
- [Arquitectura / Architecture](architecture.md)
- [Reglas de auditoría / Audit rules](rules.md)
- [Principios operativos / Operating principles](operating_principles.md)

---

## 1) `retry_config.yaml` — Reintentos, backoff y jitter / Retries, backoff, and jitter

### Parámetros y valores recomendados / Parameters and recommended values

| Parámetro | Descripción (ES) | Description (EN) | Valor por defecto | Recomendado |
| --- | --- | --- | --- | --- |
| `default.max_attempts` | Límite general de reintentos. | Global retry cap. | `5` | Normal: `5`. Low-profile: `3–5`. |
| `default.backoff_base` | Base del backoff exponencial. | Base for exponential backoff. | `2` | Normal: `2`. Low-profile: `3–5`. |
| `default.backoff_multiplier` | Multiplicador por intento. | Multiplier per attempt. | `2` | Normal: `2`. Low-profile: `2–3`. |
| `default.max_delay` | Espera máxima entre reintentos (s). | Maximum delay between retries (s). | `300` | Normal: `300`. Low-profile: `600–900`. |
| `default.jitter` | Jitter fijo (0–1). | Fixed jitter (0–1). | `0.25` | Normal: `0.2–0.3`. Low-profile: `0.3–0.4`. |
| `per_status` | Reglas específicas por HTTP. | Status-specific rules. | (ver archivo) | Ajustar 429/5xx/403 con enfoque defensivo. |
| `per_status."429".max_attempts` | Reintentos ante rate-limit. | Retries for rate-limit. | `20` | Normal: `10–20`. Low-profile: `8–12`. |
| `per_status."429".backoff_base` | Base de backoff para 429. | Backoff base for 429. | `8` | Normal: `8`. Low-profile: `8–10`. |
| `per_status."429".jitter.max` (jitter_max) | Tope de jitter en rango. | Jitter upper bound in range. | `0.3` | Normal: `0.3`. Low-profile: `0.4`. |
| `per_status."403".action` | Acción ante bloqueo. | Action on blocked/forbidden. | `alert_only` | Mantener en `alert_only`. |
| `retry_on_status_codes` | Conjunto de códigos reintentables (derivado de `per_status` y `other_status`). | Retryable status codes (derived from `per_status` and `other_status`). | (implícito) | Documentar 429/5xx y limitar 401/403. |
| `per_exception.ReadTimeout` | Reintentos por timeout. | Retries on timeout. | `max_attempts: 6` | Normal: `4–6`. Low-profile: `3–5`. |
| `other_status` | Regla para códigos no listados. | Default for unlisted codes. | (ver archivo) | Normal: `max_attempts 3`. Low-profile: `2`. |
| `timeout_seconds` | Timeout por request. | Per-request timeout. | `30` | Normal: `30`. Low-profile: `20–30`. |
| `recent_snapshot_seconds` | Idempotencia (evita duplicados). | Idempotency (avoid duplicates). | `300` | Normal: `300`. Low-profile: `300–600`. |

### Ejemplo comentado (normal) / Commented example (normal)

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
recent_snapshot_seconds: 300
```

### Ejemplo comentado (low-profile) / Commented example (low-profile)

```yaml
# """
# ES: Modo low-profile para minimizar huella y presión sobre la fuente.
# EN: Low-profile mode to minimize footprint and source pressure.
# """

default:
  max_attempts: 4
  backoff_base: 4
  backoff_multiplier: 2
  max_delay: 600
  jitter: 0.35

per_status:
  "429":
    max_attempts: 10
    backoff_base: 8
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

| Parámetro | Descripción (ES) | Description (EN) | Valor por defecto | Recomendado |
| --- | --- | --- | --- | --- |
| `check_interval_minutes` | Frecuencia de chequeo. | Watchdog check interval. | `3` | Normal: `3`. Low-profile: `3–5`. |
| `max_inactivity_minutes` | Máxima inactividad permitida. | Maximum allowed inactivity. | `30` | Normal: `30`. Mantenimiento: `45–60`. |
| `heartbeat_timeout` | Timeout de heartbeat (s). | Heartbeat timeout (s). | `10` | Normal: `10`. Low-profile: `10–15`. |
| `failure_grace_minutes` | Ventana de gracia antes de actuar. | Grace period before action. | `6` | Normal: `6–10`. |
| `action_cooldown_minutes` | Cooldown entre acciones. | Cooldown between actions. | `10` | Normal: `10–15`. |
| `restart_timeout_seconds` | Espera máxima de reinicio. | Max restart wait. | `30` | Normal: `30–45`. |
| `lock_timeout_minutes` | Locks considerados atascados. | When locks are considered stuck. | `30` | Normal: `30`. Mantenimiento: `45`. |
| `max_log_growth_mb_per_min` | Umbral de crecimiento de logs. | Log growth threshold. | `30` | Normal: `30`. |
| `alert_urls` | Destinos de alerta. | Alert endpoints. | `[]` | Configurar según operación. |

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
restart_timeout_seconds: 30
```

---

## 3) `proxies.yaml` — Rotación de proxies y validación / Proxy rotation and validation

### Parámetros y valores recomendados / Parameters and recommended values

| Parámetro | Descripción (ES) | Description (EN) | Valor por defecto | Recomendado |
| --- | --- | --- | --- | --- |
| `mode` | Modo del rotador. | Rotator mode. | `proxy_rotator` | Mantener `proxy_rotator`. |
| `rotation_strategy` | Estrategia de rotación. | Rotation strategy. | `round_robin` | `round_robin` para equidad. |
| `rotation_every_n` | Rotar cada N requests. | Rotate every N requests. | `1` | Normal: `1`. Low-profile: `1–2`. |
| `proxy_timeout_seconds` | Timeout de prueba. | Proxy test timeout. | `15` | Normal: `10–15`. |
| `test_url` | Endpoint de validación. | Validation endpoint. | `https://httpbin.org/ip` | Usar endpoint estable de salida. |
| `proxies[]` | Lista de proxies. | Proxy list. | (ejemplo) | Rotar 2–5 proxies validados. |
| `validation_method` | Método de validación (HEAD o ping) con timeout corto. | Validation method (HEAD or ping) with short timeout. | (implícito) | Preferir `HEAD` a `test_url`. |
| `fallback` | Comportamiento si fallan todos los proxies. | Fallback behavior if all proxies fail. | (implícito) | Fallback a conexión directa con alertas. |

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

### Validación y fallback / Validation and fallback

**ES:** Validar cada proxy con una solicitud **HEAD** a `test_url` o con un ping de baja carga. Si todos fallan, activar **fallback** a conexión directa con alertas y reducir la cadencia para evitar presión sobre la fuente. 

**EN:** Validate each proxy with a low-cost **HEAD** request to `test_url` or a lightweight ping. If all fail, enable **fallback** to direct connection with alerts and reduce cadence to avoid source pressure.

---

## 4) `rules.yaml` — Reglas de anomalías / Anomaly rules

### Parámetros y valores recomendados / Parameters and recommended values

| Parámetro | Descripción (ES) | Description (EN) | Valor por defecto | Recomendado |
| --- | --- | --- | --- | --- |
| `reglas_auditoria[].nombre` | Identificador de la regla. | Rule identifier. | (ver archivo) | Mantener nombres estables. |
| `reglas_auditoria[].descripcion` | Descripción de propósito. | Purpose description. | (ver archivo) | Incluir criterio estadístico. |
| `resiliencia.retry_max` | Reintentos sugeridos. | Suggested retry cap. | `5` | `3–5` según cadencia. |
| `resiliencia.backoff_factor` | Backoff sugerido. | Suggested backoff factor. | `2` | `2–3` en low-profile. |
| `resiliencia.chi2_p_critical` | Umbral crítico chi-cuadrado. | Chi-square critical threshold. | `0.01` | `0.01` (estricto). |
| `resiliencia.benford_min_samples` | Mínimo de muestras para Benford. | Minimum samples for Benford. | `10` | `10–20` según nivel. |
| `thresholds` | Umbrales porcentuales por regla. | Percentage thresholds per rule. | (definir) | Documentar por elección. |

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

## Mejores prácticas y escenarios operativos / Best practices and operational scenarios

### Elección activa (cadencia 5–15 min) / Active election (5–15 min cadence)

**ES:**
- Priorizar backoff más lento y `jitter` moderado para evitar sincronización de solicitudes.
- Limitar reintentos en `401/403` y activar alertas tempranas para mitigar bloqueos.
- Validar proxies al inicio del turno y usar rotación round-robin; si hay degradación, aplicar fallback con cadencia reducida.
- Mantener `watchdog` con intervalos cortos para detectar inactividad sin reinicios agresivos.

**EN:**
- Prefer slower backoff and moderate `jitter` to avoid request synchronization.
- Limit retries on `401/403` and trigger early alerts to mitigate blocks.
- Validate proxies at the beginning of the shift and use round-robin rotation; if degraded, apply fallback with reduced cadence.
- Keep the watchdog on short intervals to detect inactivity without aggressive restarts.

### Mantenimiento mensual / Monthly maintenance

**ES:**
- Incrementar `max_inactivity_minutes` y `action_cooldown_minutes` para minimizar reinicios.
- Reducir `rotation_every_n` o desactivar proxies si no hay necesidad operativa.
- Mantener `timeout_seconds` bajos para liberar recursos de forma limpia.

**EN:**
- Increase `max_inactivity_minutes` and `action_cooldown_minutes` to minimize restarts.
- Reduce `rotation_every_n` or disable proxies when not operationally required.
- Keep `timeout_seconds` low to release resources cleanly.

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

## 5) Chaos Testing — Condiciones adversas realistas / Realistic adverse conditions

**Qué hace / What it does**
- **ES:** Ejecuta chaos engineering con fallos CNE Honduras (rate-limit 429, timeouts 503, JSON inválido, hashes alterados, fallas de proxy, latencia elevada y pérdida de heartbeat del watchdog). Estos escenarios refuerzan la credibilidad del monitoreo electoral ante misiones internacionales al demostrar recuperación controlada y trazable.
- **EN:** Runs chaos engineering with Honduras CNE failures (429 rate limits, 503 timeouts, invalid JSON, altered hashes, proxy failures, elevated latency, and watchdog heartbeat loss). These scenarios strengthen credibility for international missions by demonstrating controlled, traceable recovery.

**Componentes / Components**
- **scripts/chaos_test.py:** Script principal con mocks HTTP usando `responses`, métricas de recuperación y reporte formal.
- **chaos_config.yaml.example:** Configuración de nivel, duración, probabilidad de fallas y escenarios habilitados.
- **.github/workflows/chaos-test.yml:** Ejecución automática en PRs (modo low por defecto) y en pushes.

**Ejecución manual / Manual run**
```bash
python scripts/chaos_test.py --config chaos_config.yaml.example --level low
```

**Verificación de recuperación / Recovery validation**
- **ES:** Cada falla abre una ventana de recuperación. El test falla si no se observa un éxito posterior dentro del `max_recovery_seconds`.
- **EN:** Each failure opens a recovery window. The test fails if no subsequent success occurs within `max_recovery_seconds`.

**Notas de credibilidad / Credibility notes**
- **ES:** Los reportes incluyen métricas de resiliencia (success/failure, tiempo de recuperación, escenarios activados) para auditoría independiente.
- **EN:** Reports include resilience metrics (success/failure, recovery time, activated scenarios) for independent audit review.
