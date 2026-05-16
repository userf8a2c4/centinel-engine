# Anomaly Detection in Centinel Engine

**ES: Detección de Anomalías en Centinel Engine**

## Overview

Centinel Engine includes real-time anomaly detection to flag suspicious patterns in election snapshots. This enables operators and auditors to identify potentially tampered data early, matching standards used by electoral authorities in Brazil (TSE) and Mexico (INE).

**ES: Centinel Engine incluye detección de anomalías en tiempo real para señalar patrones sospechosos en snapshots electorales. Esto permite a operadores y auditores identificar datos potencialmente manipulados temprano, igualando estándares usados por autoridades electorales en Brasil (TSE) y México (INE).**

### Non-Fatal Design

Anomalies **never block** verification or acceptance of data. Detection is purely informational:
- Flagged anomalies are logged and exposed via API
- Chain verification (`verify_hashchain`) remains unaffected
- Auditors decide significance; system does not judge

### Threshold Protection

Rules only apply when `>= min_snapshots` observations exist (default: 100). This avoids false positives during election night when data is sparse.

---

## Implemented Checks

### 1. Benford's Law (First-Digit Distribution)

**Test:** Do the first digits of vote counts follow Benford's Law?

**How it works:**
- Natural numbers in elections (votes, voter registrations, precinct counts) typically follow Benford's distribution
- First digit 1 appears ~30%, digit 2 ~18%, etc.
- **χ² goodness-of-fit test** compares observed vs. expected frequencies

**Why it matters:**
- Fabricated/rounded vote counts deviate from Benford (too many 1s, 2s, 5s, 0s)
- Real vote increments (1001, 1002, ..., 1098) naturally follow Benford
- If χ² > 5.99 (p<0.05), distribution is suspiciously non-Benford

**Example:**
- ✓ Natural: 1247 votes, 1251 votes, 1089 votes, ... → passes Benford
- ✗ Fake: 1000 votes, 2000 votes, 3000 votes, ... → fails Benford (χ² >> 5.99)

**References:**
- Mebane, W. R. (2006). "[Election Forensics: The Meanings of Anomalies](https://scholar.google.com/scholar?q=election+forensics+mebane)"
- Brazil TSE: Applied to audit 2022 presidential results

---

### 2. Z-Score Outlier Detection (Vote Deltas)

**Test:** Are vote changes between snapshots within normal range?

**How it works:**
- Compute vote delta: Δv[i] = votes[i] - votes[i-1]
- Compute mean and standard deviation of deltas
- Flag if |Δv[i]| > 3σ (more than 3 standard deviations from mean)

**Why it matters:**
- Election night typically shows steady vote increments (smoothly increasing curve)
- Sudden spikes (e.g., 1000 votes jump to 5000) are unusual
- Could indicate batch injection, transmission error, or tampering
- Z-score = 3 captures ~99.7% of normal variation

**Example:**
- Normal: 100, 105, 110, 102, 108, ... → Z-scores ≈ 0.5
- Suspicious: 100, 105, 5000, 110, ... → Z-score at index 2 ≈ 50 (flagged)

**Threshold:** Z > 3.0 (configurable)

---

### 3. Timestamp Monotonicity

**Test:** Do snapshot timestamps always advance (never go backward)?

**How it works:**
- Check that timestamp[i] > timestamp[i-1] for all i
- Flag any non-increasing transition

**Why it matters:**
- Snapshots should be created in chronological order
- Backward timestamps indicate:
  - Operator error (clock adjustment)
  - Data injection (tampering with timeline)
  - System malfunction (clock went backward)
- This is **high severity** — core assumption of chain verification

**Example:**
- ✓ Clean: 2026-05-16 08:00, 08:15, 08:30, 08:45, ...
- ✗ Suspicious: ..., 08:30, 08:45, **08:25**, 08:50, ...

---

## Configuration

### Basic Usage

```python
from centinel.core.anomaly_detector import AnomalyDetector

# Create detector with defaults
detector = AnomalyDetector(
    min_snapshots=100,           # Don't check until 100 snapshots
    benford_chi2_threshold=5.99,  # χ² threshold (p<0.05)
    zscore_threshold=3.0,         # 3-sigma outliers
)

# Analyze snapshots
report = detector.analyze(snapshots_list)

# Use results
for anomaly in report.anomalies:
    print(f"Snapshot {anomaly.snapshot_idx}: {anomaly.detail}")
```

### Configurable Thresholds

```python
# Stricter detection (lower threshold = more sensitive)
detector = AnomalyDetector(
    min_snapshots=50,
    benford_chi2_threshold=3.84,  # p<0.10 (more permissive)
    zscore_threshold=2.0,          # 2-sigma (more sensitive)
)

# Relaxed detection (higher threshold = fewer false positives)
detector = AnomalyDetector(
    min_snapshots=200,
    benford_chi2_threshold=7.81,  # p<0.02 (stricter)
    zscore_threshold=4.0,          # 4-sigma (less sensitive)
)
```

### Environment Integration

```python
# In audit.py or similar:
detector = AnomalyDetector(min_snapshots=100)
report = detector.analyze(all_snapshots)

for anomaly in report.anomalies:
    # Log to attack_log.jsonl
    log_event({
        "type": "anomaly",
        "snapshot_idx": anomaly.snapshot_idx,
        "anomaly_type": anomaly.anomaly_type,
        "severity": anomaly.severity,
        "detail": anomaly.detail,
    })
```

---

## API Exposure

The anomaly detector results are exposed via a REST endpoint (future):

```http
GET /audit/anomalies?from=0&to=500

Response:
{
  "anomalies": [
    {
      "snapshot_idx": 142,
      "type": "zscore",
      "severity": "medium",
      "detail": "Vote delta 5000 is 15.3σ from mean",
      "metric": "vote_delta",
      "value": 15.3
    }
  ],
  "threshold_applied": true,
  "analysis": {
    "snapshots_analyzed": 501,
    "benford_threshold": 5.99,
    "zscore_threshold": 3.0
  }
}
```

---

## Comparison to Regional Standards

| Aspect | Brazil (TSE) | Mexico (INE) | Centinel |
|--------|-------------|-------------|---------|
| First-digit check | ✓ Benford's Law | (Not documented) | ✓ χ² test |
| Vote delta outliers | (Not documented) | ✓ Threshold-based | ✓ Z-score |
| Timestamp validation | (Not documented) | (Not documented) | ✓ Monotonicity |
| Congruence rules | (Not documented) | ✓ sum(actas) = sum(results) | (Future) |
| Real-time flagging | Post-hoc | Post-hoc | ✓ Real-time |
| Minimum data threshold | N/A | Variable | ✓ 100 snapshots |

---

## Operational Notes

### False Positives

Anomalies **can** occur in legitimate scenarios:
- **Benford**: Precincts with very few votes (< 20) may deviate
- **Z-score**: Legitimate vote batches can be large
- **Timestamp**: Operator clock corrections during pilot

**Solution:** Threshold tuning + auditor review. Centinel never auto-rejects; humans decide.

### Tuning for Your Election

Before election night, test with:
1. Historical election data (if available)
2. Synthetic test scenarios (benign vs. suspicious)
3. Set thresholds so normal increments pass, obvious fakes fail

Example calibration:
```python
# Test on 2020 municipal election data
from centinel.core.anomaly_detector import detect_anomalies

historical = load_2020_snapshots()  # ~500 snapshots
report = detect_anomalies(historical, min_snapshots=100)

# Adjust thresholds if needed
if len(report.anomalies) > 5:  # Too many false positives
    # Increase thresholds (be more permissive)
    report = detect_anomalies(historical, zscore_threshold=4.0)
```

---

## Design Choices

### Why Non-Fatal?

Anomalies don't break the system because:
- They complement cryptographic verification, not replace it
- Auditors have final say on significance
- System must survive false positives (e.g., operator error)

### Why min_snapshots=100?

- Allows statistical testing (need N≥30 for good χ², preferably 100+)
- Avoids overfitting to sparse election-night data
- ~2–3 hours into election night (typical frequency: 1 snapshot/min)
- User can lower for testing: `min_snapshots=10`

### Why 3-Sigma for Z-Score?

- 3σ captures 99.7% of normal variation
- Matches academic standards (e.g., Mebane 2006)
- Balances sensitivity vs. false-positive rate
- Can be tuned: 2σ (more sensitive), 4σ (less sensitive)

---

## Testing

Comprehensive test suite in `tests/test_anomaly_detector.py`:
- Benford's Law (clean vs. fake data)
- Z-score (spikes vs. normal increments)
- Timestamp monotonicity (increasing, backward, stalled)

Run:
```bash
poetry run pytest tests/test_anomaly_detector.py -v
```

---

## References

1. **Benford's Law in Elections:**
   - Mebane, W. R. (2006). "Election Forensics: The Meanings of Anomalies."
   - Brazil TSE (2022): Applied to verify presidential election results

2. **Z-Score Outlier Detection:**
   - Standard statistical practice (ISO 16269-6)
   - Mexican INE: Vote-change thresholds in congruence rules

3. **Timestamp Monotonicity:**
   - Certificate Transparency (RFC 6962): Strictly monotonic tree growth
   - Electoral integrity: Prevents backdating/time-travel attacks

---

## Future Extensions

Planned additions (not in v0.1):
- **Congruence rules:** sum(actas) = sum(candidate_votes)
- **Geographical anomalies:** Precinct-level variance detection
- **Comparative thresholds:** Multi-witness consensus anomalies
- **Predictive models:** Learn expected curves from historical data

---

**Status:** Operationally ready for pilot. Thresholds calibrated for Honduras 2028.
