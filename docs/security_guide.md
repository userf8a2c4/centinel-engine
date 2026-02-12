# Security Integration Guide / Guía de Integración de Seguridad

## Integración de Sistemas

Centinel-Engine integra los componentes defensivos en este flujo:

```text
Honeypot detecta tráfico sospechoso
  -> Attack Forensics Logbook clasifica y rota logs JSON diarios comprimidos
  -> callback de flood evalúa umbrales anti-DDoS
  -> Dead Man's Switch evalúa señales internas (CPU/Mem/errores/conexiones)
  -> si supera umbral consecutivo activa air-gap controlado
  -> Supervisor reinicia con backoff exponencial y guardas de concurrencia
  -> Backup manager cifra y envía hashes/logs a air-gap off-site
  -> Verificación de integridad antes de reanudar polling
```

## Principios operativos

- Solo tráfico de auditoría pública con métodos GET para fuentes CNE.
- Neutralidad cívica: no inferir preferencias políticas ni alterar datos.
- Reproducibilidad: logs estructurados JSONL y config YAML versionable.

## Configuración recomendada

Archivo principal: `command_center/security_config.yaml`

- `max_restart_attempts`, `cooldown_min_minutes`, `cooldown_max_minutes` para resiliencia.
- `alerts.channels` para escalamiento (email/telegram/sms_webhook).
- `honeypot.enabled` para activar captura controlada de scans.

Archivo integrado: `command_center/advanced_security_config.yaml`

- `anomaly_consecutive_limit` reduce falsos positivos.
- `honeypot_flood_trigger_count` + `honeypot_flood_window_seconds` enlaza honeypot y dead-man switch.
- `auto_backup_forensic_logs` respalda evidencia forense automáticamente.

Archivo forense: `command_center/attack_config.yaml`

- `flood_log_sample_ratio` minimiza inflado en ataques sostenidos.
- `rotation_interval` + `retention_days` controlan ciclo de vida de logs.
- `geoip_city_db_path` habilita geolocalización offline si hay base MaxMind.

## Ejemplo de evento forense

```json
{
  "timestamp_utc": "2026-02-12T03:11:04.901324+00:00",
  "ip": "198.51.100.10",
  "route": "/admin",
  "classification": "flood",
  "frequency_count": 42,
  "geo": {"country": "HN", "city": "Tegucigalpa"}
}
```

## Troubleshooting

- **Falsos positivos de air-gap**: subir `anomaly_consecutive_limit` o `cpu_sustain_seconds`.
- **Logs crecen rápido**: aumentar `flood_log_sample_ratio` y revisar `max_requests_per_ip`.
- **No llegan alertas**: validar variables `SMTP_*`, `TELEGRAM_*`, y webhook.
- **Reinicios frecuentes**: revisar `supervisor_concurrency_guard_triggered` en logs.

## Diagramas de decisión de alertas

```text
Evento detectado
  -> nivel 1: solo log interno
  -> nivel 2: email/webhook
  -> nivel 3: telegram + fallback email
  -> si fallan N envíos: error crítico de canal
```
