# Security Policy / Política de Seguridad

## [ES] Reporte de vulnerabilidades
Si descubres una vulnerabilidad, **no** la divulgues públicamente. Reporta el hallazgo mediante un *issue privado* o al correo seguro **security@centinel.org**. Incluye:
- Descripción detallada y pasos para reproducir.
- Impacto potencial (confidencialidad, integridad, disponibilidad).
- Evidencia técnica limitada (sin datos sensibles).

Tiempo de respuesta objetivo: **72 horas** para acuse de recibo.

## [ES] Divulgación responsable
Seguimos un proceso de divulgación responsable coordinado. Solicitamos un tiempo razonable para corregir y desplegar mitigaciones antes de hacer público el detalle técnico.

## [ES] Disclaimer de datos públicos (CNE)
Este repositorio procesa **datos públicos** del CNE. No almacenamos ni solicitamos datos personales. Si se identifican datos sensibles en fuentes públicas, serán filtrados, anonimizados o eliminados.

---

## [EN] Vulnerability reporting
If you discover a vulnerability, **do not** disclose it publicly. Please report it through a *private issue* or by emailing **security@centinel.org**. Include:
- Detailed description and reproduction steps.
- Potential impact (confidentiality, integrity, availability).
- Minimal technical evidence (avoid sensitive data).

Target response time: **72 hours** to acknowledge.

## [EN] Responsible disclosure
We follow a coordinated responsible disclosure process. We request a reasonable time window to patch and deploy mitigations before public disclosure.

## [EN] Public data disclaimer (CNE)
This repository processes **public data** from the CNE. We do not store or request personal data. If sensitive data appears in public sources, it will be filtered, anonymized, or removed.

---

## Defensive Dead Man's Switch / Interruptor Defensivo de Hombre Muerto

This repository now includes a passive **Defensive Mode** that can place the pipeline into controlled hibernation when hostile runtime conditions are detected.  
Este repositorio ahora incluye un **Modo Defensivo** pasivo que puede llevar el pipeline a hibernación controlada cuando detecta condiciones hostiles.

### Flow diagram / Diagrama de flujo

```text
[Normal polling]
      |
      v
[Hostile trigger?] -- no --> [Continue]
      |
     yes
      v
[Pause jobs + collect safe state]
      |
      v
[Close connections + write defensive flag]
      |
      v
[Controlled shutdown]
      |
      v
[Supervisor waits random cooldown 10-60 min]
      |
      v
[Retry up to 5 times with exponential cooldown]
      |
      +--> [Recovered] --> [Return to polling]
      |
      +--> [Still failing] --> [Human admin alert]
```

### Defensive triggers / Disparadores defensivos

- Sustained CPU pressure (`>90%` for `>60s`).
- High memory pressure (`>85%`).
- HTTP transient failure storms (`429`, `503`, timeout bursts).
- Error log flooding bursts.
- Graceful hostile signals (`SIGTERM`, `SIGINT`).
- Optional suspicious listening-ports monitor.

### Why this matters for electoral resilience / Por qué importa para resiliencia electoral

- Reduces brittle behavior under DDoS and heavy platform stress.
- Preserves forensic context (`data/safe_state/*`) for reproducible audits.
- Avoids aggressive retry loops that could worsen upstream instability.
- Escalates to humans only after bounded retries, limiting noise and alert fatigue.

See:
- `core/security.py`
- `scripts/supervisor.py`
- `command_center/security_config.yaml`

## Attack Forensics Logbook / Bitácora Forense de Atacantes

Centinel now includes a passive forensic layer designed for hostile electoral contexts, without interfering with core polling.
Centinel ahora incluye una capa forense pasiva diseñada para contextos electorales hostiles, sin interferir con el polling principal.

### Evidence flow / Flujo de evidencia

```text
[Inbound suspicious request / psutil socket anomaly]
                    |
                    v
         [Rule classification: flood/scan/brute/proxy]
                    |
                    v
  [Async JSONL append -> logs/attack_log.jsonl]
                    |
                    +--> [Daily/size rotation -> attack_log-YYYYMMDD.jsonl.gz]
                    |
                    +--> [Optional anonymized summary -> webhook/Telegram]
```

### What is captured / Qué se captura

- UTC timestamp (`datetime.utcnow().isoformat()`).
- Source IP, user-agent, HTTP method, route, headers, content-length.
- Sliding-window frequency counters per IP and request sequence evidence.
- Automatic classification labels: `flood`, `scan`, `brute`, `proxy_suspect`.
- Unexpected listening-port evidence from `psutil` when enabled.

### What is intentionally NOT captured / Qué NO se captura intencionalmente

- Request bodies / payloads (especially POST data).
- Electoral result payloads or voter-sensitive data.

### Example JSONL event / Ejemplo de evento JSONL

```json
{"timestamp_utc":"2029-11-30T05:00:00.000000","ip":"203.0.113.11","user_agent":"sqlmap/1.8","http_method":"GET","route":"/admin","headers":{"User-Agent":"sqlmap/1.8"},"content_length":0,"frequency_window_seconds":60,"frequency_count":35,"sequence":["/admin","/login"],"classification":"flood","source":"honeypot_or_ingress"}
```

### Reproducibility value for audit observers / Valor de reproducibilidad para observadores

This logbook helps demonstrate attack pressure over time with immutable-like append-only records and deterministic fields, supporting independent review by mathematicians, engineers, political observers, and international missions (OEA/UE/Centro Carter).
Esta bitácora ayuda a demostrar presión de ataque a lo largo del tiempo con registros append-only y campos deterministas, apoyando revisión independiente por matemáticos, ingenieros, observadores políticos y misiones internacionales (OEA/UE/Centro Carter).

### Operational guardrails / Salvaguardas operativas

- Keep honeypot disabled by default (`command_center/attack_config.yaml`).
- Expose honeypot only behind reverse proxy and strict firewall if required.
- Use environment variables for external notifications (`WEBHOOK_URL`, `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`, `ATTACK_LOG_SALT`).

## Sistema de Seguridad Avanzada Integrado (Integrated Advanced Security System)

Este módulo agrega resiliencia defensiva pasiva para escenarios hostiles sin interferir con el polling del CNE.

### Componentes

1. **Honeypot ligero (`core/advanced_security.py`)**
   - Endpoints señuelo configurables (`/admin`, `/login`, etc.) con respuestas aleatorias `404/403/500`.
   - Registro forense de metadata (IP, UA, headers, tamaño, ruta, método, UTC).

2. **Air-gap temporal automático**
   - Al detectar anomalías internas (CPU/memoria/archivos nuevos), activa hibernación aleatoria.
   - Detiene honeypot, limpia memoria (`gc.collect`) y verifica integridad antes de retomar.

3. **Supervisor externo (`scripts/supervisor.py`)**
   - Reinicio con cooldown largo aleatorio/exponencial ante salidas forzadas.
   - Distingue cierre limpio por `/tmp/clean_shutdown.flag`.

4. **Backups off-site cifrados**
   - Respaldo cifrado de hashes/snapshots en intervalos (S3/B2/GitHub/local fallback).
   - Hook post-hash (`core/hasher.py`) y backup en startup/shutdown.

5. **Rotación de identidad**
   - User-Agent rotativo restringido a versión `1.0`.
   - Perfil de proxy opcional para evitar fingerprinting estático.

6. **Alertas escalonadas**
   - Nivel 1: solo bitácora local.
   - Nivel 2: email.
   - Nivel 3: Telegram principal + email fallback.

### Flujo de alerta escalonada (ASCII)

```text
[detector interno/honeypot/supervisor]
               |
               v
        clasificar severidad
      /        |          \
    L1         L2          L3
    |          |           |
 log local   email     telegram -> (si falla) -> email
```

### Recomendaciones operativas

- Mantener `honeypot_enabled: false` por defecto y exponerlo solo detrás de firewall/reverse proxy.
- Definir `BACKUP_AES_KEY`, credenciales cloud y canales de alerta por variables de entorno.
- Usar `centinel-supervisor` como servicio externo en Compose o contenedor independiente.

## CI Error Handling Hardening / Endurecimiento de manejo de errores en CI

- **[EN] Collector resilience:** `scripts/collector.py` now catches HTTP and JSON parsing failures, applies retry policy from `retry_config.yaml`, and emits structured logs for forensic debugging in CI.
- **[ES] Resiliencia del colector:** `scripts/collector.py` ahora captura fallos HTTP y de parsing JSON, aplica política de reintentos desde `retry_config.yaml`, y emite logs estructurados para depuración forense en CI.
- **[EN] Audit hash safety:** `scripts/hash.py` handles missing files safely, computes chained SHA-256 snapshots with timestamps, and avoids unhandled crashes on empty directories.
- **[ES] Seguridad de hash en auditoría:** `scripts/hash.py` maneja archivos faltantes de forma segura, calcula snapshots SHA-256 encadenados con timestamp, y evita caídas no controladas en directorios vacíos.
- **[EN/ES] Workflow diagnostics:** `.github/workflows/pipeline.yml` includes debug steps (`env`, `ls data/`, `ls hashes/`) and Poetry dependency caching to reduce failure opacity and runtime.

## Security CI Handling / Manejo de seguridad en CI

- **[EN] Exit code 2 hardening:** Security workflows now include explicit debug output (`set -x`, `pwd`, `ls -la`) to make scan failures reproducible.
- **[ES] Endurecimiento de exit code 2:** Los workflows de seguridad ahora incluyen salida de depuración explícita (`set -x`, `pwd`, `ls -la`) para volver reproducibles los fallos de escaneo.
- **[EN] Bandit policy:** `bandit.yaml` skips only low-priority patterns such as `B101` (`assert` usage), while preserving medium+ findings.
- **[ES] Política Bandit:** `bandit.yaml` omite solo patrones de baja prioridad como `B101` (uso de `assert`), manteniendo hallazgos medium+.
- **[EN] Dev branch tolerance:** For `dev-v*` / `work`, non-blocking security execution is enabled (`|| true`) to avoid blocking rapid hardening loops.
- **[ES] Tolerancia en ramas dev:** Para `dev-v*` / `work`, se habilita ejecución de seguridad no bloqueante (`|| true`) para no bloquear ciclos rápidos de endurecimiento.
