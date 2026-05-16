# Centinel — Guía Rápida (5 minutos)

## ¿Qué es Centinel?

**Testigo criptográfico de elecciones.** Captura datos de una autoridad electoral, verifica que no fueron modificados, y reporta si detecta manipulación. Sin confiar en nadie.

**No es votación electrónica.** Es auditoría continua del sistema de conteo oficial.

---

## Instalación (1 minuto)

```bash
# Clonar
git clone https://github.com/userf8a2c4/centinel-engine.git
cd centinel-engine

# Instalar
poetry install

# Verificar instalación
poetry run centinel panel show
```

Salida esperada:
```
╔════════════════════════════════════════════════════════════════╗
║ CENTINEL — Estado Operacional / Operational Status             ║
...
║  AMENAZA GENERAL / Threat Score:   22/100 🟢 VERDE             ║
...
```

---

## Operación Básica (2 minutos)

### 1. Ver Estado
```bash
centinel panel show
```

**¿Qué significa cada color?**
- 🟢 **GREEN** (0–30): Operación normal, sin alertas
- 🟡 **YELLOW** (31–74): Anomalía detectada, revisar logs
- 🔴 **RED** (≥75): Amenaza activa, **posible ataque**

### 2. Ejecutar Captura Manual
```bash
centinel snapshot
```

Guarda un snapshot de datos en `hashes/latest_snapshot.json`.

### 3. Configurar Captura Automática (Cron)
```bash
# Capturar cada 30 segundos
centinel cron --interval 30s

# O manualmente en systemd/crontab
*/1 * * * * /usr/bin/poetry -C /path/to/centinel run centinel snapshot
```

### 4. Ver Logs de Auditoría
```bash
# Últimos eventos de ataque
tail -f hashes/attack_log.jsonl

# Buscar eventos específicos
jq '.[] | select(.event == "threat_score")' hashes/attack_log.jsonl | tail -20
```

---

## Las 5 Defensas Animales (1 minuto)

Centinel usa 5 defensas independientes:

| Animal | Defensa | Protege Contra |
|--------|---------|---|
| 🐦 Cuervo | Memoria distribuida | Testigo único vulnerable |
| 🦑 Pulpo | Cifrado tránsito | MITM en red |
| 🦌 Venado | Timing impredecible | Predicción de capturas |
| 🦎 Lagartija | Auto-regeneración | Rootkit local |
| ⚔️ Tejón | Freeze + backoff | Ataque activo en tiempo real |

**Estado actual:** Todas activas ✓

→ [Explicación completa](ANIMAL-DEFENSES-ES.md)

---

## Próximos Pasos (1 minuto)

### Si estás en Verde (🟢)
✅ Sistema operativo. Continúa:
1. Configura cron para captura automática
2. Conecta almacenamiento externo (mirrors)
3. Agrega testigos hermanos (federación)

→ [Guía detallada](OPERATOR-RUNBOOKS.md)

### Si estás en Amarillo (🟡)
⚠️ Anomalía detectada. Pasos:
1. Revisa `centinel panel show --verbose`
2. Lee últimos logs: `tail -50 hashes/attack_log.jsonl`
3. Si es cambio de endpoint CNE: OK, D11 logged
4. Si es estadístico: espera 1h, score debería bajar

→ [Troubleshooting](OPERATOR-RUNBOOKS.md#si-amarillo)

### Si estás en Rojo (🔴)
🚨 Amenaza activa. Pasos:
1. **NO TOQUES NADA.** Sistema se congela automáticamente (Tejón)
2. Espera ~2-39 segundos (intenta recuperarse)
3. Si vuelve a verde: Éxito, revisar logs para auditoría
4. Si permanece rojo >5 min: Escala a autoridad electoral

→ [Procedimiento completo](OPERATOR-RUNBOOKS.md#si-rojo)

---

## Archivos Clave

```
centinel-engine/
├── hashes/
│   ├── latest_snapshot.json      ← Último snapshot capturado
│   ├── attack_log.jsonl          ← Log append-only de ataques
│   ├── checkpoint_frozen.json    ← Estado si fue congelado
│   └── recovery_state.json       ← Estado de recuperación
├── src/centinel/core/
│   ├── kill_switch.py            ← Tejón (freeze + recovery)
│   ├── animal_defenses.py        ← Enum de 5 defensas
│   └── ...
└── docs/
    ├── QUICKSTART.md             ← Este archivo
    ├── ANIMAL-DEFENSES-ES.md     ← Explicación detallada
    ├── OPERATOR-PANEL.md         ← Cómo leer el panel
    ├── OPERATOR-RUNBOOKS.md      ← Qué hacer en cada caso
    ├── ARCHITECTURE.md           ← Deep-dive técnico
    └── SECURITY-REVIEW.md        ← Auditoría de seguridad
```

---

## Comandos Útiles

```bash
# Panel interactivo
centinel panel show
centinel panel show --verbose

# Panel en JSON (para máquinas)
centinel panel json

# Snapshot manual
centinel snapshot

# Ver logs en vivo
tail -f hashes/attack_log.jsonl

# Buscar eventos específicos
jq '.[] | select(.event == "kill_switch_freeze")' hashes/attack_log.jsonl

# Health check
centinel audit  # (v0.2+)
```

---

## Preguntas Frecuentes

### ¿Centinel detecta fraude?
No. Centinel **detecta modificación de datos en custodia**. Si los datos originales del CNE son fraudulentos, Centinel no lo sabrá. Requiere validación electoral independiente.

### ¿Qué pasa si el testigo es hackeado?
Lagartija (auto-regeneración) sincroniza noche a noche con copias externas. Si datos locales fueron modificados, se restauran automáticamente.

### ¿Cuánto cuesta?
**Cero.** Puro código open source + almacenamiento gratuito (S3 free tier, Google Drive, etc.).

### ¿Necesito múltiples testigos?
**Recomendado.** Con 1 testigo, tienes garantía local. Con ≥2, tienes consenso distribuido (consenso Cuervo: 2/3 deben estar de acuerdo).

### ¿Puedo confiar en esto?
Centinel es **matemáticamente auditable**. Todo se puede verificar offline:
- Merkle chain: reproducible
- Benford detection: estadístico replicable
- Bitcoin timestamps: verificables públicamente

Audita el código, no confíes solo en Centinel.

---

## Recursos

| Recurso | Para Quién |
|---------|-----------|
| **QUICKSTART.md** (este) | Primeros 5 min, operadores |
| **ANIMAL-DEFENSES-ES.md** | Entender cada defensa |
| **OPERATOR-PANEL.md** | Leer panel + colores |
| **OPERATOR-RUNBOOKS.md** | Qué hacer en cada escenario |
| **ARCHITECTURE.md** | Deep-dive: teoremas T1–T4 |
| **SECURITY-REVIEW.md** | Auditoría de seguridad |
| **KILL-SWITCH-CONFIG.md** | Detalles del Tejón |

---

## Siguiente Paso

👉 [Lee OPERATOR-RUNBOOKS.md](OPERATOR-RUNBOOKS.md) para configuración completa y procedimientos operacionales.

---

**Última actualización:** 2026-05-16  
**Versión:** 0.1 — Pre-piloto  
**Status:** Listo para auditoría y validación
