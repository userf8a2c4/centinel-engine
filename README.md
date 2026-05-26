<p align="center">
  <img src="web/assets/logo.svg" alt="CENTINEL — Trustless Electoral Integrity" width="700">
</p>

# CENTINEL
### Trustless Electoral Integrity Verification — Latin America
*Verificación Confiable de Integridad Electoral — América Latina*

---

[![CI](https://github.com/vectisdev/centinel/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/vectisdev/centinel/actions/workflows/ci.yml)
[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-2b6cb0.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-2b6cb0.svg)](pyproject.toml)
[![Tests](https://img.shields.io/badge/tests-526%20passing-2f855a.svg)](#validation-status)
[![Security](https://img.shields.io/badge/security-audited-2f855a.svg)](docs/security/SECURITY-REVIEW.md)
[![Zero Cost](https://img.shields.io/badge/deployment-zero%20cost-2f855a.svg)](#design-principles)
[![LATAM](https://img.shields.io/badge/countries-HN%20%7C%20GT%20%7C%20SV%20%7C%20NI%20%7C%20MX%20%7C%20CO-orange.svg)](#supported-countries)

---

> Electoral authorities publish results that citizens must accept on trust.  
> **CENTINEL eliminates that required trust** — permanently, cryptographically, at zero cost.

A single operator can audit a national election from a laptop.  
Every capture is chained, signed, and anchored to Bitcoin's blockchain.  
Any third party can verify — offline, independently, without your cooperation.

> *Auditoría electoral independiente y reproducible, sin dependencia institucional, sin infraestructura dedicada y sin coste operativo. Un solo operador puede auditar una elección nacional desde un portátil.*

<!-- INSTANCE-STATUS-START -->

---

## Deploy in 3 steps — nothing to install

[![Step 1 — Fork this repo](https://img.shields.io/badge/STEP%201%20→%20Fork%20this%20repository-2b6cb0?style=for-the-badge&logo=github&logoColor=white)](https://github.com/vectisdev/centinel/fork)

> Click above. GitHub creates **your own independent, private copy** of the tool in your account.

---

**Step 2 — Enable Actions** *(in your fork, once)*

Go to the **[Actions](../../actions)** tab of **your fork** and click:
> **"I understand my workflows, go ahead and enable them"**

---

**Step 3 — Run the Setup Wizard**

[![Run Setup Wizard](https://img.shields.io/badge/Run%20Setup%20Wizard%20→-2f855a?style=for-the-badge&logo=github-actions&logoColor=white)](../../actions/workflows/setup-wizard.yml)

> In your fork: **Actions → Setup Wizard → "Run workflow"** → select your country → **"Run workflow"**

The wizard auto-configures everything: data repository, electoral authority endpoints, cryptographic seeds, and the visualization dashboard. Follow the Issue it opens for any remaining manual step.

**What you get after setup:**  
→ Captures every 30 min · Cryptographic hash chain · Bitcoin-anchored proof · Public verification dashboard · P2P swarm-ready

<details>
<summary>Panel not showing after setup?</summary>

→ **[Settings → Pages](../../settings/pages)** → Source: **GitHub Actions** → Save

It will be available on the next push to `main`.
</details>

<!-- INSTANCE-STATUS-END -->

---

## Why CENTINEL?

| | Traditional NGO Observer | CENTINEL |
|--|--------------------------|----------|
| **Cost** | $10K – $500K per election | **Zero** — GitHub Actions free tier |
| **Independence** | Requires access, funding, accreditation | **Complete** — no permission needed |
| **Verifiability** | Reports and statements | **Cryptographic proof** — anyone can verify offline |
| **Scale** | Team of observers, weeks of planning | **1 operator, 1 laptop, 3-step setup** |
| **Real-time** | Post-election reports | **Continuous capture during the event** |
| **Censorship resistance** | Single organization = single point to pressure | **P2P swarm — no center to seize or bribe** |
| **Temporal proof** | None | **Bitcoin-anchored** via OpenTimestamps |
| **Replicability** | Closed methodology | **Every step reproducible by any third party** |

---

## Supported Countries

| Country | Code | Electoral Authority | Status |
|---------|------|---------------------|--------|
| 🇭🇳 Honduras | `HN` | Consejo Nacional Electoral (CNE) | ✅ Production-ready — piloted on 2025 general election |
| 🇬🇹 Guatemala | `GT` | Tribunal Supremo Electoral (TSE) | 🔧 Configured — awaiting field test |
| 🇸🇻 El Salvador | `SV` | Tribunal Supremo Electoral (TSE) | 🔧 Configured — awaiting field test |
| 🇳🇮 Nicaragua | `NI` | Consejo Supremo Electoral (CSE) | 🔧 Configured — awaiting field test |
| 🇲🇽 Mexico | `MX` | Instituto Nacional Electoral (INE) | 🔧 Configured — awaiting field test |
| 🇨🇴 Colombia | `CO` | Registraduría Nacional | 🔧 Configured — awaiting field test |

Adding a new country requires only a preset in [`src/centinel/countries.py`](src/centinel/countries.py).

---

## What it solves

Electoral authorities publish results that citizens must accept on trust. CENTINEL eliminates that required trust: it captures published data, chains it cryptographically, and allows any third party to verify — reproducibly and offline — that data was not altered after publication.

| Property | Guarantee |
|----------|-----------|
| **Reproducibility** | SHA-256 chain + Merkle root, verifiable offline by anyone |
| **Independence** | Operator needs no permission or cooperation from the authority |
| **Resilience** | P2P federation — no single point of failure or capture |
| **Temporal immutability** | Bitcoin anchoring via OpenTimestamps — zero cost |
| **Neutrality** | Reports verifiable facts only — no political interpretation |
| **Ethical scraping** | Token-bucket rate limiting + jitter + gossip-first swarm design — the full swarm behaves as at most one visitor to the audited site |

> **Anti-DDoS by design:** If a node receives a cryptographically-signed snapshot from a peer, it skips the scrape entirely. The entire witness swarm never exceeds the footprint of a single polite visitor — your infrastructure cannot cause harm to the audited site.

---

## Design principles

Three decisions are non-negotiable — they determine whether the tool remains useful under pressure:

- **Zero cost.** Anyone — student, journalist, civil society organization — can operate it without budget or authorization.
- **Resilience.** No central point to seize, block, or bribe.
- **Survival.** The protocol persists and replicates even if its author disappears; the license and documentation guarantee it.

---

## Swarm / Federation

Each fork is a fully independent node. Nodes can optionally join a **witness swarm** — sharing cryptographically signed snapshots over a gossip protocol without any central coordinator:

- **Join**: Fork → enable Actions → run wizard → the wizard auto-discovers existing peers
- **Leave**: disable master switch → node gracefully exits; peers discard it after timeout
- **Anti-DDoS**: gossip-first design means if a node receives a valid signed snapshot from a peer, it does not scrape the source again. The entire swarm never exceeds the footprint of a single polite visitor.
- **OpenTimestamps**: any node can anchor to Bitcoin's blockchain for free. Multiple nodes submitting the same hash get the same proof — no coordination needed.

---

## Operation

```bash
poetry install

make wizard                  # Guided interactive setup (recommended)
centinel panel show          # System status
centinel snapshot            # One-shot capture and verification
centinel cron --interval 30s # Continuous automated capture
```

---

## Defense architecture

CENTINEL applies defense in depth: each layer mitigates a distinct class of threat.

| Layer | Function | Threat mitigated |
|-------|----------|-----------------|
| Distributed attestation | Cross-confirmation between witnesses | Single witness compromised |
| Transit encryption | ChaCha20-Poly1305 | Interception / MITM |
| Non-deterministic timing | Capture jitter | Predictive selective blocking |
| Auto-regeneration | Resync from replicas | Local state manipulation |
| Kill switch | Freeze on active attack | Real-time compromise |

→ [Defense specification](docs/architecture/ANIMAL-DEFENSES-ES.md) · [Architecture and theorems T1–T4](docs/architecture/ARCHITECTURE.md)

---

## Cryptographic stack

| Primitive | Use |
|-----------|-----|
| SHA-256 chained hash | Snapshot integrity chain |
| Ed25519 (EdDSA) | Witness signatures, operator keypairs |
| Fernet (AES-128-CBC + HMAC-SHA256) | Encrypted backups and checkpoints |
| HKDF-SHA256 | Checkpoint key derivation |
| PBKDF2-SHA256 (600k iterations) | Admin seed hashing |
| OpenTimestamps / Bitcoin | External temporal immutability anchor |
| Merkle tree (SHA-256) | Batch snapshot anchoring |

---

## Validation status

| Axis | Status |
|------|--------|
| Cryptographic audit (theorems T1–T4) | Complete — verifiable in code |
| Test suite | 526 / 526 passing |
| Independent academic validation | In progress (UPNFM, Honduras) |
| Field pilot | Completed — Honduras 2025 general election data |
| False positive analysis | 500-run validation — [results published](docs/research/FALSE_POSITIVE_ANALYSIS.md) |

Version **0.1 — pre-pilot.** Cryptographic core stable; pending formal independent academic review (UPNFM, Universidad Pedagógica Nacional Francisco Morazán).

---

## Data architecture

CENTINEL separates code (this repository) from captured electoral data (`centinel-data`). Data is published automatically to an independent repository on each capture — any auditor can verify it without running the engine.

**Data repository:** <!-- CENTINEL_DATA_URL -->*(auto-configured when you fork)*<!-- /CENTINEL_DATA_URL -->

**Visualization panel:** <!-- CENTINEL_PAGES_URL -->*(auto-activated when you fork)*<!-- /CENTINEL_PAGES_URL -->

→ [Code/data separation architecture](docs/operations/DATA-REPOS.md) · [Setup guide](docs/operations/SETUP-GUIDE.md) · [Visualization panel](docs/operations/PAGES-GUIDE.md)

---

## Documentation

| Document | Audience |
|----------|----------|
| [QUICKSTART.md](docs/guides/QUICKSTART.md) | Operators — getting started |
| [ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md) | Technical reviewers — design and theorems |
| [SECURITY-REVIEW.md](docs/security/SECURITY-REVIEW.md) | Security auditors — threat model |
| [METHODOLOGY.md](docs/research/METHODOLOGY.md) | Academics — methodological foundation |
| [OPERATOR-RUNBOOKS.md](docs/operations/OPERATOR-RUNBOOKS.md) | Operators — step-by-step procedures |
| [LEGAL-AND-OPERATIONAL-BOUNDARIES.md](docs/legal/LEGAL-AND-OPERATIONAL-BOUNDARIES.md) | Legal framework and operational limits |
| [docs/](docs/) | Full documentation index |

---

## For grant reviewers and bounty programs

CENTINEL is designed for zero operating cost, maximum verifiability, and AGPL-3.0 licensing that prevents capture or privatization.

**Relevant materials:**
- [Theory of Change](docs/architecture/THEORY_OF_CHANGE.md) — impact logic model
- [Methodology](docs/research/METHODOLOGY.md) — 25+ statistical detectors, academic foundation
- [Budget Narrative](docs/grants/BUDGET_NARRATIVE.md) — grant budget breakdown
- [Institutional Readiness](docs/grants/INSTITUTIONAL_READINESS.md) — readiness for multilateral observer engagement
- [Roadmap](docs/grants/ROADMAP.md) — feature and deployment roadmap
- [False Positive Analysis](docs/research/FALSE_POSITIVE_ANALYSIS.md) — 500-run validation

**Suitable for:** Gitcoin · Open Society Foundations · NDI / IRI · OAS · NSF · Immunefi security bounties

→ [Full grants documentation](docs/grants/)

---

## License

**GNU AGPL-3.0.** Free, auditable, and redistribution-guaranteed software: any derivative must remain open. This license is deliberate — it ensures CENTINEL cannot be captured, closed, or privatized by any actor, public or private.

---

**CENTINEL** · Electoral auditing as a citizen right, not an institutional privilege · `vectisdev`

<!-- FORK-GUIDE-START -->
---

## Want your own instance? / ¿Quieres tu propia instancia?

Fork → enable Actions → run Setup Wizard → done. Your instance includes a public data repository (`centinel-data`), a GitHub Pages visualization dashboard, and continuous verifiable capture — no servers, no operating cost.

Full details: [docs/operations/SETUP-GUIDE.md](docs/operations/SETUP-GUIDE.md)
<!-- FORK-GUIDE-END -->
