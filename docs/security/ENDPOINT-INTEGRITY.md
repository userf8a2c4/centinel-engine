# Endpoint Integrity Monitoring

**ES: Monitoreo de Integridad de Endpoints**

Detección de cambios en estructura y disponibilidad de endpoints. Si CNE cambia URLs o estructura JSON, quedará registrado como evidencia forense.

**EN: Detection of changes in endpoint structure and availability. If CNE changes URLs or JSON structure, it will be recorded as forensic evidence.**

---

## Problema Real (Honduras, 2024)

Durante elecciones anteriores, el CNE cambió sus endpoints sin avisar:
- `/api/results` desapareció
- `/api/v2/results` tomó su lugar (estructura similar pero diferente)
- Testigos que querían el endpoint viejo quedaban ciegos

**Solución:** Monitoreo activo de schema de endpoints. Si CNE cambia estructura, quedará documentado en checkpoint con timestamp + merkle root.

---

## Arquitectura

### Schema Fingerprinting

En lugar de almacenar respuestas (datos), guardamos **estructura** (schema):

```json
{
  "url": "https://cne.hn/api/results",
  "status_code": 200,
  "keys": ["votes", "timestamp", "location"],
  "schema_hash": "abc123...def456",
  "timestamp": 1715822400
}
```

- `keys`: Claves JSON top-level (ordenadas alfabéticamente)
- `schema_hash`: SHA256 de las claves (determinista)
- Si CNE agrega/quita campos → hash cambia

### Detection Points

| Cambio | Detectado | Severidad |
|--------|-----------|-----------|
| Endpoint 200 → 503 | ✓ | High |
| Claves {a,b} → {a,b,c} | ✓ | High |
| HTTP header content-type cambio | ✓ | Medium |
| Endpoint timeout | ✓ | High |

### Non-Fatal Design

- Anomalías **logged pero no bloquean**
- Snapshot continúa capturando aunque endpoint cambió
- Forensic record en `attack_log.jsonl`
- Schema merkle root en checkpoint para consensus

---

## Uso

### Registro de Baseline

```python
from centinel.core.endpoint_monitor import EndpointMonitor, EndpointSchema

monitor = EndpointMonitor()

# Después de verificar endpoint por primera vez:
baseline = EndpointSchema(
    timestamp=time.time(),
    url="https://cne.hn/api/results",
    status_code=200,
    content_type="application/json",
    keys=["votes", "timestamp", "location"],
    schema_hash="abc123...def456"
)

monitor.register_baseline(baseline.url, baseline)
```

### Monitoreo Continuo

```python
# En snapshot pipeline (antes de query):
schema = monitor.scan_endpoint("https://cne.hn/api/results")
change = monitor.detect_changes(schema)

if change:
    logger.error("endpoint_changed", change.to_dict())
    # Continuar (non-fatal)
```

### Consensus via Merkle Root

```python
# En checkpoint:
schema_merkle = monitor.schema_merkle_root()
checkpoint = {
    "timestamp": now(),
    "chain_length": len(snapshots),
    "merkle_root": compute_merkle_root(snapshots),
    "endpoint_schema_merkle": schema_merkle,  # NEW
    "operator_signature": "..."
}
```

Auditor verifica:
1. Si todos testigos tienen mismo `endpoint_schema_merkle` → CNE no manipuló
2. Si divergen → detectar qué testigo vio qué cambio

---

## Integration in Snapshot Pipeline

```python
def snapshot(cne_url: str, monitor: EndpointMonitor) -> SnapshotResult:
    """Capture snapshot with endpoint integrity check."""
    
    # Pre-query: scan endpoint structure
    schema = monitor.scan_endpoint(cne_url)
    change = monitor.detect_changes(schema)
    
    if change:
        # Log forensic event (non-fatal)
        forensic_log.append({
            "type": "endpoint_integrity_violation",
            "timestamp": time.time(),
            "change": change,
        })
    
    # Continue snapshot (endpoint change doesn't block data capture)
    data = query_endpoint(cne_url)
    
    return SnapshotResult(
        index=next_index(),
        timestamp=now(),
        data=data,
        endpoint_schema_hash=schema.schema_hash,
        endpoint_healthy=not schema.is_error,
    )
```

---

## Forensic Record

Cada snapshot incluye:
```json
{
  "index": 42,
  "timestamp": "2026-05-16T19:45:00Z",
  "total_votes": 1500000,
  "endpoint_schema_hash": "abc123...def456",
  "endpoint_healthy": true
}
```

Al final de noche electoral, forensic log:
```jsonl
{"event_type": "endpoint_integrity_scan", "timestamp": ..., "changes_detected": 2, "changes": [...]}
```

---

## Multi-Testigo Consensus

### Scenario: CNE Blocks One Testigo

Testigo A: "Endpoint is 200 OK, schema = abc123"
Testigo B: "Endpoint is 503, schema = error"

Checkpoint merkle root difiere → auditor investiga quién está viendo qué.

### Publication

Mirror repos incluyen:
```bash
checkpoint-2026-05-16.json
  └── endpoint_schema_merkle: "xyz..."  # All 3 testigos agree
```

---

## Configuration

No requiere config especial. Monitor se integra en:
- `src/centinel/core/snapshot.py` (capture pipeline)
- `src/centinel/api/routes/audit.py` (forensic endpoint)

Default:
- Timeout: 10 segundos
- Schema hash tolerance: 0 (strict)

---

## Testing

```bash
poetry run pytest tests/test_endpoint_monitor.py -v
```

18 tests cover:
- Schema computation
- Merkle root consistency
- Change detection (status, schema, timeout)
- Forensic export

---

## Future: Honeypot Endpoints

Could extend to monitor:
- Canary endpoints (should always return 404)
- Rate-limit thresholds
- WAF fingerprints

Low priority for v0.1.

---

**Last Updated:** May 2026
