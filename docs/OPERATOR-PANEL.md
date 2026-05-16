# Panel Operador — Cómo Leer el Status

## Acceso Rápido

```bash
# Panel interactivo en terminal
centinel panel show

# Panel con detalles
centinel panel show --verbose

# Panel en JSON (máquinas/APIs)
centinel panel json
```

---

## Estructura del Panel

```
╔════════════════════════════════════════════════════════════════╗
║ CENTINEL — Estado Operacional / Operational Status             ║
╠════════════════════════════════════════════════════════════════╣
│                                                                │
│  AMENAZA GENERAL / Threat Score:   22/100 🟢 VERDE            │
│                                                                │
│  DEFENSAS ANIMALES / Animal Defenses:                         │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ 🐦 Cuervo (Memory):      ACTIVO ✓  Último:  5m          │  │
│  │ 🦑 Pulpo (Encrypt):       ACTIVO ✓  Clave: hash...     │  │
│  │ 🦌 Venado (Evasion):     ACTIVO ✓  Jitter: ±30%        │  │
│  │ 🦎 Lagartija (Healing):  ACTIVO ✓  Mirrors: 3/3        │  │
│  │ ⚔️  Tejón (Kill Switch):  READY   (no activado)         │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                │
│  MÉTRICAS / Metrics:                                           │
│  Merkle Root:     abc123...abc123        [VIGENTE — 2m]       │
│  Anomalías:       0 Benford + 0 Z-score                       │
│  Conectividad:    4/4 endpoints UP       [100%]              │
│  Snapshots:       2847 captured          [Last: 30s ago]      │
│                                                                │
│  ⓘ Detalles: centinel panel show --verbose                    │
│  ⓘ Auditoría: cat hashes/attack_log.jsonl                     │
╚════════════════════════════════════════════════════════════════╝
```

---

## Sección 1: AMENAZA GENERAL (Threat Score)

### Valor y Significado

```
Threat Score: XX/100 [COLOR]
```

**¿Qué significa?**
- **0–30 (🟢 VERDE):** Operación normal, sin alertas
- **31–74 (🟡 AMARILLO):** Anomalía detectada, revisar logs
- **≥75 (🔴 ROJO):** Amenaza activa, kill switch posiblemente activado

### Cómo se Calcula

El score es automático:
- Merkle divergence: +40 pts
- Benford anomaly severa: +25 pts
- Conectividad pérdida: +20 pts
- Consenso federation roto: +35 pts

**Ignora (score = 0):**
- Cambios de endpoint (D11 se encarga)
- Cambios de API schema
- Timeouts transientes

### Ejemplo: Interpretación

```
Threat Score: 22/100 🟢 VERDE
↓
Significa: Sistema operativo normalmente.
Acción: Continúa monitoreando.

Threat Score: 50/100 🟡 AMARILLO
↓
Significa: Anomalía detectada (posiblemente Benford o endpoint).
Acción: Revisa logs, puede ser falsa alarma.

Threat Score: 85/100 🔴 ROJO
↓
Significa: Amenaza de integridad real (Merkle diverge + Benford).
Acción: Kill switch se activó. Espera recuperación.
```

---

## Sección 2: DEFENSAS ANIMALES

### Formato

```
[EMOJI] [Nombre] ([Key]): [Status]  [Detalles Adicionales]
```

### 🐦 Cuervo (Corvid Memory)

| Status | Significado | Acción |
|--------|---|---|
| ACTIVO ✓ | Hermanos responden | Normal |
| ⚠️ DEGRADADO | 1+ hermanos offline | Revisar red |
| ❌ CRÍTICO | Todos hermanos offline | Revisar conectividad |

**Detalles:** `Último: 5m` = última atestación hace 5 minutos

---

### 🦑 Pulpo (Cephalopod Encryption)

| Status | Significado | Acción |
|--------|---|---|
| ACTIVO ✓ | Cifrado OK | Normal |
| ⚠️ DEGRADADO | Error cifrado pero continúa | Revisar logs |
| ❌ CRÍTICO | Cifrado falla | Problema criptográfico |

**Detalles:** `Clave: hash...` = hash de derivación de clave

---

### 🦌 Venado (Evasion Timing)

| Status | Significado | Acción |
|--------|---|---|
| ACTIVO ✓ | Jitter funcionando | Normal |
| ⚠️ DEGRADADO | Jitter deshabilitado | Revisar config |
| ❌ CRÍTICO | Timing predecible | Problema scheduler |

**Detalles:** `Jitter: ±30%` = rango de variabilidad actual

---

### 🦎 Lagartija (Regeneration Healing)

| Status | Significado | Acción |
|--------|---|---|
| ACTIVO ✓ | Mirrors sincronizadas | Normal |
| ⚠️ DEGRADADO | 1–2 mirrors offline | Revisar almacenamiento |
| ❌ CRÍTICO | Todos mirrors offline | Problema crítico |

**Detalles:** `Mirrors: 3/3` = 3 de 3 mirrors online

---

### ⚔️ Tejón (Kill Switch)

| Status | Significado | Acción |
|--------|---|---|
| READY | No activado | Normal |
| 🔴 FROZEN | Congelado, recuperando | Espera, revisar logs |
| ⚠️ RECOVERY_FAILED | Recuperación falló | Escala a autoridad |

**Detalles durante freeze:** `Intento 2/5, próximo en 5.3s`

---

## Sección 3: MÉTRICAS

### Merkle Root

```
Merkle Root: abc123...abc123  [VIGENTE — 2m]
```

- **Valor:** Hash criptográfico de todos los datos capturados
- **[VIGENTE — 2m]:** Hace 2 minutos que se actualizó
- **Uso:** Para detectar modificaciones (si cambia, hay problema)

### Anomalías

```
Anomalías: 0 Benford + 0 Z-score
```

- **Benford:** Detección de manipulación estadística
- **Z-score:** Detección de outliers en métricas
- **0 + 0 = Normal**
- **≥1 en cualquiera = Revisar**

### Conectividad

```
Conectividad: 4/4 endpoints UP  [100%]
```

- **Endpoints:** URLs del CNE siendo monitoreadas
- **4/4:** Los 4 endpoints responden normalmente
- **< 100%:** Revisar accesibilidad red/DNS

### Snapshots

```
Snapshots: 2847 captured  [Last: 30s ago]
```

- **2847:** Total de snapshots capturados desde inicio
- **30s ago:** Último snapshot hace 30 segundos
- **Si > 60s:** Revisar cron/scheduler

---

## Modo Verbose (--verbose)

```bash
centinel panel show --verbose
```

Muestra detalles adicionales:

```
DETALLES VERBOSOS / Verbose Details:
Last merkle update: 2026-05-16T14:30:00Z
Threat events (24h): 2
Recovery attempts: 0
Lock file present: false
```

- **Last merkle update:** Timestamp exacto de última actualización
- **Threat events (24h):** Número de eventos de amenaza en últimas 24h
- **Recovery attempts:** Intentos de recuperación del kill switch
- **Lock file:** Si `/tmp/centinel.lock` existe (congelado?)

---

## Panel JSON (API)

```bash
centinel panel json
```

O vía HTTP:
```bash
curl http://localhost:8000/operator/panel
```

Retorna estructura:
```json
{
  "threat_score": 22,
  "status": "🟢 GREEN",
  "timestamp": "2026-05-16T14:30:00Z",
  "defenses": {
    "corvid": {"emoji": "🐦", "name_es": "Cuervo", ...},
    "cephalopod": {...},
    ...
  },
  "metrics": {
    "merkle_root": "abc123...",
    "merkle_age_seconds": 120,
    ...
  }
}
```

---

## Escenarios Comunes

### Escenario 1: Todo Verde (Normal)

```
Threat Score: 15/100 🟢 VERDE
Todas defensas: ACTIVO ✓
Anomalías: 0 + 0
Conectividad: 100%
```

**Acción:** Continúa monitorando. Sistema operativo.

---

### Escenario 2: Amarillo por Endpoint

```
Threat Score: 35/100 🟡 AMARILLO
Cuervo: ⚠️ DEGRADADO  (1 hermano offline)
Anomalías: 0 + 0
```

**Acción:**
1. Revisa: `tail -50 hashes/attack_log.jsonl`
2. Si dice "endpoint schema changed": Normal (D11 logged)
3. Si hermano offline: Revisar red de hermano

---

### Escenario 3: Rojo por Ataque

```
Threat Score: 90/100 🔴 ROJO
Tejón: 🔴 FROZEN  (Intento 3/5, próximo en 10s)
```

**Acción:**
1. **NO TOQUES NADA.** Sistema está recuperándose automáticamente
2. Espera 30 segundos
3. Si vuelve a verde: Auditoría desde `attack_log.jsonl`
4. Si sigue rojo: Escala a autoridad electoral

---

## Refresh Automático (Monitoring)

```bash
# Ver panel actualizado cada 5 segundos
watch 'poetry run centinel panel show'

# O con jq en vivo
watch 'poetry run centinel panel json | jq .threat_score'
```

---

## Troubleshooting Panel

### Panel no muestra defensas
- Verifica: `ls -la src/centinel/core/animal_defenses.py`
- Reinstala: `poetry install`

### Panel muestra CRITICAL en todo
- Verificar que `hashes/` directorio existe
- Ejecutar `centinel snapshot` para inicializar

### Panel freezado (no se actualiza)
- Mata proceso: `pkill -f 'centinel panel'`
- Reinicia: `centinel panel show`

---

## Referencias Cruzadas

- **Threat Score Logic:** [KILL-SWITCH-CONFIG.md](KILL-SWITCH-CONFIG.md#detección-de-amenaza)
- **Defensa Detallada:** [ANIMAL-DEFENSES-ES.md](ANIMAL-DEFENSES-ES.md)
- **Qué Hacer en Cada Case:** [OPERATOR-RUNBOOKS.md](OPERATOR-RUNBOOKS.md)

---

**Última actualización:** 2026-05-16  
**Status:** v0.1 Operacional
