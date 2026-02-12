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
