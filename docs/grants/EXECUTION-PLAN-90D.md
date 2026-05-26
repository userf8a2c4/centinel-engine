# 90-Day Execution Plan (Credibility + Precision + Immutability)

## Track 1 — Public verifiability
- [ ] Publish `evidence_bundle.json` per run.
- [ ] Add one-command verifier for third parties.
- [ ] Attach pipeline version + ruleset hash to each bundle.

## Track 2 — Cryptographic hardening
- [ ] Keep SHA-256 per artifact and Merkle root per batch.
- [ ] Add optional signing of bundles (external key management).
- [ ] Define anchor cadence for critical windows.

## Track 3 — Rule governance (core vs research)
- [ ] Maintain `rules_core.yaml` as stable production baseline.
- [ ] Maintain `rules_research.yaml` as academic sandbox.
- [ ] Promote rules only with reproducible evidence + documented review.

## Track 4 — Demonstrable resilience
- [ ] Run resilience suite in CI with visible reports.
- [ ] Publish recovery evidence and retry discipline metrics.
- [ ] Track controlled degradation (`normal/conservative/critical`).

## Track 5 — Supply-chain governance
- [ ] Enforce release checklist before tagging.
- [ ] Keep lockfile and SBOM integrity checks green.
- [ ] Record provenance metadata for each release.

## Track 6 — Precision metrics
- [ ] Track rule precision/recall estimates on labeled historical windows.
- [ ] Publish false-positive and false-negative notes per rule.
- [ ] Keep thresholds configurable and versioned.

## Track 7 — Security enforcement
- [ ] Enforce strict JSON validation in the pipeline.
- [ ] Enforce secure log redaction defaults.
- [ ] Audit secrets handling and key rotation schedule.
