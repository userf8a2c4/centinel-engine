# Arquitectura Técnica — Deep-Dive

**ES:** Arquitectura Técnica Completa — Teoremas, Flujos, Formatos  
**EN:** Complete Technical Architecture — Theorems, Flows, Formats

---

## Teoremas Fundamentales (T1–T4)

### T1: Cadena de Hashes (Hash Chain Integrity)

**Definición:**  
Todo snapshot `S_i` está criptográficamente vinculado al anterior `S_{i-1}` mediante SHA-256. Si alguien modifica cualquier dato pasado, el hash mismatch propaga hacia adelante.

**Fórmula:**
```
Merkle_Root = SHA256(concat(S_1, S_2, ..., S_n))

Para cualquier S_i:
  hash_i = SHA256(content_i)
  Merkle difiere si content_i cambia
```

**Protección:**
- ✅ Detecta modificación de datos históricos
- ✅ Detecta reordenamiento de snapshots
- ✅ Imposible "arreglar" un snapshot sin propagar cambios

**Limitación:**
- ❌ No prueba quién capturó el snapshot (requiere T2)
- ❌ No marca timestamp (requiere T3)

---

### T2: Consenso Distribuido (Byzantine Consensus)

**Definición:**  
Con ≥3 testigos, el sistema tolera 1 testigo faulty/malicioso. Usa Merkle root como "verdad": si ≥2 testigos reportan Merkle_Root_A, y 1 reporta Merkle_Root_B, se detecta divergencia = ataque.

**Fórmula:**
```
consensus_valid = (count(merkle_root = A) >= ceil(n/2))

Ejemplos:
  n=3: necesita ≥2 testigos iguales
  n=4: necesita ≥2 testigos iguales
  n=5: necesita ≥3 testigos iguales
```

**Protección:**
- ✅ Detecta bloqueo selectivo (algunos testigos manipulados)
- ✅ Detecta sybil attack (múltiples "testigos" falsos)
- ✅ Tolera 1 testigo completamente comprometido

**Limitación:**
- ❌ Requiere ≥2 testigos vivos (single testigo = sin consenso)
- ❌ Red partition puede romper consenso (mitigation: T3 timestamp)

---

### T3: Timestamp Independiente (External Anchor)

**Definición:**  
Merkle root se ancla a Bitcoin blockchain vía OpenTimestamps. Costo: cero, verificación: offline, confianza: Bitcoin network.

**Flujo:**
```
1. Computar: Merkle_Root = SHA256(snapshots)
2. Enviar: Merkle_Root → OpenTimestamps
3. OTS retorna: Bitcoin TX ID + prueba de inclusión
4. Verificar: reproducir prueba offline sin tocar Merkle_Root
```

**Protección:**
- ✅ Prueba: "Merkle_Root existía en fecha X" (verificable públicamente)
- ✅ Imposible retrodatar (Bitcoin es inmutable)
- ✅ Independiente de Centinel (auditor externo confía en Bitcoin, no en nosotros)

**Limitación:**
- ❌ Latencia: puede tardar 10+ min en ser incluido en bloque
- ❌ Solo sirve para timestamp, no para integridad de datos

---

### T4: Federación de Testigos (Multi-Witness Federation)

**Definición:**  
Múltiples testigos independientes ejecutan Centinel en paralelo. Cada uno captura datos, computa Merkle, reporta. Sistema detecta si uno diverge.

**Flujo Típico (3 testigos):**
```
Hora H:
  Testigo A: captura → Merkle_A → reporta
  Testigo B: captura → Merkle_B → reporta
  Testigo C: captura → Merkle_C → reporta

Consenso:
  Si Merkle_A == Merkle_B == Merkle_C → ✅ VÁLIDO
  Si Merkle_A ≠ Merkle_C → 🚨 DIVERGENCIA (ataque en C o A)

Reporte:
  Divergencia → log a attack_log.jsonl
  Auto-recuperación Lagartija (T4) intenta restore desde mirrors
```

**Protección:**
- ✅ Detecta rootkit en 1 testigo (otros 2 lo exponen)
- ✅ Detecta MITM selectivo (CNE devuelve datos falsos solo a testigo C)
- ✅ Detecta bloqueo (testigo offline es evidente)

**Limitación:**
- ❌ Si >50% testigos comprometidos, consenso es falso
- ❌ Si red entre testigos está particionada, consenso imposible (mitigation: T3)

---

## Flujo Operacional End-to-End

### Captura Periódica (Cada 30–60 segundos)

```
┌─────────────────────────────────────────────────────────┐
│ SNAPSHOT: Cita datos de endpoints del CNE               │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ NORMALIZACIÓN: Parse JSON, valida schema (D11 activo)   │
│ - Si schema cambió: log evento, continúa igual          │
│ - Si datos corrupto: flag anomalía, intenta restaurar   │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ DEFENSAS ANIMALES EN PARALELO:                          │
│ 🐦 Cuervo: contacta hermanos → consenso                 │
│ 🦑 Pulpo: cifra respuesta en tránsito                   │
│ 🦌 Venado: jitter ±30% en timing                        │
│ 🦎 Lagartija: prepara copia para mirrors                │
│ ⚔️ Tejón: evalúa threat score, freeze si ≥75           │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ HASH CHAIN (T1): Merkle_Root = SHA256(snapshots)        │
│ - Almacena en hashes/latest_snapshot.json               │
│ - Compara vs anterior → divergencia = ataque            │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ ANOMALÍA DETECTION: Benford + Z-score                   │
│ - Si anomalía: +25 pts a threat score                   │
│ - Log a attack_log.jsonl                                │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ ENDPOINT MONITOR (D11): Schema de respuesta cambió?     │
│ - Si cambió: log evento (NO activa kill switch)         │
│ - Propaga a hermanos para consensus                     │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ THREAT SCORE EVAL: ¿Merkle diverge + Benford alto?     │
│ - Score < 75: continúa normal (green status)            │
│ - Score ≥ 75: FREEZE (Tejón activo)                    │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ CONSENSUS (T2 + T4): ¿Hermanos están de acuerdo?        │
│ - ≥2/3 testigos tienen Merkle_Root = nuestro → OK      │
│ - Divergencia detectada → log + federación alerta       │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ EXTERNAL ANCHOR (T3, cada 1h): OpenTimestamps           │
│ - Merkle_Root → Bitcoin blockchain                      │
│ - Auditor puede verificar offline                       │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ NOCHE SYNC (Lagartija): Sincroniza con mirrors          │
│ - Verifica coherencia vs copias guardadas               │
│ - Si divergencia: restaura de mayoría                   │
│ - Log append-only: audit trail completo                 │
└─────────────────────────────────────────────────────────┘
```

---

## Estructuras de Datos Clave

### 1. Snapshot

```json
{
  "timestamp": "2026-05-16T14:30:00Z",
  "source": "https://cne.hn/api/results",
  "data": {
    "total_votes": 2847392,
    "departments": [
      {"name": "Cortés", "votes": 342872},
      {"name": "Francisco Morazán", "votes": 1028374}
    ]
  },
  "schema_hash": "abc123def456...",
  "merkle_root_previous": "prev_hash...",
  "captured_by": "testigo-primary",
  "signatures": {
    "testigo-primary": "sig_ed25519...",
    "testigo-backup": "sig_ed25519..."
  }
}
```

### 2. Checkpoint

```json
{
  "timestamp": "2026-05-16T14:30:00Z",
  "merkle_root": "abc123def456...",
  "total_snapshots": 2847,
  "snapshots": [
    {"timestamp": "...", "hash": "..."},
    {"timestamp": "...", "hash": "..."}
  ],
  "frozen_at": null,
  "recovery_state": {
    "attempt_count": 0,
    "is_frozen": false,
    "last_freeze_timestamp": null
  },
  "opentimestamps_proof": {
    "bitcoin_txid": "abcd1234...",
    "inclusion_proof": "base64...",
    "timestamp": "2026-05-16T15:30:00Z"
  },
  "mirrors": {
    "primary": {"url": "s3://bucket/", "status": "synced", "last_sync": "2026-05-16T14:00:00Z"},
    "backup": {"url": "gs://bucket/", "status": "synced", "last_sync": "2026-05-16T14:00:00Z"}
  }
}
```

### 3. Attack Log (Append-Only)

```jsonl
{"timestamp": 1715875800.123, "event": "snapshot_captured", "count": 2847, "hash": "abc123"}
{"timestamp": 1715875860.456, "event": "anomaly_detected", "type": "benford", "severity": "warning"}
{"timestamp": 1715875920.789, "event": "endpoint_schema_changed", "endpoint": "cne.hn", "action": "logged"}
{"timestamp": 1715875980.001, "event": "threat_score_evaluated", "score": 22, "status": "green"}
{"timestamp": 1715876040.234, "event": "consensus_check", "agreement": "2/3", "testigos": ["A", "B", "C"]}
{"timestamp": 1715876100.567, "event": "federation_attestation_sent", "recipients": 2}
```

---

## Modelos de Amenaza

### Modelo 1: Testigo Único

```
╔════════════════════════════════════════════╗
║ CNE (Adversario Potencial)                 ║
║                                            ║
║  Puede:                                    ║
║  ✓ Modificar datos en tránsito (MITM)      ║
║  ✓ Intercambiar snapshot válido            ║
║  ✓ Rootkit + modificar binario Centinel    ║
║                                            ║
║  No puede:                                 ║
║  ✗ Falsificar timestamp Bitcoin (T3)       ║
║  ✗ Romper T1 (hash chain es inviolable)    ║
║                                            ║
║  LIMITACIÓN: Sin hermanos, sin consenso    ║
║  Asunción: Auditor confía en Merkle chain  ║
╚════════════════════════════════════════════╝

Defensa: Auditoría posterior es posible
- Merkle root se puede reproducir
- Benford detection es verificable
- T3 timestamp es independiente
```

### Modelo 2: Testigos Múltiples (n=3)

```
╔─────────────────────────────────────────────────────────╗
║ Testigo A (Nodo 1)   Testigo B (Nodo 2)   Testigo C     ║
║ ┌──────────────┐     ┌──────────────┐     ┌──────────┐  ║
║ │ Merkle_A     │     │ Merkle_B     │     │ Merkle_C │  ║
║ │ abc123...    │     │ abc123...    │     │ xyz999.. │  ║
║ └──────────────┘     └──────────────┘     └──────────┘  ║
║        │                   │                    │        ║
║        └───────────────┬───────────────────────┘        ║
║                        │                                 ║
║                    CONSENSUS: 2/3 acuerdan abc123       ║
║                    DIVERGENCIA: C ≠ A,B → ALERTA 🚨     ║
║                                                          ║
║ Impacto: Imposible romper sin comprometer ≥2 testigos   ║
╚─────────────────────────────────────────────────────────╝

Escenarios:
1. C es rootkiteado → A,B lo detectan
2. MITM en C → A,B lo detectan
3. Red partition A|B,C → timestamp (T3) lo resuelve
```

### Modelo 3: Ataque Activo en Noche Electoral

```
Timeline:
T+0min: CNE publica datos falsos
T+1min: Centinel captura → Merkle_A
        Testigo B captura → Merkle_B (igual)
        Testigo C captura → Merkle_C (igual)
        ⇒ Consensus OK, no hay ataque detectado YET

T+5min: Auditor externo verifica Benford
        ⇒ χ² = 45.2 (crítico, p<0.001)
        ⇒ Threat score += 25 pts
        ⇒ Kill Switch: FROZEN

T+6min: Testigo auto-recover intenta:
        - Verifica local integrity
        - Restaura desde mirrors
        - Si ambas fallan: permanece frozen, ESCALALA

T+30min: Autoridad electoral contactada
         Merkle chain + Benford report + attack_log.jsonl
         = Evidencia forense completa
```

---

## Algoritmos Clave

### Merkle Root Computation

```python
def compute_merkle_root(snapshots):
    """
    Calcula raíz Merkle de todos los snapshots.
    Árbol binario completo, SHA-256.
    """
    if not snapshots:
        return SHA256(b"")
    
    # Convertir cada snapshot a hash
    leaves = [SHA256(json.dumps(s).encode()) for s in snapshots]
    
    # Construir árbol binario completo
    while len(leaves) > 1:
        if len(leaves) % 2 == 1:
            leaves.append(leaves[-1])  # Duplica último si impar
        
        parents = []
        for i in range(0, len(leaves), 2):
            parent = SHA256(leaves[i] + leaves[i+1])
            parents.append(parent)
        
        leaves = parents
    
    return leaves[0].hex()
```

### Benford Detection (χ² test)

```python
def benford_chi_square(values):
    """
    Detecta manipulación estadística usando ley de Benford.
    Retorna χ² statistic (crítico si > 15.99 para α=0.05)
    """
    first_digits = [int(str(abs(int(v)))[0]) for v in values if v > 0]
    
    if len(first_digits) < 30:
        return 0  # Muestra muy pequeña
    
    observed = [first_digits.count(d) for d in range(1, 10)]
    expected = [len(first_digits) * math.log10(1 + 1/d) for d in range(1, 10)]
    
    chi_square = sum((o - e)**2 / e for o, e in zip(observed, expected))
    return chi_square  # Si > 15.99, hay anomalía
```

### Threat Score Evaluation

```python
def evaluate_threat_score():
    """
    Puntuación de amenaza: 0–100 (activates kill_switch si ≥75)
    
    SOLO integridad de datos, IGNORA cambios de API.
    """
    score = 0
    
    # Merkle divergence: ±3 snapshots
    if check_merkle_divergence(min_samples=3):
        score += 40
    
    # Benford anomaly
    if get_benford_chi_square() > 15.99:
        score += 25
    
    # Connectivity loss (>2min)
    if check_complete_connectivity_loss(timeout=120):
        score += 20
    
    # Federation consensus broken
    if not check_federation_consensus(threshold=2):
        score += 35
    
    # IGNORA: endpoint schema cambió (D11 logged, score = 0)
    # IGNORA: URL cambió (D11 logged, score = 0)
    
    return min(score, 100)
```

---

## Garantías de Seguridad

### Lo Que Centinel PRUEBA

| Garantía | Basado en | Nivel |
|----------|-----------|-------|
| Datos no fueron modificados en custodia | T1 (Merkle) | Alto |
| Múltiples testigos están de acuerdo | T2+T4 (Consenso) | Alto |
| Merkle root existía en fecha X | T3 (OTS Bitcoin) | Muy Alto |
| Anomalía estadística presente | Benford + Z-score | Medio |
| Endpoint schema cambió | D11 Monitor | Informativo |

### Lo Que Centinel NO PRUEBA

| Claim | Razón | Requiere |
|-------|-------|----------|
| Datos originales del CNE son correctos | No audita captura, solo custodia | Validación electoral independiente |
| Fraude en acta original | Centinel es custodia, no validador | Auditoría en punto de origen |
| Voto fue registrado correctamente | No es sistema de votación | Acta física + Centinel juntos |

---

## Configuración Recomendada

### Production (Elección Nacional)

```yaml
centinel:
  capture:
    interval_seconds: 30  # Cada 30s
    timeout_seconds: 10   # Timeout agresivo
  
  endpoints:
    sources:
      - url: "https://cne.hn/api/results"
        schema_tolerance: 0.1  # 10% cambio permite
        timeout: 10
      - url: "https://cne.hn/api/v2/results-live"
        timeout: 10
  
  federation:
    testigos:
      - "testigo-a.example.com:8000"
      - "testigo-b.example.com:8000"
      - "testigo-c.example.com:8000"
    consensus_threshold: 2  # 2/3 requerido
  
  kill_switch:
    threat_threshold: 75  # ≥75 = freeze
    max_recovery_attempts: 5
    backoff_base_seconds: [2, 5, 10, 20, 30]
  
  external_anchor:
    enabled: true
    provider: "opentimestamps"
    interval_seconds: 3600  # Cada hora
    fallback: "testnet"
  
  mirrors:
    enabled: true
    providers:
      - type: "s3"
        bucket: "centinel-primary-hn"
        region: "us-east-1"
      - type: "gcs"
        bucket: "centinel-backup-hn"
  
  anomaly_detection:
    benford_enabled: true
    benford_threshold: 5.99  # χ² critical value
    zscore_enabled: true
    zscore_threshold: 3.0  # 3σ
    min_snapshots: 100  # No alarmear con <100 datos
  
  auto_audit:
    enabled: true
    interval_seconds: 3600  # Cada hora
    min_health_threshold: 0.75
```

---

## Verificación Offline (Auditor)

Un auditor externo puede verificar completamente sin confiar en Centinel:

```bash
# 1. Obtener: hashes/attack_log.jsonl + hashes/checkpoint.json
# 2. Computar Merkle root localmente
merkle=$(python3 -c "
  import json, hashlib
  with open('checkpoint.json') as f:
    snapshots = json.load(f)['snapshots']
  # Recompute merkle (ver compute_merkle_root arriba)
")

# 3. Verificar contra Bitcoin timestamp
# Usar herramienta OTS pública: https://opentimestamps.org/
ots_verify checkpoint.json

# 4. Analizar Benford (cualquier stat package)
# R: benford.analysis(log10(values))
# Python: usar scipy.stats.chisquare

# 5. Inspeccionar attack_log.jsonl línea por línea
# ¿Hay eventos sospechosos? ¿Freeze events? ¿Divergence?
jq '.[] | select(.event == "threat_score") | .score' attack_log.jsonl
```

---

## Referencias Técnicas

- **T1 Implementation:** `src/centinel/core/hasher.py`, `compute_merkle_root()`
- **T2 Implementation:** `src/centinel/core/corvid_broadcast.py`, `FederationCoordinator`
- **T3 Implementation:** `src/centinel/core/opentimestamps.py`, `ExternalAnchor`
- **T4 Implementation:** `src/centinel/core/corvid_broadcast.py`, federation consensus
- **Anomaly Detection:** `src/centinel/core/anomaly_detector.py`, `AnomalyDetector`
- **Kill Switch:** `src/centinel/core/kill_switch.py`, `KillSwitch` class
- **Endpoint Monitor:** `src/centinel/core/endpoint_monitor.py`, `EndpointMonitor`

---

**Última actualización:** 2026-05-16  
**Versión:** 0.1 — Pre-piloto  
**Status:** Operacional
