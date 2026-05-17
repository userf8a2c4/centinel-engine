# Incident Response Protocol — Centinel Engine
## Protocolo de Respuesta a Incidentes

**Version:** 1.0 | **Date:** 2025-05-17 | **Status:** Active

---

## Español

### Propósito

Este documento define qué hace el operador de Centinel Engine cuando el sistema detecta una
anomalía estadística o criptográfica durante un proceso electoral. Define la cadena de
notificación, la preservación de evidencia digital y la plantilla de reporte de incidente.

---

### Clasificación de Severidad

| Nivel | Código | Condición | Ejemplo |
|-------|--------|-----------|---------|
| CRÍTICO | `CRITICAL` | Manipulación activa posible | Hash chain rota, rollback detectado |
| ALTO | `HIGH` | Anomalía estadística fuerte | Benford MAD > 0.015, Z-score > 5σ |
| MEDIO | `MEDIUM` | Anomalía estadística moderada | Velocidad de resolución anómala |
| BAJO | `LOW` | Irregularidad menor | Endpoint degradado, datos tardíos |
| INFO | `INFO` | Evento sin anomalía | Snapshot capturado correctamente |

---

### Flujo de Respuesta por Nivel

#### CRÍTICO — Responder en < 15 minutos

```
1. PRESERVAR
   └─ No reiniciar ni detener el sistema
   └─ Exportar snapshot actual: python scripts/export_snapshot.py --full
   └─ Guardar attack_log.jsonl en storage externo inmediato
   └─ Tomar screenshot del panel con timestamp visible

2. NOTIFICAR (en este orden)
   └─ Coordinador técnico del equipo observador
   └─ Entidad legal (UPNFM o equivalente)
   └─ Misión de observación presente (OEA/UE/NDI si aplica)

3. DOCUMENTAR
   └─ Completar plantilla de Reporte de Incidente (ver abajo)
   └─ Registrar: hora exacta UTC, hash del bloque afectado,
      descripción del cambio observado

4. CONSERVAR CADENA DE CUSTODIA
   └─ No compartir datos crudos por canales inseguros
   └─ Usar canales cifrados (Signal, correo GPG) para comunicación inicial
   └─ La evidencia primaria es el archivo attack_log.jsonl + hash chain

5. NO HACER
   └─ No publicar en redes sociales sin coordinación con entidad legal
   └─ No interpretar públicamente como fraude sin validación técnica
   └─ No reiniciar el pipeline sin preservar logs completos
```

#### ALTO — Responder en < 60 minutos

```
1. VERIFICAR
   └─ Confirmar que la anomalía persiste en la siguiente captura
   └─ Revisar si hay correlación con otro departamento o regla

2. NOTIFICAR
   └─ Coordinador técnico

3. DOCUMENTAR
   └─ Registrar en Reporte de Incidente con nivel ALTO
   └─ Incluir: regla disparada, umbral, valor observado, contexto
```

#### MEDIO / BAJO — Responder en < 4 horas

```
1. REGISTRAR en bitácora de turno
2. MONITOREAR si escala a nivel superior
3. INCLUIR en resumen de fin de jornada
```

---

### Cadena de Notificación

```
DETECCIÓN AUTOMÁTICA
        │
        ▼
OPERADOR DE TURNO
        │
        ├─── CRÍTICO/ALTO ──────────────────────────────────┐
        │                                                   │
        ▼                                                   ▼
COORDINADOR TÉCNICO                                 ENTIDAD LEGAL
(responsable de confirmar                           (UPNFM o equivalente)
la anomalía técnicamente)                                   │
        │                                                   │
        └─────────────────────────┬─────────────────────────┘
                                  │
                                  ▼
                    MISIÓN DE OBSERVACIÓN PRESENTE
                    (OEA DECO / UE EOM / NDI si aplica)
                                  │
                                  ▼
                    DECISIÓN CONJUNTA: publicar / litigar / monitorear
```

---

### Preservación de Evidencia Digital

La evidencia forense de Centinel Engine tiene valor legal cuando:

1. **El hash chain está íntegro**: cada bloque referencia el hash del anterior
2. **El ancla Bitcoin existe**: el primer hash del día está en OpenTimestamps
3. **El log forense no fue modificado**: `attack_log.jsonl` tiene su propio hash
4. **Existe testigo técnico**: el operador puede testificar sobre el procedimiento

#### Pasos para exportar evidencia legalmente preservable

```bash
# 1. Exportar snapshot completo con hash chain
python scripts/export_snapshot.py --full --output evidence_$(date -u +%Y%m%dT%H%M%SZ)/

# 2. Calcular SHA-256 del directorio
sha256sum evidence_*/* > evidence_manifest.sha256

# 3. Verificar OpenTimestamps (si disponible)
ots verify evidence_*/checkpoint_*.ots

# 4. Comprimir y firmar el paquete
zip -r evidence_package.zip evidence_*/ evidence_manifest.sha256
sha256sum evidence_package.zip > evidence_package.zip.sha256

# 5. Guardar en al menos 2 ubicaciones externas (storage cloud + USB físico)
```

---

### Plantilla de Reporte de Incidente

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REPORTE DE INCIDENTE — CENTINEL ENGINE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Número de referencia: INC-[YYYYMMDD]-[SEQ]
Fecha/hora UTC: 
Proceso electoral:
Operador:

━━━━━━ DETECCIÓN ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Severidad: [ ] CRÍTICO [ ] ALTO [ ] MEDIO [ ] BAJO
Regla(s) disparada(s):
Valor observado:
Umbral configurado:
Hash del bloque afectado:
Hash del bloque anterior:

━━━━━━ DESCRIPCIÓN ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[Describir en lenguaje claro qué cambió, en qué endpoints,
y qué departamentos o totales están involucrados]

━━━━━━ ACCIONES TOMADAS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
□ Evidencia preservada en: [ruta/URL]
□ Notificado coordinador técnico a las: [hora UTC]
□ Notificada entidad legal a las: [hora UTC]
□ Notificada misión de observación a las: [hora UTC]
□ Screenshot del panel adjunto: [sí/no]

━━━━━━ ANÁLISIS TÉCNICO ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[Análisis del operador: ¿es una anomalía esperada por el
contexto del conteo, o requiere investigación adicional?]

━━━━━━ ESTADO ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[ ] Abierto   [ ] En investigación   [ ] Cerrado
Resolución:

━━━━━━ FIRMA ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Nombre del operador:
SHA-256 del evidence_package.zip:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

### Qué NO constituye un incidente

Estas condiciones son esperadas y NO deben escalar:

- Endpoint degradado durante < 30 minutos (el sistema auto-recupera)
- Datos de baja cobertura en las primeras 2 horas del conteo (< 5% mesas reportadas)
- Velocidad de resolución alta en el cierre del conteo (esperado: aceleración al final)
- Anomalía de Benford en departamentos con < 50 actas (insuficientes para análisis)

---

## English

### Purpose

This document defines what the Centinel Engine operator does when the system detects a
statistical or cryptographic anomaly during an electoral process. It defines the notification
chain, digital evidence preservation, and the incident report template.

---

### Severity Classification

| Level | Code | Condition | Example |
|-------|------|-----------|---------|
| CRITICAL | `CRITICAL` | Active manipulation possible | Broken hash chain, rollback detected |
| HIGH | `HIGH` | Strong statistical anomaly | Benford MAD > 0.015, Z-score > 5σ |
| MEDIUM | `MEDIUM` | Moderate statistical anomaly | Anomalous resolution velocity |
| LOW | `LOW` | Minor irregularity | Degraded endpoint, delayed data |
| INFO | `INFO` | No anomaly event | Snapshot captured correctly |

---

### Digital Evidence Preservation

Centinel Engine forensic evidence has legal value when:

1. **The hash chain is intact**: each block references the hash of the previous one
2. **The Bitcoin anchor exists**: the first hash of the day is in OpenTimestamps
3. **The forensic log was not modified**: `attack_log.jsonl` has its own hash
4. **A technical witness exists**: the operator can testify about the procedure

---

### Incident Report Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INCIDENT REPORT — CENTINEL ENGINE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Reference number: INC-[YYYYMMDD]-[SEQ]
Date/time UTC:
Electoral process:
Operator:

━━━━━━ DETECTION ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Severity: [ ] CRITICAL [ ] HIGH [ ] MEDIUM [ ] LOW
Rule(s) triggered:
Observed value:
Configured threshold:
Hash of affected block:
Hash of previous block:

━━━━━━ DESCRIPTION ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[Describe in plain language what changed, on which endpoints,
and which departments or totals are involved]

━━━━━━ ACTIONS TAKEN ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
□ Evidence preserved at: [path/URL]
□ Technical coordinator notified at: [UTC time]
□ Legal entity notified at: [UTC time]
□ Observation mission notified at: [UTC time]
□ Panel screenshot attached: [yes/no]

━━━━━━ STATUS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[ ] Open   [ ] Under investigation   [ ] Closed
Resolution:

━━━━━━ SIGNATURE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Operator name:
SHA-256 of evidence_package.zip:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

*Bilingual document ES/EN — Last revision: 2025-05-17*
*See also: [METHODOLOGY.md](METHODOLOGY.md) | [THEORY_OF_CHANGE.md](THEORY_OF_CHANGE.md)*
