# Security Integration Guide / Guía de Integración de Seguridad

## Resolución de Críticas y Flujo Integrado

Plan paso a paso (operativo y reproducible):

1. **Rotación forense anti-inflado**: activar rotación diaria JSONL con compresión `.gz`, retención configurable y escritura asíncrona para minimizar overhead bajo ataques sostenidos.
2. **Umbrales adaptativos**: usar baseline de CPU con ventana móvil + margen adaptativo para ignorar picos breves de VPS y reducir falsos positivos del dead-man.
3. **Integración honeypot → dead-man**: disparar air-gap automático si se supera `honeypot_threshold_per_minute` (ej. `>100 req/min`) o flood sostenido.
4. **Persistencia pre-OOM**: al recibir señales de terminación/OOM-like, persistir snapshot mínimo en disco y forzar backup cifrado antes de salir.
5. **Alertas escalonadas**: nivel 1 (solo log), nivel 2 (email + webhook SMS), nivel 3 (Telegram + fallback).
6. **Seguridad Solidity + Python**: chequeos runtime de contratos (`pragma`, patrones bloqueados como `delegatecall`/`tx.origin`) antes de anclaje.
7. **Métricas Prometheus**: exponer CPU, tamaño de logs, anomalías y alertas en endpoint para monitoreo continuo.
8. **Pruebas integradas y chaos**: validar cadena completa detección → logging → dead-man → backup, incluyendo DDoS + tampering + OOM.

## Flujo defensivo consolidado

```text
Tráfico sospechoso (honeypot/ingress)
  -> Attack Forensics Logbook (JSONL async + rotación diaria + gzip)
  -> Clasificación (scan/brute/flood/proxy_suspect)
  -> Umbral adaptive + dead-man switch
  -> Air-gap controlado
  -> Persistencia pre-OOM + backup cifrado off-site
  -> Supervisor con backoff exponencial y guardas de concurrencia
  -> Verificación de integridad (archivos + contratos Solidity)
  -> Reanudación segura de polling GET-only
```

## Configuraciones clave

### `command_center/security_config.yaml`

- `forensics.log_rotation_days`: días de retención de rotación comprimida.
- `honeypot.honeypot_threshold`: req/min para activar dead-man.
- `observability.prometheus_port`: puerto del endpoint de métricas.
- `alert_email`: destino primario de escalamiento.

### `command_center/advanced_security_config.yaml`

- `cpu_adaptive_margin_percent`, `cpu_spike_grace_seconds`, `cpu_baseline_window`.
- `honeypot_threshold_per_minute`.
- `prometheus_enabled`, `prometheus_port`.
- `solidity_contract_paths`, `solidity_blocked_patterns`.

### `command_center/attack_config.yaml`

- `log_rotation_days`.
- `honeypot.firewall_default_deny` + `honeypot.allowlist`.
- `flood_log_sample_ratio` para ataques sostenidos.

## Firewall para honeypot

- Default deny para IP pública fuera de allowlist local.
- Recomendación host-level:

```bash
# UFW ejemplo mínimo
ufw default deny incoming
ufw allow 22/tcp
ufw allow from 127.0.0.1 to any port 8080 proto tcp
```

- En Docker, replicar con reglas de red bridge + puertos explícitos.

## Ejemplo de alerta y evento

```json
{"level":3,"event":"honeypot_rate_limit_deadman","metrics":{"rpm":132}}
```

```json
{"classification":"flood","ip":"198.51.100.10","route":"/admin","frequency_count":42}
```

## Troubleshooting rápido

- **Falsos positivos CPU**: subir `cpu_spike_grace_seconds` o `cpu_adaptive_margin_percent`.
- **Logs inflados**: revisar `flood_log_sample_ratio`, `log_rotation_days` y endpoint Prometheus.
- **Alertas no entregadas**: validar `SMTP_*`, `TELEGRAM_*`, `SMS_WEBHOOK_URL`.
- **OOM recurrente**: revisar `data/backups/pre_oom_snapshot.json` y `supervisor_pre_oom.json`.

## Neutralidad y límites operativos

- Solo se permiten consultas a fuentes públicas CNE vía GET.
- No se altera contenido electoral ni se infieren preferencias políticas.
- La evidencia forense preserva trazabilidad sin exfiltrar datos sensibles.
