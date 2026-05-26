# External Anchoring — Bitcoin via OpenTimestamps

**ES: Anclaje Externo — Bitcoin vía OpenTimestamps**

Provee timestamping criptográfico a Bitcoin blockchain. Permite auditor verificar: "Este checkpoint fue creado antes de TIMESTAMP" sin confiar en reloj del testigo.

**EN: Provides cryptographic timestamping to Bitcoin blockchain. Allows auditor to verify: "This checkpoint was created before TIMESTAMP" without trusting witness clock.**

---

## Why External Anchoring?

**El Problema:** Testigo puede falsear su reloj (adelantarlo/atrasarlo).

**Solución:** Anclar Merkle root a Bitcoin blockchain (inmutable, distribuido).

**Resultado:** Checkpoint + Bitcoin TX hash = prueba que datos existían en o antes de cierto bloque.

---

## Architecture

### OpenTimestamps Protocol

1. Testigo computa Merkle root: `abc123...def456`
2. Solicita timestamp a servidor OTS público (gratis, sin clave)
3. Servidor OTS:
   - Acepta hash (no datos)
   - Agrega a árbol que se ancla a Bitcoin regularmente
4. OTS devuelve "prueba":
   - `ots_proof`: Árbol de hashes hasta Bitcoin root
   - `bitcoin_tx`: TX hash en blockchain
   - `bitcoin_block`: Bloque donde fue incluida

### Non-Fatal Design

- Si OTS falla → continuar sin anclaje (checkpoint se publica igual)
- Assurance degradada pero operativo (witness sigue capturando)
- Fallback a Arbitrum si OTS no disponible (futuro)

### Forensic Logging

Cada intento de anclaje queda registrado:
```json
{
  "event_type": "external_anchor_attempt",
  "checkpoint_hash": "abc123...def456",
  "ots_success": true,
  "bitcoin_tx": "0x789abc...",
  "bitcoin_block": 12345,
  "timestamp": 1715822400
}
```

---

## Integration in Checkpoint Pipeline

```python
from centinel.anchor.opentimestamps_client import MultichainAnchor

# In snapshot.py or checkpoint.py:
anchor = MultichainAnchor(testnet=False)  # mainnet by default

checkpoint = {
    "timestamp": now_iso(),
    "chain_length": len(snapshots),
    "merkle_root": compute_merkle_root(snapshots),
    "endpoint_schema_merkle": monitor.schema_merkle_root(),
    # ... other fields
}

# Attempt to anchor
checkpoint = anchor.anchor_checkpoint(checkpoint)

# Result:
# {
#   "merkle_root": "...",
#   "ots_proof": "base64...",
#   "bitcoin_tx": "0x789abc123...",
#   "bitcoin_block": 12345,
#   "anchor_chain": "bitcoin"
# }
```

---

## Verification (Auditor Side)

### Online Verification

Auditor can verify anchor without running full Bitcoin node:

```bash
# 1. Get checkpoint
curl https://witness.example.com/api/checkpoint | jq .

# 2. Verify OTS proof
# Uses online OTS verify endpoint:
curl -X POST https://verify.opentimestamps.org \
  -d '{"ots_proof": "...", "hash": "..."}'

# 3. Verify Bitcoin TX
# Query blockchain explorer:
# https://blockchain.info/tx/{bitcoin_tx}
```

### Offline Verification

Full node operators can verify locally:
```bash
# Download Bitcoin block {bitcoin_block}
# Check that TX {bitcoin_tx} contains Merkle root
# Compute SPV proof to root
```

---

## Configuration

### Mainnet (Production)

```python
anchor = MultichainAnchor(testnet=False)
# Uses: https://a.pool.opentimestamps.org, etc.
```

### Testnet (Development)

```python
anchor = MultichainAnchor(testnet=True)
# Uses: https://testnet.opentimestamps.org
# Bitcoin testnet chain
```

### Retry Logic

```python
client = OpenTimestampsClient(
    timeout=30.0,       # HTTP timeout
    max_retries=3,      # Retry 3x with exponential backoff
    use_testnet=False,
)

proof = client.stamp(merkle_root)
# Retries: 1s, 2s, 4s delays on transient failures
```

---

## Testing

### Unit Tests

```bash
poetry run pytest tests/test_opentimestamps_client.py -v
```

17 tests cover:
- OTS client creation (mainnet/testnet)
- Proof request and validation
- Retry logic and exponential backoff
- Multi-chain fallback
- Forensic logging

### Integration Test (Live OTS)

```python
# Optional: test against live OTS server
import time
from centinel.anchor.opentimestamps_client import OpenTimestampsClient

client = OpenTimestampsClient(use_testnet=True)
proof = client.stamp("test-checkpoint-" + str(int(time.time())))

if proof:
    print(f"Bitcoin TX: {proof.bitcoin_tx}")
    print(f"Bitcoin Block: {proof.bitcoin_block}")
else:
    print("OTS unavailable")
```

---

## Bitcoin Proof of Existence

### What Auditor Verifies

1. **Merkle root in checkpoint:** `abc123...def456`
2. **OTS proof:** proves hash was submitted before date X
3. **Bitcoin TX:** includes Merkle root in output or scriptPubKey
4. **Bitcoin block:** chain of PoW work above it (immutable)

### Result

✓ Timestamp is **independent of witness clock**
✓ Immutable (changing block requires redoing all PoW)
✓ Publicly verifiable (any Bitcoin node)

---

## Future: Multi-Chain

Current: Bitcoin mainnet via OTS
Future:
- Arbitrum (fast, cheap fallback if OTS down)
- Ethereum (slower but high security)
- Solana (faster finality)

Design supports multiple anchors in same checkpoint:
```json
{
  "merkle_root": "...",
  "anchors": {
    "bitcoin": {"tx": "0x789...", "block": 12345},
    "arbitrum": {"tx": "0xabc...", "block": 56789}
  }
}
```

Non-fatal: if Bitcoin fails, try Arbitrum; if both fail, publish unanchored.

---

## Security Considerations

### Threat: OTS Server Compromise

**Attack:** Attacker controls OTS server, issues false proofs.

**Defense:**
- OTS is public infrastructure (monitored by community)
- Bitcoin blockchain is the source of truth
- Auditor can verify OTS proofs against Bitcoin independently
- Multi-testigo consensus: if one testigo gets false OTS proof, others will see different Bitcoin TX → consensus detected fraud

### Threat: Witness Predates Checkpoint

**Attack:** Witness claims checkpoint was created at time T, but Bitcoin timestamp is T' > T.

**Defense:**
- Checkpoint includes snapshot data (votes, timestamps)
- Auditor checks: are vote totals consistent with time T?
- If not → Witness is lying about when checkpoint was created

---

## Deployment Checklist

- [ ] OpenTimestamps client tested (unit + live)
- [ ] Checkpoint pipeline integrates anchor call
- [ ] Forensic logging to attack_log.jsonl
- [ ] Documentation: this file
- [ ] Operator runbook: how to check anchor status
- [ ] Auditor guide: how to verify OTS proofs

---

**Last Updated:** May 2026
