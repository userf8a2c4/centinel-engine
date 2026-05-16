# Runbooks Operacionales — Procedimientos para el Testigo

## Índice

1. [Startup & Daily Operations](#startup--daily-operations)
2. [Procedimiento si AMARILLO](#procedimiento-si-amarillo)
3. [Procedimiento si ROJO](#procedimiento-si-rojo)
4. [Troubleshooting](#troubleshooting)
5. [Noche Electoral](#noche-electoral)
6. [Post-Elección](#post-elección)

---

## Startup & Daily Operations

### Antes de Elección (Setup)

#### Semana 1: Instalación

```bash
# 1. Clonar repo
git clone https://github.com/userf8a2c4/centinel-engine.git
cd centinel-engine

# 2. Instalar dependencias
poetry install

# 3. Verificar instalación
poetry run centinel panel show
# Esperado: 🟢 GREEN status

# 4. Configurar almacenamiento externo (mirrors)
# Editar: advanced_security_config.yaml
# Agregar rutas S3, Google Drive, etc.

# 5. Configurar captura automática (cron)
crontab -e
# Agregar línea:
# * * * * * cd /path/to/centinel && poetry run centinel snapshot
```

#### Semana 2-3: Configuración

```bash
# 1. Conectar testigos hermanos (si aplica)
# Editar: advanced_security_config.yaml
# Agregar sibling_urls (ej: https://witness-b.example.com)

# 2. Sincronizar mirrors manualmente
poetry run centinel regeneration --sync-now

# 3. Prueba de carga (simulación)
# Ejecutar snapshot de prueba contra datos dummy
poetry run centinel snapshot --test-data

# 4. Verificar integridad de logs
jq '.' hashes/attack_log.jsonl | wc -l
# Esperado: 0 o números pequeños (sin ataques previos)
```

### Daily Operations (Cada Día)

#### Mañana
```bash
# 1. Health check rápido
poetry run centinel panel show

# 2. Ver eventos últimas 24h
jq '.[] | select(.timestamp > "2026-05-15T00:00:00Z")' \
  hashes/attack_log.jsonl | tail -10

# 3. Si no hay nada raro: OK
```

#### Noche (Antes de Dormir)
```bash
# 1. Sync con mirrors (regeneración)
poetry run centinel regeneration --sync-now

# 2. Backup de hashes/ a ubicación segura
tar -czf hashes-backup-$(date +%Y%m%d).tar.gz hashes/

# 3. Verificar cron está corriendo
pgrep -f 'centinel snapshot' || echo "ALERTA: Cron no activo"
```

---

## Procedimiento si AMARILLO

### Nivel 1: Evaluación Rápida

```bash
# 1. Ver panel
centinel panel show --verbose

# 2. Identificar qué está amarillo
# Posibilidades:
# - Threat score 31–74 (anomalía leve)
# - 1+ defensa DEGRADADA
# - Conectividad < 100%
```

### Nivel 2: Revisar Logs

```bash
# 1. Últimas 50 líneas de attack_log
tail -50 hashes/attack_log.jsonl | jq '.'

# 2. Últimas threat scores
jq '.[] | select(.event == "threat_score")' \
  hashes/attack_log.jsonl | tail -10

# 3. Ver eventos específicos
# Si Benford: 
jq '.[] | select(.event == "benford_anomaly")' hashes/attack_log.jsonl

# Si endpoint:
jq '.[] | select(.event == "endpoint_schema_change")' hashes/attack_log.jsonl
```

### Nivel 3: Diagnóstico por Defensa

#### Si 🐦 Cuervo DEGRADADO

```bash
# 1. Revisar conectividad a hermanos
ping witness-b.example.com
# Si no responde: problema de red, esperar

# 2. Revisar timestamp de última atestación
jq '.metrics.corvid.last_attestation' hashes/recovery_state.json

# 3. Si >10 min sin atestación: contactar a hermano
```

#### Si 🦑 Pulpo DEGRADADO

```bash
# 1. Revisar error de cifrado
jq '.[] | select(.event == "cephalopod_error")' hashes/attack_log.jsonl

# 2. Si error de key derivation: reinicia (se recalcula)
poetry run centinel snapshot

# 3. Si continúa: problema criptográfico (escala)
```

#### Si 🦌 Venado DEGRADADO

```bash
# 1. Revisar config de jitter
grep -A 5 "evasion:" advanced_security_config.yaml

# 2. Si jitter deshabilitado: editar config e reiniciar
sed -i 's/enabled: false/enabled: true/' advanced_security_config.yaml
```

#### Si 🦎 Lagartija DEGRADADO

```bash
# 1. Revisar mirrors accesibles
ls -la hashes/mirrors/

# 2. Si algunos falta: intentar resync
poetry run centinel regeneration --sync-now --force

# 3. Si todos falta: problema de almacenamiento externo
```

### Decisión Final

#### Si Causa Es Falsa Alarma (ej: endpoint schema cambió)
```bash
# Revisar D11 logs
jq '.[] | select(.event == "endpoint_monitor")' hashes/attack_log.jsonl | tail -5

# Si solo es schema change (D11 logged, NO en threat score):
# → IGNORA, es normal
# Score debe estar < 75, continúa monitoreando
```

#### Si Causa Es Desconocida
```bash
# 1. Exporta evidence
tail -100 hashes/attack_log.jsonl > logs_export_$(date +%s).jsonl

# 2. Contacta a Centinel team
```

---

## Procedimiento si ROJO

### 🚨 ¡AMENAZA ACTIVA! CUIDADO

**NO HAGAS:**
- ❌ No apagues el testigo
- ❌ No borres archivos de hashes/
- ❌ No intentes "arreglar" manualmente

**HAZLO:**
- ✅ Espera (sistema está auto-recuperándose)
- ✅ Revisa logs
- ✅ Documenta evidence

---

### Timeline (0–60 segundos)

#### T+0s: Score sube a ≥75
```
🔴 ROJO activado
Sistema acción: Kill Switch (Tejón) se congela automáticamente
```

#### T+1s: Freeze ejecutado
```
Panel muestra: "Tejón: 🔴 FROZEN (Intento 1/5, próximo en 1.4-2.6s)"
Archivo creado: /tmp/centinel.lock
Efecto: Testigo DEJA DE CAPTURAR (preserva integridad)
```

#### T+2-39s: Reintentos con backoff exponencial
```
Intento 1:  espera 1.4-2.6s
Intento 2:  espera 3.5-6.5s
Intento 3:  espera 7-13s
Intento 4:  espera 14-26s
Intento 5:  espera 21-39s

Si alguno tiene éxito: 🟢 VERDE nuevamente
```

#### T+40+s: Fallo permanente (si ≥5 intentos fallaron)
```
Panel muestra: "Tejón: ❌ PERMANENT FAILURE"
Acción: ESCALA INMEDIATAMENTE
```

---

### Procedimiento Detallado

#### Paso 1: Observación (primeros 5 segundos)
```bash
# Ver panel en vivo
watch -n 0.5 'poetry run centinel panel show'

# En otra terminal: ver logs
tail -f hashes/attack_log.jsonl | grep -E 'freeze|recovery|threat'

# Esperar: Sistema intenta recuperarse (backoff exponencial)
```

#### Paso 2: ¿Volvió a Verde? (después 30s)
```bash
# Caso A: 🟢 VERDE nuevamente
# → Auditar qué pasó

# Caso B: 🔴 Sigue ROJO
# → Continúa Paso 3

# Caso C: ❌ PERMANENT FAILURE
# → Salta a Escalación
```

#### Paso 3: Auditoría Post-Recuperación (Si Volvió a Verde)
```bash
# 1. Exporta attack_log (evidencia)
jq '.[] | select(.event == "kill_switch_freeze" or .event == "kill_switch_recovery")' \
  hashes/attack_log.jsonl > kill_switch_audit.jsonl

# 2. Verifica Merkle antes/después
jq '.recovery_state.merkle_root' hashes/checkpoint_frozen.json
# vs.
jq '.merkle_root' hashes/checkpoint_current.json
# Deben coincidir si recuperación fue exitosa

# 3. Timeline
jq '.[] | select(.event == "kill_switch_freeze" or .event == "kill_switch_recovery") | .timestamp' \
  kill_switch_audit.jsonl

# 4. Reporta: contacta a autoridad electoral con evidence
```

#### Paso 4: Si Sigue ROJO (Escalación)
```bash
# 1. DEJA DE CAPTURAR. No hagas nada.

# 2. Documenta state exacto
centinel panel show > red_state_$(date +%s).txt
centinel panel show --verbose >> red_state_$(date +%s).txt

# 3. Exporta logs críticos
tail -200 hashes/attack_log.jsonl > critical_logs_$(date +%s).jsonl
cp hashes/checkpoint_frozen.json checkpoint_frozen_$(date +%s).json

# 4. **CONTACTA AUTORIDAD ELECTORAL INMEDIATAMENTE**
# Proporciona:
#   - red_state_*.txt
#   - critical_logs_*.jsonl
#   - checkpoint_frozen_*.json
#   - Todo el directorio hashes/

# 5. Espera instrucciones
```

---

## Troubleshooting

### Síntoma: "No se puede conectar a mirrors"

```bash
# Causa 1: Almacenamiento externo down
# Solución:
ping s3.amazonaws.com
# Revisar credentials en config
grep -A 5 "mirrors:" advanced_security_config.yaml

# Causa 2: Conexión a internet problema
# Solución:
nslookup google.com
ping 8.8.8.8
```

### Síntoma: "Cron no captura cada 30 segundos"

```bash
# Causa 1: Cron no está registrado
crontab -l | grep centinel
# Si no existe: agregar

# Causa 2: Poetry path incorrecta
which poetry
# Actualizar cron con full path
```

### Síntoma: "Lock file still exists after recovery"

```bash
# Solución (CUIDADO):
# 1. Revisar si está realmente congelado
cat /tmp/centinel.lock

# 2. Si timestamps son >1 hora atrás: remover
rm /tmp/centinel.lock

# 3. Intenta captura manual
poetry run centinel snapshot
```

---

## Noche Electoral

### Antes (6 AM)
```bash
# 1. Health check
centinel panel show
# Esperado: 🟢 GREEN

# 2. Verifica cron
ps aux | grep centinel

# 3. Abre log en vivo
tmux new-session -d -s centinel-live \
  'tail -f hashes/attack_log.jsonl | jq "."'

# 4. Abre panel
tmux new-window -t centinel-live \
  'watch -n 2 "poetry run centinel panel show"'

# 5. Notifica: "Centinel LIVE"
```

### Durante (7 AM — 6 PM)
```bash
# 1. MONITOREAR CONSTANTEMENTE
# - Terminal 1: live logs
# - Terminal 2: panel refresh
# - Terminal 3: reserve

# 2. CADA CAMBIO DE COLOR:
# - 🟢 → 🟡: Documentar, ver logs
# - 🟡 → 🔴: ALERTA, sigue Procedimiento si ROJO
# - 🔴 → 🟢: Documentar recovery time

# 3. NO HAGAS:
# ❌ No reinicies sin necesidad
# ❌ No edites configs en vivo
# ❌ No dejes desatendido >5 min

# 4. DOCUMENTA TODO:
jq '.[] | {timestamp, event, threat_score}' hashes/attack_log.jsonl | tail -50
```

### Después (6 PM+)
```bash
# 1. Deja de monitorear
tmux kill-session -t centinel-live

# 2. Exporta evidence
mkdir -p election_audit_$(date +%Y%m%d)
cp hashes/attack_log.jsonl election_audit_$(date +%Y%m%d)/
cp hashes/recovery_state.json election_audit_$(date +%Y%m%d)/

# 3. Genera reporte
jq -s 'length as $len | {total_events: $len, threat_events: [.[] | select(.event == "threat_score")]}' \
  election_audit_$(date +%Y%m%d)/attack_log.jsonl \
  > election_audit_$(date +%Y%m%d)/SUMMARY.json

# 4. Entrega a autoridad electoral
```

---

## Post-Elección

### Auditoría Completa (Dentro de 48 horas)

```bash
# 1. Verifica integridad de chain
jq '.[] | .merkle_root' hashes/attack_log.jsonl | wc -l

# 2. Valida Benford
jq '.[] | select(.event == "benford_check")' hashes/attack_log.jsonl

# 3. Reporte Final
echo "Audit Report: Centinel $(date +%Y-%m-%d)" > AUDIT_REPORT.md
echo "Total events: $(jq '.' hashes/attack_log.jsonl | wc -l)" >> AUDIT_REPORT.md
```

---

**Última actualización:** 2026-05-16  
**Status:** v0.1 Operacional
