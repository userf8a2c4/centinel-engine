# Autosanitaria Interna — Auto-Audit Loop

**ES:** Autosanitaria Interna — Sistema de Auto-Auditoría Continua  
**EN:** Self-Health — Continuous Self-Audit System

---

## ¿Qué es Autosanitaria?

Cada hora, el testigo **se audita a sí mismo** verificando:

1. **Integridad Binaria:** ¿modificaron archivos core del código?
2. **Consistencia de Estado:** ¿logs y checkpoint son coherentes?
3. **Salud de Defensas:** ¿todas 5 defensas animales funcionan?
4. **Coherencia de Mirrors:** ¿datos locales coinciden con copias guardadas?

Si detecta un problema → **intenta restaurar automáticamente** desde mirrors.

---

## Uso

### Ejecutar Auto-Audit Ahora

```bash
centinel audit run
```

Salida esperada:
```
╔════════════════════════════════════════════════════════════════╗
║ AUTOSANITARIA — Self-Audit Report                              ║
╠════════════════════════════════════════════════════════════════╣
║  Timestamp:       2026-05-16T14:30:00Z                        ║
║  Health Score:    100.0% 🟢                                    ║
║                                                                ║
║  CHECKS:                                                       ║
║  ✓ Binary Integrity                                        ║
║  ✓ State Consistency                                        ║
║  ✓ Defense Health (5/5)                                 ║
║  ✓ Mirror Coherence                                        ║
╚════════════════════════════════════════════════════════════════╝
```

### Ver Últimos Reportes

```bash
centinel audit history --limit 20
```

Ejemplo:
```
AUTOSANITARIA — Last 20 Reports
======================================================================
🟢 2026-05-16T14:30:00Z        Health: 100.0%
🟢 2026-05-16T13:30:00Z        Health: 100.0%
🟢 2026-05-16T12:30:00Z        Health: 100.0%
🟡 2026-05-16T11:30:00Z        Health: 75.0%
```

### Ver Solo Health Score

```bash
centinel audit health
```

Salida:
```
🟢 Health Score: 100.0%
```

---

## Health Score

### Escala

```
1.0 (100%) = 🟢 PERFECTO       4/4 checks OK
0.75 (75%) = 🟡 DEGRADADO      3/4 checks OK
0.50 (50%) = 🟡 CRÍTICO        2/4 checks OK
0.25 (25%) = 🔴 FALLIDO        1/4 checks OK
0.0 (0%)   = 🔴 SIN SERVICIO   0/4 checks OK
```

### Qué Significa Cada Nivel

| Score | Estado | Acción |
|-------|--------|--------|
| ≥0.75 | 🟢 Operativo | Continúa monitoreando normalmente |
| 0.50–0.74 | 🟡 Degradado | Revisa logs, escala si empeora |
| <0.50 | 🔴 Crítico | Escala inmediatamente |

---

## 4 Componentes de Health

### 1. Binary Integrity (Integridad Binaria)

**¿Qué verifica?** MD5/SHA256 de archivos core:
- `src/centinel/core/custody.py`
- `src/centinel/core/kill_switch.py`
- `src/centinel/core/animal_defenses.py`
- `src/centinel/core/anomaly_detector.py`
- `src/centinel/core/endpoint_monitor.py`

**Falla si:** Algún archivo fue modificado.

**Causa probable:**
- Rootkit local modificó archivos
- Admin cambió configuración sin commit
- Corrupción de almacenamiento

**Acción:**
```bash
# Verifica git status
git status src/centinel/core

# Si hay cambios no auditados
git diff src/centinel/core
```

---

### 2. State Consistency (Consistencia de Estado)

**¿Qué verifica?**
- `hashes/attack_log.jsonl` tiene timestamps monotónicos (nunca atrasa)
- `hashes/checkpoint.json` es válido (Merkle root calculable)
- Snapshots en checkpoint son coherentes

**Falla si:**
- Log tiene timestamps fuera de orden
- Checkpoint corrompido
- Merkle mismatch

**Causa probable:**
- Filesystem corruption
- Fallo durante escritura
- Ataque: intentó reescribir logs

**Acción:**
```bash
# Verifica últimos eventos
tail -50 hashes/attack_log.jsonl | jq .

# Si corrupto, restaura desde mirror
centinel regeneration restore --source-mirror primary
```

---

### 3. Defense Health (Salud de Defensas)

**¿Qué verifica?** Todas 5 defensas animales funcionan:

| Defensa | Check |
|---------|-------|
| 🐦 Cuervo (Corvid) | ¿Contacta testigos hermanos? |
| 🦑 Pulpo (Cephalopod) | ¿Cifrado derivado es válido? |
| 🦌 Venado (Evasion) | ¿Jitter está activo? |
| 🦎 Lagartija (Regeneration) | ¿≥2 mirrors accesibles? |
| ⚔️ Tejón (Kill Switch) | ¿Lock file puede crearse/borrarse? |

**Falla si:** ≥2 defensas están inactivas.

**Causa probable:**
- Red caída (Cuervo falla)
- Problemas de almacenamiento (Lagartija falla)
- Scheduler pausado (Venado falla)
- Filesystem readonly (Tejón falla)

**Acción:**
```bash
# Ver cuál defensa falló
centinel audit run --verbose | jq .defense_health

# Reiniciar componente específico
centinel status --component cuervo
```

---

### 4. Mirror Coherence (Coherencia de Mirrors)

**¿Qué verifica?** Datos locales = copias en almacenamiento externo.

**Compara:**
- Merkle root local vs mirrors
- Attack log local vs mirrors
- Checkpoint local vs mirrors

**Falla si:** Divergencia detectada (local ≠ mirrors).

**Causa probable:**
- Mirror offline (no puedo verificar)
- Datos locales fueron modificados
- Mirrors desincronizados por fallo de red

**Acción:**
```bash
# Restaura desde mirror más confiable
centinel regeneration restore --source-mirror backup

# O fuerza re-sync
centinel regeneration sync --force
```

---

## Configuración

### Habilitar Auto-Audit Horario

```bash
centinel audit run --enable-cron
```

Esto agrega entrada a crontab:
```bash
0 * * * * /path/to/poetry -C /path/to/centinel run centinel audit run
```

### Configuración Avanzada

**Archivo:** `command_center/advanced_security_config.yaml`

```yaml
auto_audit:
  enabled: true
  interval_seconds: 3600      # Cada hora
  binary_scan: true           # Verificar integridad binaria
  state_check: true           # Verificar consistencia logs
  defense_test: true          # Probar 5 defensas
  mirror_verify: true         # Verificar coherencia mirrors
  min_health_alert: 0.75      # Alerta si < 75%
  max_restore_attempts: 3     # Intentos de auto-restore
```

---

## Escenarios Comunes

### Escenario 1: Todo Verde (100%)

```
Health Score: 100.0% 🟢
✓ Binary Integrity
✓ State Consistency
✓ Defense Health (5/5)
✓ Mirror Coherence
```

**Significado:** Sistema 100% íntegro.  
**Acción:** Continúa monitoreando.

---

### Escenario 2: Amarillo por Espejo (75%)

```
Health Score: 75.0% 🟡
✓ Binary Integrity
✓ State Consistency
✓ Defense Health (5/5)
✗ Mirror Coherence
```

**Significado:** Mirror diverge de datos locales.  
**Acción:**
1. Revisa conectividad del mirror: `ping backup-mirror.example.com`
2. Si está offline: OK, lo reporta como "stale"
3. Si está online pero diverge: **Alerta de integridad**, restaura desde local

```bash
# Restaura desde copia local (confiable)
centinel regeneration restore --source local
```

---

### Escenario 3: Crítico por Defensa (50%)

```
Health Score: 50.0% 🔴
✓ Binary Integrity
✓ State Consistency
✗ Defense Health (2/5)
✗ Mirror Coherence
```

**Significado:** Fallan 2+ defensas, posiblemente bajo ataque.  
**Acción:**
1. **ESCALA INMEDIATAMENTE** a autoridad electoral
2. Proporciona:
   - `hashes/attack_log.jsonl` (últimas 1000 líneas)
   - Reporte: `centinel audit history --limit 100 > audit_report.txt`
   - Status: `centinel panel show --verbose > status.txt`

---

### Escenario 4: Fallo Permanente (0%)

```
Health Score: 0.0% 🔴
✗ Binary Integrity
✗ State Consistency
✗ Defense Health (0/5)
✗ Mirror Coherence
```

**Significado:** Compromise total probable.  
**Acción:**
1. **APAGA TESTIGO AHORA.** No intentes restaurar sin autoridad electoral.
2. Preserva:
   - Disco completo (para forense)
   - Logs de syslog
   - Network traffic captures
3. Contacta autoridad electoral con evidencia

---

## Troubleshooting

### "Health < 0.75, ¿qué hago?"

1. Ejecuta con verbose:
   ```bash
   centinel audit run --verbose
   ```

2. Identifica cuál check falla:
   - **Binary Integrity falla:** `git status src/centinel/core`
   - **State Consistency falla:** `tail -100 hashes/attack_log.jsonl | jq .timestamp`
   - **Defense Health falla:** `centinel panel show` → cuál animal está down
   - **Mirror Coherence falla:** `ping backup-mirror`

3. Según el fallo:
   - **Binario:** Restaura código desde git
   - **Estado:** Restaura desde mirror
   - **Defensa:** Reinicia componente específico
   - **Mirror:** Verifica red, resincroniza

### "Health fluctúa entre 75% y 50%"

**Causa probable:** Conectividad a mirrors es inestable (red lenta).

**Acción:**
- Revisa conectividad: `centinel connectivity check`
- Aumenta timeout en config: `mirror_check_timeout_seconds: 30`
- Considera mirror más cercano (geográficamente)

### "Health siempre 50%, defensa Cuervo falla"

**Causa probable:** Testigos hermanos no responden.

**Acción:**
```bash
# Verifica hermanos configurados
centinel federation list

# Intenta contactar manualmente
curl http://hermano1.example.com:8000/operator/panel
```

Si hermanos están offline:
- Operación degradada, continúa en modo local
- Health score refleja ausencia de consenso (esperado)

---

## Referencia Rápida

| Comando | Uso |
|---------|-----|
| `centinel audit run` | Ejecutar audit ahora |
| `centinel audit run --verbose` | Audit con detalles completos |
| `centinel audit history --limit 20` | Ver últimos 20 reportes |
| `centinel audit health` | Ver solo health score |
| `centinel audit run --enable-cron` | Habilitar audit horario |

---

## Archivos Relacionados

- **`hashes/audit_log.jsonl`** — Append-only log de reportes
- **`hashes/attack_log.jsonl`** — Eventos de amenaza/anomalía
- **`command_center/advanced_security_config.yaml`** — Configuración auto-audit
- **`docs/KILL-SWITCH-CONFIG.md`** — Recuperación automática (Tejón)
- **`docs/ANIMAL-DEFENSES-ES.md`** — Detalles de 5 defensas

---

## FAQ

### ¿Cada cuánto se ejecuta auto-audit?

Por defecto: **cada hora (3600 segundos)**.  
Configurable en `advanced_security_config.yaml`.

### ¿Si health score baja a 0%, ¿se activa kill switch?

**No.** Kill switch se activa por threat score (merkle divergence, Benford, etc.), no por health score.  
Health score es diagnosis; threat score es amenaza detectada.

### ¿Puedo desactivar auto-audit?

Sí:
```yaml
auto_audit:
  enabled: false
```

⚠️ **No recomendado.** Auto-audit es protección esencial.

### ¿Los reportes de audit se borran?

No. `audit_log.jsonl` es **append-only**. Nunca se borran.  
Puedes mantener histórico ilimitado o comprimir logs viejos.

---

## Referencias Técnicas

- **Teorema T1 (Cadena de Hashes):** Todos los snapshots están conectados criptográficamente. Integridad binaria detecta si los archivos que generan hashes fueron modificados.
- **Teorema T4 (Federación):** Múltiples testigos deben estar de acuerdo. Defense Health (Cuervo) verifica que contacta hermanos.
- **Non-fatal Design:** Incluso si auto-audit falla, testigo continúa capturando. No bloquea operación; solo alerta.

---

## Recursos

- [QUICKSTART.md](QUICKSTART.md) — Primeros 5 minutos
- [OPERATOR-PANEL.md](OPERATOR-PANEL.md) — Panel operador
- [ANIMAL-DEFENSES-ES.md](ANIMAL-DEFENSES-ES.md) — Defensa detallada
- [KILL-SWITCH-CONFIG.md](KILL-SWITCH-CONFIG.md) — Tejón + recuperación

---

**Última actualización:** 2026-05-16  
**Versión:** 0.1 — Pre-piloto  
**Status:** Operacional
