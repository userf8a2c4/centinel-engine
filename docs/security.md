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
