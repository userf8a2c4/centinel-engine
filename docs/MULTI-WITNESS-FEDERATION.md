# Multi-Witness Federation

**ES: Federación de Múltiples Testigos**

Coordina ≥2 testigos independientes para verificar datos de elecciones. Si CNE bloquea/manipula uno, otros detectan divergencia automáticamente.

**EN: Coordinates ≥2 independent witnesses to verify election data. If CNE blocks/manipulates one, others automatically detect divergence.**

---

## Why Multiple Witnesses?

### Single Witness Risk

Una autoridad electoral hostil puede:
- Bloquear al testigo (DDoS, IP blacklist)
- Manipular respuestas HTTP (MITM attack)
- Falsear timestamps en su reloj
- Ignorar cambios de endpoints

### Multiple Witnesses Solution

≥2 testigos independientes:
- Geografía distinta (no mismo ISP/datacenter)
- Operadores diferentes
- Comparan Merkle roots → detectan divergencia automáticamente
- Publican hallazgos públicamente (git mirrors)

**Teorem T4 (Federación):** Si ≥2 de 3 testigos comparten Merkle root, el dato es verificado (Byzant Fault Tolerance 1/3).

---

## Architecture

### Attestation Exchange

Cada testigo publica checkpoint con:
```json
{
  "timestamp": "2026-05-16T19:00:00Z",
  "chain_length": 237,
  "merkle_root": "abc123...def456",
  "endpoint_schema_merkle": "xyz789...",
  "bitcoin_tx": "0x789abc123...",
  "witness_id": "Witness-HN-1",
  "operator_signature": "ed25519_sig_..."
}
```

### Consensus Mechanism

FederationCoordinator:
1. Queries `/api/checkpoint` de todos testigos
2. Extrae `merkle_root` de cada uno
3. Compara pares (allpairs comparison)
4. Determinaconsenso:
   - ≥2 testigos con mismo Merkle → **consensus reached**
   - Todos diferentes → **consensus failed** → escalate to auditors

### Divergence Handling

Si detecta divergencia:
```json
{
  "event_type": "federation_consensus_failed",
  "timestamp": "2026-05-16T19:15:00Z",
  "witnesses": {
    "Witness-HN-1": {"merkle": "abc123...", "snapshots": 237},
    "Witness-HN-2": {"merkle": "def456...", "snapshots": 235},
    "Witness-HN-3": {"merkle": "abc123...", "snapshots": 237}
  },
  "consensus": "FAILED - 2 agree on abc123, 1 on def456",
  "recommendation": "Investigate Witness-HN-2 (differs on 2 snapshots)"
}
```

---

## Integration in Snapshot Pipeline

### Nightly Consensus Check

```python
from centinel.federation.multi_witness import FederationCoordinator

# Configuration: list of sibling witness URLs
SIBLING_WITNESSES = [
    "https://witness-hn-1.example.com",
    "https://witness-hn-2.example.com",
    "https://witness-hn-3.example.com",
]

fed = FederationCoordinator(witness_urls=SIBLING_WITNESSES)

# Every 4 hours during elections:
report = fed.check_consensus()

if not report.consensus_reached:
    logger.error(f"FEDERATION ALERT: {len(report.divergences)} divergence(s) detected")
    # Log to attack_log.jsonl for forensics
    forensic_log.append(fed.to_forensic_record())
else:
    logger.info(f"Consensus OK: {report.consensus_count} witnesses agree")
    # Publish consensus report to mirrors
    fed.publish_consensus(report, "consensus-2026-05-16T19-00-00.json")
```

### Mirror Publication

Each witness publishes checkpoints to shared mirrors:
```bash
hashes/mirrors/
├── checkpoint-2026-05-16T00-00-00.json
├── consensus-2026-05-16T04-00-00.json
├── consensus-2026-05-16T08-00-00.json
├── consensus-2026-05-16T12-00-00.json
└── ...
```

Auditor can clone any mirror and verify locally:
```bash
git clone https://github.com/userfxxx/centinel-mirror.git
cd centinel-mirror
jq .consensus_reached consensus-*.json | sort | uniq -c
```

---

## Scenarios

### Scenario A: CNE Blocks One Testigo

Time: 19:45 UTC (1h 45min into polling)

**Witness-1 (HN-1):**
- 237 snapshots
- Merkle: `abc123...`
- Last snapshot: 19:45 UTC

**Witness-2 (HN-2):**
- 233 snapshots
- Merkle: `def456...` (different)
- Last snapshot: 19:30 UTC (15min behind)
- Error logs: "Connection refused" for last 15 min

**Witness-3 (HN-3):**
- 237 snapshots
- Merkle: `abc123...` (agrees with Witness-1)
- Last snapshot: 19:45 UTC

**Consensus:** Reached (2/3 agree)
**Action:** Investigate Witness-2 connectivity
**Recommendation:** Manual check if CNE blocking selectively

---

### Scenario B: All Three Differ (Rare)

Time: 20:15 UTC

**Witness-1:** Merkle `abc123...` (235 snapshots)
**Witness-2:** Merkle `def456...` (240 snapshots)
**Witness-3:** Merkle `ghi789...` (237 snapshots)

**Consensus:** Failed (all three different)
**Action:** High alert - potential CNE attack
**Escalation:**
1. Freeze all publishing (don't push to mirrors)
2. Contact electoral authority + international observers
3. Preserve all forensic logs
4. Ask: did CNE change endpoint structure?
5. Check OpenTimestamps proofs (should differ if tampering happened)

---

## Auditor Verification

### Online (No Full Node)

```bash
# 1. Query all witnesses
for witness in witness1 witness2 witness3; do
  curl https://$witness/api/checkpoint | jq .merkle_root
done

# 2. Check if ≥2 agree
# ...

# 3. If consensus reached: ✓ data is verified
# 4. If divergence: escalate
```

### Offline (Bitcoin SPV)

```python
# Download checkpoint from mirror
checkpoint = json.load("checkpoint-2026-05-16.json")

# Get OTS proof
ots_proof = checkpoint["ots_proof"]

# Verify OTS proof locally (requires openssl + Bitcoin block headers)
# ...

# Result: 
# - If OTS verifies → timestamp is independent
# - If ≥2 witnesses agree → Merkle is verified
# - Both → ✓ full verification
```

---

## Configuration

### Sibling Witness Registry

```python
# In config/witnesses.yaml or env var:
WITNESSES = [
    {
        "id": "Witness-HN-1",
        "url": "https://witness1.example.com",
        "organization": "NGO-A",
        "location": "Tegucigalpa",
    },
    {
        "id": "Witness-HN-2",
        "url": "https://witness2.example.com",
        "organization": "NGO-B",
        "location": "San Pedro Sula",
    },
    {
        "id": "Witness-HN-3",
        "url": "https://witness3.example.com",
        "organization": "International Observer",
        "location": "Dalanghoa",
    },
]
```

### Consensus Thresholds

```python
CONSENSUS_REQUIRED = 2  # ≥ 2 must agree
MIN_WITNESSES = 3       # Need ≥ 3 total (Byzantine: n ≥ 3f+1 where f=1)
CONSENSUS_INTERVAL = 4 * 3600  # Check every 4 hours
```

---

## Testing

```bash
poetry run pytest tests/test_multi_witness.py -v
```

14 tests cover:
- Attestation creation and comparison
- Consensus with 2, 3 witnesses
- Divergence detection
- Byzantine majority (2/3)
- Forensic logging

---

## Deployment Checklist

- [ ] Identify ≥3 sibling witness organizations
- [ ] Deploy at least 2 independently
- [ ] Configure FederationCoordinator URLs
- [ ] Test consensus check (dry run)
- [ ] Set up automatic consensus checks (cron/scheduler)
- [ ] Document witness operator contact info
- [ ] Publish consensus reports to mirrors (git)
- [ ] Train operators on divergence response
- [ ] Auditor guide: how to verify consensus

---

## Future: Gossip Protocol

Current: Centralized coordinator queries all
Future: Gossip (epidemic protocol)
- Each witness pushes attestation to others
- Eventually consistent (auto-propagates)
- Resilient to single witness failure
- Lower bandwidth

---

**Last Updated:** May 2026
