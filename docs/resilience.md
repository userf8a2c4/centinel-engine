# Resiliencia operativa y tolerancia a fallos / Operational Resilience and Fault Tolerance

## Introducción formal / Formal introduction

**ES:** La resiliencia en auditoría electoral digital garantiza continuidad, integridad y verificabilidad cuando las fuentes públicas presentan **rate-limits, timeouts, fingerprinting o bloqueos temporales**. En C.E.N.T.I.N.E.L., el pipeline consulta JSON públicos del CNE con cadencia típica de **cada 5 minutos** en elección activa. La estrategia es defensiva y proporcional: **reintentos controlados, backoff con jitter, rotación de proxies y watchdogs** reducen presión sobre la fuente, documentan fallos y preservan evidencia reproducible para observadores internacionales (OEA, Carter Center).

**EN:** Resilience in digital electoral auditing preserves continuity, integrity, and verifiability when public sources experience **rate limits, timeouts, fingerprinting, or temporary blocks**. In C.E.N.T.I.N.E.L., the pipeline polls public CNE JSON on a typical **5-minute cadence** during active elections. The approach is defensive and proportional: **controlled retries, backoff with jitter, proxy rotation, and watchdog thresholds** reduce pressure on the source, document failures, and preserve reproducible evidence for international observers (OAS, Carter Center).

**Enlaces internos / Internal links:**
- [README principal / Main README](../README.md)
- [Índice de documentación / Documentation index](README.md)
- [Arquitectura / Architecture](architecture.md)
- [Reglas de auditoría / Audit rules](rules.md)
- [Principios operativos / Operating principles](operating_principles.md)
- [Seguridad / Security](security.md)

---

## 1) `retry_config.yaml` — Reintentos, backoff y jitter / Retries, backoff, and jitter

### Ecuaciones de backoff y jitter / Backoff and jitter equations

**ES:** Para el intento `n` (empezando en 0), el tiempo de espera se modela como:

**EN:** For attempt `n` (starting at 0), the wait time is modeled as:

\[
t_n = \text{base} \cdot 2^{n} + J
\]

**ES:** donde el jitter `J` suele ser una variable aleatoria uniforme `J \sim U(0, j_{max})`. El valor esperado es:

**EN:** where jitter `J` is typically a uniform random variable `J \sim U(0, j_{max})`. The expected value is:

\[
\mathbb{E}[t_n] = \text{base} \cdot 2^{n} + \frac{j_{max}}{2}
\]

**ES:** El jitter reduce colisiones porque desincroniza clientes que fallan al mismo tiempo. Si `N` clientes reintentan en una ventana `T` y se considera una colisión cuando dos caen en el mismo sub-intervalo `w`, la probabilidad aproximada de colisión por cliente se reduce a:

**EN:** Jitter reduces collisions by desynchronizing clients that fail at the same time. If `N` clients retry within a window `T` and a collision is defined as two clients landing in the same sub-interval `w`, an approximate collision probability per client is reduced to:

\[
P(\text{colisión}) \approx 1 - \left(1 - \frac{w}{T}\right)^{N-1}
\]

**ES:** Al aumentar la aleatoriedad (`j_{max}` más amplio), se incrementa `T` efectivo y disminuye la probabilidad de reintentos simultáneos. Esto reduce presión sobre el endpoint y evita bloqueos por patrones de tráfico repetitivo.

**EN:** Increasing randomness (wider `j_{max}`) effectively increases `T`, decreasing the chance of synchronized retries. This reduces pressure on the endpoint and avoids blocks caused by repetitive traffic patterns.

### Umbral de circuit breaker / Circuit breaker threshold

**ES:** El circuito se abre cuando el número de fallos en la ventana `W` supera `k`:

**EN:** The circuit opens when the number of failures within window `W` exceeds `k`:

\[
\text{OPEN si } f_W \ge k
\]

**ES:** Esta regla evita reintentos agresivos cuando la fuente presenta fallos persistentes (429/5xx), permitiendo usar snapshots locales como fallback sin perder continuidad operativa.

**EN:** This rule avoids aggressive retries when the source returns persistent failures (429/5xx), enabling local snapshot fallback without losing operational continuity.

### Parámetros y valores recomendados / Parameters and recommended values

| Parámetro | Descripción | Default | Recomendado | Escenario |
| --- | --- | --- | --- | --- |
| `default.max_attempts` | ES: Límite general de reintentos. EN: Global retry cap. | `5` | Normal: `5` / Low-profile: `3` | Elección activa y mantenimiento / Active election & maintenance |
| `default.backoff_multiplier` | ES: Multiplicador por intento. EN: Multiplier per attempt. | `2` | Normal: `2` / Low-profile: `3` | Mantenimiento / Maintenance |
| `default.jitter` | ES: Jitter fijo (0–1). EN: Fixed jitter (0–1). | `0.25` | Normal: `0.2–0.3` / Low-profile: `0.3–0.4` | Elección activa / Active election |
| `per_status."429".max_attempts` | ES: Reintentos ante rate-limit. EN: Retries for rate-limit. | `20` | Normal: `10–20` / Low-profile: `6–10` | Elección activa / Active election |
| `per_status."5xx".max_attempts` | ES: Reintentos por errores del servidor. EN: Retries for server errors. | `8` | Normal: `6–8` / Low-profile: `3–5` | Elección activa / Active election |
| `per_exception.ReadTimeout.max_attempts` | ES: Reintentos por timeout. EN: Retries on timeout. | `6` | Normal: `4–6` / Low-profile: `3–4` | Elección activa / Active election |
| `timeout_seconds` | ES: Timeout por request. EN: Per-request timeout. | `30` | Normal: `20–30` / Low-profile: `20–25` | Low-profile |
| `failed_requests_path` | ES: Registro de fallos definitivos. EN: Failed requests log. | `failed_requests.jsonl` | Sin cambio / No change | Todos / All |

**Notas de compatibilidad / Compatibility notes:**
- **ES:** `retry_on_status_codes` se implementa por composición con `per_status` y `other_status`. Limite reintentos en `401/403/400` para no amplificar bloqueos. **EN:** `retry_on_status_codes` is implemented by composition via `per_status` and `other_status`. Limit retries on `401/403/400` to avoid amplifying blocks.
- **ES:** `jitter_max` puede expresarse como `jitter.max` cuando el jitter es un rango; en `retry_config.yaml` se usa `jitter` como número fijo o como objeto `{min, max}`. **EN:** `jitter_max` can be expressed as `jitter.max` when jitter is a range; in `retry_config.yaml` jitter is defined as a fixed number or a `{min, max}` object.

### Ejemplo comentado (elección activa) / Commented example (active election)

```yaml
# ES: Configuración estándar para polling cada 5 minutos.
# EN: Standard configuration for 5-minute polling.

default:
  # ES: Intentos máximos por solicitud.
  # EN: Maximum attempts per request.
  max_attempts: 5
  # ES: Multiplicador por intento.
  # EN: Multiplier per attempt.
  backoff_multiplier: 2
  # ES: Jitter fijo (0-1).
  # EN: Fixed jitter (0-1).
  jitter: 0.25

per_status:
  "429":
    # ES: Rate limit: más intentos y backoff lento.
    # EN: Rate limit: more attempts and slower backoff.
    max_attempts: 20
    backoff_multiplier: 2
    jitter:
      min: 0.1
      max: 0.3
  "5xx":
    # ES: Errores del servidor: reintentos moderados.
    # EN: Server errors: moderate retries.
    max_attempts: 8
  "403":
    # ES: Bloqueo: alertar sin insistir.
    # EN: Forbidden/block: alert without heavy retry.
    max_attempts: 2
    action: "alert_only"

per_exception:
  ReadTimeout:
    # ES: Timeout de lectura: reintentos moderados.
    # EN: Read timeout: moderate retries.
    max_attempts: 6

timeout_seconds: 30
failed_requests_path: failed_requests.jsonl
```

---

## 2) `watchdog.yaml` — Umbrales de actividad y reinicios / Activity thresholds and restarts

### Parámetros y valores recomendados / Parameters and recommended values

| Parámetro | Descripción | Default | Recomendado | Escenario |
| --- | --- | --- | --- | --- |
| `heartbeat_interval` | ES: Intervalo de heartbeat. EN: Heartbeat interval. | `3 min` | Normal: `3–5 min` / Low-profile: `5–10 min` | Mantenimiento / Maintenance |
| `max_missed_heartbeats` | ES: Umbral de heartbeats perdidos. EN: Threshold of missed heartbeats. | `10` | Normal: `8–12` / Low-profile: `12–18` | Elección activa / Active election |
| `grace_period` | ES: Ventana de gracia antes de actuar. EN: Grace period before action. | `6 min` | Normal: `6–10 min` / Low-profile: `10–15 min` | Elección activa / Active election |
| `restart_delay` | ES: Espera antes del reinicio. EN: Delay before restart. | `30 s` | Normal: `30–45 s` / Low-profile: `45–60 s` | Mantenimiento / Maintenance |
| `resource_check_interval_seconds` | ES: Frecuencia de chequeo CPU/MEM. EN: CPU/MEM check cadence. | `30 s` | Normal: `30–60 s` | Elección activa / Active election |
| `max_cpu_percent` | ES: Umbral máximo de CPU. EN: Max CPU threshold. | `80` | Normal: `75–85` | Todos / All |
| `max_mem_percent` | ES: Umbral máximo de memoria. EN: Max memory threshold. | `90` | Normal: `85–92` | Todos / All |
| `restart_on_fail` | ES: Auto-recuperación. EN: Auto-recovery. | `true` | `true` | Todos / All |

**Notas de compatibilidad / Compatibility notes:**
- **ES:** En `watchdog.yaml`, `heartbeat_interval` corresponde a `check_interval_minutes`. `max_missed_heartbeats` se deriva de `max_inactivity_minutes / check_interval_minutes`. `grace_period` corresponde a `failure_grace_minutes` y `restart_delay` a `restart_timeout_seconds`. **EN:** In `watchdog.yaml`, `heartbeat_interval` maps to `check_interval_minutes`. `max_missed_heartbeats` is derived from `max_inactivity_minutes / check_interval_minutes`. `grace_period` maps to `failure_grace_minutes` and `restart_delay` to `restart_timeout_seconds`.

### Ejemplo comentado / Commented example

```yaml
# ES: Watchdog con umbrales conservadores para elecciones activas.
# EN: Watchdog with conservative thresholds for active elections.

check_interval_minutes: 3
max_inactivity_minutes: 30
failure_grace_minutes: 6
restart_timeout_seconds: 30
heartbeat_timeout: 10
# EN: Resource check every 30 seconds.
# ES: Chequeo de recursos cada 30 segundos.
resource_check_interval_seconds: 30
# EN: CPU/MEM thresholds.
# ES: Umbrales de CPU/MEM.
max_cpu_percent: 80
max_mem_percent: 90
# EN: Auto-restart on failures.
# ES: Reinicio automático ante fallos.
restart_on_fail: true
alert_urls: []
log_path: "logs/centinel.log"
lock_files:
  - "data/temp/pipeline.lock"
heartbeat_path: "data/heartbeat.json"
pipeline_command:
  - "python"
  - "scripts/run_pipeline.py"
```

---

## 3) `proxies.yaml` — Rotación de proxies y validación / Proxy rotation and validation

### Parámetros y valores recomendados / Parameters and recommended values

| Parámetro | Descripción | Default | Recomendado | Escenario |
| --- | --- | --- | --- | --- |
| `mode` | ES: Modo del rotador. EN: Rotator mode. | `proxy_rotator` | `direct` por defecto, `proxy_rotator` solo para resiliencia | Todos / All |
| `rotation_strategy` | ES: Estrategia de rotación. EN: Rotation strategy. | `round_robin` | `round_robin` | Todos / All |
| `rotation_every_n` | ES: Rotar cada N requests. EN: Rotate every N requests. | `1` | Defensivo: `3–10` (evitar rotación agresiva) | Low-profile |
| `proxy_timeout_seconds` | ES: Timeout de validación y uso del proxy. EN: Proxy validation and request timeout. | `15` | Normal: `10–15` / Low-profile: `15–20` | Elección activa / Active election |
| `test_url` | ES: Endpoint de validación (GET liviano). EN: Validation endpoint (light GET). | `https://httpbin.org/ip` | Endpoint estable y de bajo costo | Todos / All |
| `proxies[]` | ES: Lista de proxies (http/socks5). EN: Proxy list (http/socks5). | (ejemplo) | Normal: `2–5` / Low-profile: `1–2` | Elección activa / Active election |

### Ejemplo comentado / Commented example

```yaml
# ES: Perfil defensivo: por defecto directo, habilitar rotación solo si hay necesidad operativa.
# EN: Defensive profile: direct by default, enable rotation only when operationally needed.

mode: direct
rotation_strategy: round_robin
rotation_every_n: 5
proxy_timeout_seconds: 15
test_url: https://httpbin.org/ip
proxies:
  # ES: Formato esquema://[user:pass@]ip:port
  # EN: Format scheme://[user:pass@]ip:port
  - "http://user:pass@ip:port"
  - "socks5://ip:port"
```

### Validación, rotación y fallback / Validation, rotation, and fallback

**ES:** Validar cada proxy con una solicitud **GET liviana** a `test_url` y registrar latencia. Usar rotación **round-robin** para distribuir carga, no para evasión. Si todos fallan, activar **fallback** a conexión directa con alertas y reducir cadencia para evitar presión sobre la fuente.

**EN:** Validate each proxy with a **light GET** request to `test_url` and record latency. Use **round-robin** rotation for load distribution, not evasion. If all fail, enable **fallback** to direct connection with alerts and reduce cadence to avoid source pressure.

### Arquitectura defensiva sugerida / Suggested defensive architecture

1. **Direct-first policy / Política direct-first**
   - **ES:** Iniciar en `mode: direct` y activar `proxy_rotator` únicamente cuando exista degradación técnica comprobada (caídas de egress, timeouts, rutas inestables).
   - **EN:** Start in `mode: direct` and enable `proxy_rotator` only when there is confirmed technical degradation (egress outages, timeouts, unstable routes).
2. **Health-based failover / Failover por salud**
   - **ES:** Revalidar pool antes de cada ventana crítica y tras agotar proxies activos. El sistema ya marca un proxy como muerto tras 3 fallos consecutivos y hace fallback a directo cuando no quedan activos.
   - **EN:** Revalidate the pool before each critical window and after exhausting active proxies. The system already marks a proxy as dead after 3 consecutive failures and falls back to direct mode when none remain.
3. **Slow rotation / Rotación lenta**
   - **ES:** Preferir `rotation_every_n` entre `3` y `10` para evitar cambios de IP por cada request.
   - **EN:** Prefer `rotation_every_n` between `3` and `10` to avoid IP switching on every request.
4. **Circuit breaker + cadence / Circuit breaker + cadencia**
   - **ES:** Ante 429/5xx persistentes, priorizar backoff y reducción de frecuencia de polling antes de aumentar rotación.
   - **EN:** On persistent 429/5xx responses, prioritize backoff and lower polling frequency before increasing rotation.
5. **Traceability / Trazabilidad**
   - **ES:** Mantener logs de `proxy_validation_ok`, `proxy_marked_failure`, `proxy_marked_dead` y `proxy_fallback_direct` para auditoría técnica.
   - **EN:** Keep logs for `proxy_validation_ok`, `proxy_marked_failure`, `proxy_marked_dead`, and `proxy_fallback_direct` for technical auditing.

---

## 4) `rules.yaml` — Reglas de anomalías / Anomaly rules

### Parámetros y valores recomendados / Parameters and recommended values

| Parámetro | Descripción | Default | Recomendado | Escenario |
| --- | --- | --- | --- | --- |
| `reglas_auditoria[].nombre` | ES: Identificador estable. EN: Stable rule identifier. | ver archivo | Mantener estable | Todos / All |
| `reglas_auditoria[].descripcion` | ES: Propósito de la regla. EN: Rule purpose. | ver archivo | Describir criterio estadístico | Todos / All |
| `reglas_auditoria[].thresholds.percent_deviation` | ES: Umbral de desviación porcentual. EN: Percent deviation threshold. | (opcional) | Normal: `0.10–0.15` / Low-profile: `0.15–0.20` | Elección activa / Active election |
| `reglas_auditoria[].thresholds.max_diff_pct` | ES: Diferencia máxima permitida. EN: Maximum allowed difference. | (opcional) | Normal: `0.05–0.10` / Low-profile: `0.10–0.15` | Elección activa / Active election |

### Ejemplo comentado (diffs básicos) / Commented example (basic diffs)

```yaml
# ES: Regla básica para detectar diferencias entre snapshots consecutivos.
# EN: Basic rule to detect differences between consecutive snapshots.

reglas_auditoria:
  - nombre: "basic_snapshot_diff"
    # ES: Regla mínima para diferencias porcentuales.
    # EN: Minimal rule for percentage differences.
    descripcion: "Detecta diferencias básicas entre snapshots consecutivos."
    thresholds:
      # ES: Desviación porcentual máxima por entidad.
      # EN: Maximum percent deviation per entity.
      percent_deviation: 0.12
      # ES: Diferencia absoluta máxima (en proporción).
      # EN: Maximum absolute difference (proportion).
      max_diff_pct: 0.08
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

## Pruebas locales de resiliencia / Local resilience testing

**ES:** Use los siguientes comandos para validar resiliencia y fallback en un entorno local (ajustar rutas si es necesario):

**EN:** Use the following commands to validate resilience and fallback in a local environment (adjust paths if needed):

- **ES:** Ejecutar pipeline una vez con configuración actual.  
  **EN:** Run the pipeline once with current configuration.  
  `poetry run python scripts/run_pipeline.py --run-once`
- **ES:** Forzar fallos de polling en pruebas de caos.  
  **EN:** Force polling failures in chaos tests.  
  `poetry run python scripts/chaos_test.py --scenario network_fail`
- **ES:** Ejecutar watchdog con umbrales de recursos y auto-recuperación.  
  **EN:** Run the watchdog with resource thresholds and auto-recovery.  
  `poetry run python scripts/watchdog.py`
- **ES:** Simular fallo del endpoint cambiando temporalmente `BASE_URL` (por ejemplo a un host inválido) y observar fallback.  
  **EN:** Simulate endpoint failure by temporarily changing `BASE_URL` (e.g., to an invalid host) and observe fallback.  
  `BASE_URL=https://invalid.local poetry run python scripts/download_and_hash.py`

**ES:** Verifique que se generen snapshots con `fallback: true` en `data/` y que los hashes se actualicen en `hashes/`.  
**EN:** Verify that snapshots with `fallback: true` are generated in `data/` and hashes are updated in `hashes/`.

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

### Mantenimiento mensual / Monthly maintenance

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

## Credibilidad ante observadores internacionales / Credibility with international observers

**ES:** La resiliencia documentada aporta **reproducibilidad** (parámetros explícitos, registros de fallos, cadencias declaradas) y **trazabilidad** (hashes y snapshots verificables), lo que facilita auditorías independientes y fortalece la confianza de observadores internacionales en la neutralidad y consistencia técnica del monitoreo. Vincular estas configuraciones con el [manual operativo](manual.md) y la [metodología](methodology.md) permite explicar decisiones técnicas ante OEA, Carter Center y otras misiones con criterios verificables.

**EN:** Documented resilience provides **reproducibility** (explicit parameters, failure logs, declared cadences) and **traceability** (verifiable hashes and snapshots), enabling independent audits and strengthening international observers’ confidence in the neutrality and technical consistency of monitoring. Linking these configurations with the [operational manual](manual.md) and [methodology](methodology.md) makes technical decisions explainable to the OAS, Carter Center, and other missions using verifiable criteria.
