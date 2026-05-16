# Defensa de Tejón — Configuración y Operación

## Descripción

La **Defensa de Tejón** (Kill Switch) es un mecanismo autónomo de respuesta a ataques activos en tiempo real. Cuando detecta una amenaza de integridad de datos (no cambios de API), el testigo se congela instantáneamente y se recupera de forma independiente.

**Principios fundamentales:**
- ✅ Autónomo: no espera a nadie
- ✅ Defensivo: "seguro de vida", no ataque
- ✅ Moderado: máximo 39 segundos recuperación (electoral realista)
- ✅ Forensic: cada acción logged para auditoría

---

## Detección de Amenaza

### Threat Score (0–100)

El sistema calcula automáticamente una puntuación de amenaza basada en señales criptográficas/estadísticas:

```python
score = 0
if merkle_divergence:           score += 40  # Datos realmente modificados
if benford_severity > 15.99:    score += 25  # Manipulación estadística
if connectivity_lost:           score += 20  # Infraestructura atacada
if consensus_broken:            score += 35  # Bloqueo selectivo
```

**IGNORA (score = 0):**
- ✗ Endpoint schema cambió → D11 se encarga
- ✗ Endpoint URL cambió → D11 se encarga
- ✗ Endpoint timeout transiente → reintento normal

### Threshold de Activación

- **Threat score ≥ 75:** Kill Switch se activa
- **Threat score < 75:** Sistema opera normalmente

### Ejemplos de Escenarios

| Escenario | Score | Acción |
|-----------|-------|--------|
| CNE cambió `/api/results` → `/api/v2/results` | 0 | Nada (D11 logged) |
| Merkle root diverge en 3 snapshots consecutivos | 40+ | ⚠️ Yellow alert |
| Benford χ² = 18.5 + Merkle diverge | 65 | ⚠️ Yellow alert |
| Merkle diverge + Benford severe + consensus roto | 100 | 🔴 **FREEZE** |
| Conectividad 100% perdida >2min | 20 | ⚠️ Yellow alert |

---

## Congelación (Freeze)

Cuando `threat_score ≥ 75`, el kill switch ejecuta:

### 1. Snapshot Atómico
```
Acción: Guardar estado completo en este momento exacto
Archivo: hashes/checkpoint_frozen.json
{
  "frozen_at": "2026-05-16T14:30:00Z",
  "recovery_state": {
    "attempt_count": 0,
    "last_freeze_timestamp": 1715851800.123,
    "is_frozen": true
  },
  "merkle_root": "abc123...abc123"
}
```

### 2. Lock File
```
Acción: Crear señal visible de congelamiento
Archivo: /tmp/centinel.lock
{
  "frozen_at": "2026-05-16T14:30:00Z",
  "reason": "Merkle divergence detected (40 pts) + Benford anomaly (25 pts) = 65 pts",
  "recovery_state": {...}
}
```

### 3. Stop Capturing
```
Acción: Dejar de capturar nuevos snapshots
Efecto: Preserva cadena completa sin corrupción adicional
```

### 4. Log Attack Event
```
Acción: Registrar en attack_log.jsonl (append-only)
Contenido: timestamp, evento, detalles completos
```

---

## Recuperación (Auto-Recovery)

Después del freeze, el testigo intenta **recuperarse automáticamente**:

### Exponential Backoff (Moderado)

```
Intento 1:  2s ± 30%  →  1.4s–2.6s   (rápido)
Intento 2:  5s ± 30%  →  3.5s–6.5s   (control)
Intento 3: 10s ± 30%  →  7s–13s      (paciencia)
Intento 4: 20s ± 30%  → 14s–26s      (resistencia)
Intento 5+: 30s ± 30%  → 21s–39s      (máximo)
```

**¿Por qué exponencial?**
- Defende contra coordinated waves (atacante no puede sincronizar)
- Jitter ±30% imposibilita pattern matching
- Cap en 39s: <1 min en elección (realista electoral)

### Validación Local

Cada intento verifica **sin esperar hermanos**:

```python
while attempt < 5:
    attempt += 1
    sleep(exponential_backoff(attempt) + jitter)
    
    if local_chain_matches_mirrors():
        # ✅ Integridad confirmada
        publish_recovery_attestation()
        return SUCCESS
    
    if restore_from_best_local_mirror():
        # ✅ Restaurado desde copia
        return SUCCESS

# ❌ Fallo permanente
log_permanent_failure()
return FAILED
```

### Condición de Éxito

Recuperación exitosa si:
- Merkle root local = merkles de espejo local (mayoría)
- O: restauración desde espejo confiable completó correctamente

### Fallo Permanente

Si ≥5 intentos fallan:
- Testigo permanece congelado (seguro)
- Log: "kill_switch_permanent_failure"
- Operador debe escalar a autoridad electoral
- Proporcionar: `attack_log.jsonl`, `checkpoint_frozen.json`, últimos hashes

---

## Configuración

### `advanced_security_config.yaml`

```yaml
kill_switch:
  enabled: true
  
  # Threat scoring
  threat_threshold: 75
  benford_severity_threshold: 15.99
  merkle_divergence_points: 40
  benford_anomaly_points: 25
  connectivity_loss_points: 20
  consensus_broken_points: 35
  
  # Recovery backoff
  backoff_schedule: [2, 5, 10, 20, 30]  # segundos base
  jitter_percent: 30
  max_recovery_attempts: 5
  
  # Logging
  attack_log_path: "hashes/attack_log.jsonl"
  frozen_checkpoint_path: "hashes/checkpoint_frozen.json"
  recovery_state_path: "hashes/recovery_state.json"
```

### Variables de Entorno (Opcional)

```bash
# Override configuración YAML
CENTINEL_KILL_SWITCH_ENABLED=true
CENTINEL_KILL_SWITCH_THREAT_THRESHOLD=75
CENTINEL_KILL_SWITCH_MAX_ATTEMPTS=5
CENTINEL_KILL_SWITCH_BACKOFF_BASE_1=2
```

---

## Operación

### Ver Estado

```bash
# Panel interactivo
centinel panel

# Salida esperada si está READY:
⚔️ Tejón (Kill Switch):  READY    (no activado)

# Salida esperada si ESTÁ CONGELADO:
⚔️ Tejón (Kill Switch):  FROZEN   (Intento 2/5, próximo en 5.3s)
```

### Revisar Lock File

Si ves `/tmp/centinel.lock`:

```bash
cat /tmp/centinel.lock
# Verá JSON con frozen_at, reason, recovery_state
```

### Leer Logs de Ataque

```bash
# Últimas 10 eventos de kill switch
jq '.[] | select(.event == "kill_switch_freeze" or .event == "kill_switch_recovery")' \
  hashes/attack_log.jsonl | tail -10

# Ver threat scores históricos
jq '.[] | select(.event == "threat_score") | {timestamp, score}' \
  hashes/attack_log.jsonl | tail -20
```

### Monitoreo en Vivo

```bash
# Ver línea a línea de ataques en progreso
tail -f hashes/attack_log.jsonl | grep -E "freeze|recovery|threat"

# Contar eventos por tipo
jq '.event' hashes/attack_log.jsonl | sort | uniq -c
```

---

## Escenarios de Operación

### Escenario 1: False Alarm (Score 40)

**Situación:** Merkle diverge una vez por error de red transiente

```
Threat score: 40 pts (solo merkle)
Action: Yellow alert, sin freeze
Result: Sistema continúa normal

Operador ve:
  🟡 Yellow status en panel
  "Merkle diverge detected 1 time (40 pts)"
Acción: Revisar logs, normalidad restaurada en 2 min
```

### Escenario 2: Ataque Coordenado (Score 100)

**Situación:** CNE ataca en tiempo real (merkle diverge + Benford + consensus roto)

```
Threat score: 100 pts (40 + 25 + 35)
Action: FREEZE inmediato ← KILL SWITCH ACTIVATED

Timeline:
T+0s:   Freeze detectado, snapshot atómico
T+2s:   Intento 1 recuperación (1.4–2.6s espera)
T+4s:   Verifica integridad local vs mirrors
T+4.5s: Restauración exitosa desde mirror
T+5s:   Publica atestación de recuperación
T+6s:   Resume captura normal

Operador ve:
  🔴 Red status en panel
  "Kill Switch ACTIVE: Merkle divergence + Benford + Consensus"
  Después: 🟢 Green
  "Recovery successful from local mirror"
```

### Escenario 3: Fallo Permanente (≥5 intentos)

**Situación:** Ataque tan severo que recuperación falla 5 veces

```
T+0s:   Freeze
T+2.6s: Intento 1 falla
T+6.5s: Intento 2 falla
T+13s:  Intento 3 falla
T+26s:  Intento 4 falla
T+39s:  Intento 5 falla
T+40s:  Permanente freeze

Operador ve:
  🔴 Red status en panel
  "Kill Switch: PERMANENT FAILURE after 5 attempts"
  
Acciones:
  1. Revisar attack_log.jsonl (últimas líneas)
  2. Contactar autoridad electoral
  3. Proporcionar:
     - attack_log.jsonl
     - checkpoint_frozen.json
     - hashes/ directorio completo
```

---

## Troubleshooting

### ¿Congelado pero debería recuperarse?

**Síntoma:** `/tmp/centinel.lock` existe, pero no avanza en recuperación

**Checklist:**
1. ¿Mirrors accesibles? `ls -la hashes/mirrors/`
2. ¿Espacio en disco? `df -h`
3. ¿Logs de error? `tail -100 hashes/attack_log.jsonl | grep error`
4. ¿Red OK? `ping 8.8.8.8`

**Solución:**
- Si mirrors no accesibles: agregar ruta de backup
- Si espacio: limpiar snapshots antiguos (>1 mes)
- Si red: esperar conexión, kill switch reintentará automáticamente

### ¿Threat score muy alto por falsa alarma?

**Síntoma:** Score 75+ pero no parece ataque real

**Checklist:**
1. ¿CNE endpoint cambió schema? (D11 debería loggear)
2. ¿Benford threshold muy bajo? (default 15.99 es conservador)
3. ¿Consenso de hermanos roto? (fallo de red vs ataque real)

**Solución:**
- Si cambio de endpoint: D11 logs + ignorar threat score
- Si Benford falso positivo: aumentar threshold (16.99 en config)
- Si consenso roto: verificar hermanos están online

### ¿Recovery toma demasiado?

**Síntoma:** Intento 5 = 39s, demasiado para elección

**Solución:** No editar backoff schedule en medio de elección
- El máximo 39s es por diseño (desalienta ataques coordenados)
- En próximas versiones: considerar 2-tier (fast recovery + verification)

---

## Auditoría Post-Ataque

Después que testigo se recupera, auditor verifica:

### Paso 1: Timeline de Ataque

```bash
jq '.[] | select(.event == "kill_switch_freeze") | {timestamp, reason}' \
  attack_log.jsonl
```

### Paso 2: Puntuación de Amenaza

```bash
jq '.[] | select(.event == "threat_score") | {timestamp, score, merkle, benford}' \
  attack_log.jsonl | tail -20
```

### Paso 3: Integridad de Recuperación

```bash
jq '.[] | select(.event == "kill_switch_recovery") | {timestamp, recovery_state}' \
  attack_log.jsonl
```

### Paso 4: Merkle Root Comparación

```bash
# Merkle antes del ataque
jq '.recovery_state.merkle_root' hashes/checkpoint_frozen.json

# Merkle actual (después de restauración)
jq '.merkle_root' hashes/checkpoint_current.json

# Deben coincidir si la recuperación fue correcta
```

---

## Referencias

- **Defensa de Tejón:** ⚔️ Kill Switch, exponential backoff autónomo
- **Animal Defenses:** Documentación completa en `ANIMAL-DEFENSES-ES.md`
- **D11:** Endpoint Monitor (esquema de cambios, no threat score)
- **D13:** Federation (consenso multi-testigo)
- **Attack Log Format:** Append-only JSONL, timestamp ISO 8601

---

**Última revisión:** 2026-05-16  
**Status:** v0.1 Operacional  
**Auditoría:** Listo para campo
