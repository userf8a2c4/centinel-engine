# Web Verification Tools

**ES: Herramientas de Verificación Web**

This directory contains client-side web tools for verifying Centinel witness data.

**ES: Este directorio contiene herramientas web del lado del cliente para verificar datos de testigos Centinel.**

---

## Purpose

The web tools provide **zero-server verification**:
- No backend required
- No authentication needed
- Fully auditable JavaScript (browser crypto)
- Can be deployed as static files (GitHub Pages, CDN, etc.)
- Can be run locally from the filesystem

**ES: Las herramientas web proporcionan verificación sin servidor:**
- **Sin backend requerido**
- **Sin autenticación necesaria**
- **JavaScript completamente auditable (cripto del navegador)**
- **Puede desplegarse como archivos estáticos (GitHub Pages, CDN, etc.)**
- **Puede ejecutarse localmente desde el sistema de archivos**

---

## Tools

### Public Verifier (`verifier/`)

**Purpose:** Read-only verification of witness snapshot data.

**How it works:**
1. User provides witness URL (e.g., `https://witness.example.com`)
2. Verifier downloads snapshots and transparency checkpoint
3. Browser computes Merkle root locally using embedded crypto
4. Compares local Merkle root to server-reported root
5. If they match → integrity verified (Theorem T3)
6. If they differ → rewrite detected

**Key features:**
- Zero trust (server could be lying; we verify locally)
- Bilingual interface (ES/EN)
- Live demo mode (embedded synthetic data, no server needed)
- CSV/JSON export of data
- Cross-mirror verification (consensusjson required)

**Deployment:**
```bash
# Static deployment (GitHub Pages, S3, etc.)
cp verifier/index.html /path/to/webroot/
# Users visit: https://example.com/verifier.html
```

**Usage:**
1. Open in browser
2. Enter witness URL or select "Demo"
3. Watch panels fill in real-time
4. Check ✓/✗ on each verification stage

### Validator Sandbox (`sandbox/`)

**Purpose:** Isolated testing environment for electoral auditors.

**Two modes:**

#### Mode 1: Attack the Core (T1/T3)
- Load real or demo snapshot data
- Edit snapshots (change hash, vote totals, timestamps)
- Watch chain-link break (T1 violation)
- See Merkle rewrite detected (T3 violation)
- Learn the guarantees hands-on

#### Mode 2: Tune Anomaly Rules
- Pre-register hypothesis (Benford threshold, Z-score limit)
- Generate synthetic data (clean vs. tampered)
- Run live rule evaluation
- Export report with validator attribution

**Key features:**
- Local account (browser localStorage, non-repudiable authorship)
- Attack/tune modes independent
- Zero backend mutation (all sandboxed)
- Report export (JSON, signatureless but timestamped)

**Deployment:**
```bash
cp sandbox/index.html /path/to/webroot/
```

**Usage:**
1. Open in browser
2. Create account (validator name + affiliation)
3. Choose Mode 1 or Mode 2
4. Run tests, export report

---

## Testing Web Tools

### Crypto Equivalence

Web verifier uses JavaScript crypto. Tests verify it matches Python:

```bash
poetry run pytest tests/test_web_verifier_crypto.py -v
```

Tests cover:
- SHA-256 (against hashlib)
- Merkle root computation (tree-building logic)
- Demo chain verification
- Merkle determinism (same input = same output)

### Manual Testing

Open in browser:
```
file:///path/to/centinel-engine/web/verifier/index.html
```

Click "▶ Demo" to load synthetic 24-element chain. Merkle root computes locally.

---

## Deployment Checklist

### Static Site (GitHub Pages, Vercel, etc.)

- [ ] Copy `verifier/index.html` to `docs/verifier/`
- [ ] Copy `sandbox/index.html` to `docs/sandbox/`
- [ ] Test locally (file:// protocol)
- [ ] Push to GitHub
- [ ] Enable GitHub Pages in settings
- [ ] Pages auto-deploys from `/docs` folder

### Custom Domain

- [ ] Point DNS CNAME to GitHub Pages / Vercel
- [ ] Ensure HTTP → HTTPS redirect
- [ ] Test CORS headers (witness must allow your domain)
- [ ] Monitor console for CORS errors

### Self-Hosted (nginx/Apache)

```nginx
server {
    listen 443 ssl;
    root /var/www/centinel;

    location /verifier {
        try_files $uri /verifier/index.html;
    }

    location /sandbox {
        try_files $uri /sandbox/index.html;
    }

    # Witness API (same origin)
    location /api {
        proxy_pass http://localhost:8000;
    }
}
```

---

## Security Considerations

### CORS

Verifier makes cross-origin requests to witness. Witness must have:
```
Access-Control-Allow-Origin: https://your-verifier-domain.com
```

(Not wildcard `*` — specific domain only)

### Crypto

- SHA-256: WebCrypto API (all modern browsers)
- Random number generation: Not required (deterministic)
- Signing: Optional (demo is unsigned)

### No Auth Required

Web tools are read-only. No credentials transmitted. Safe to run from untrusted CDN.

---

## Integration with Core

Web verifier and sandbox are **independent of the Python core**. They:
- Download JSON snapshots via HTTP
- Compute Merkle root locally
- Never trust the server

This separation is intentional:
- Core Python is operator tool (capturing + storing data)
- Web tools are auditor tool (verifying data trustlessly)

---

## Extensibility

Want to add a new verification panel to the verifier?

1. Add HTML section in `<body>`
2. Add JavaScript function `verify<PanelName>()`
3. Call from `verifyOne()`
4. Update test in `tests/test_web_verifier_crypto.py`

Example:
```javascript
function verifyAnomaly(baseURL) {
    const res = await fetch(`${baseURL}/audit/anomalies`);
    const data = await res.json();
    updatePanel('anomaly', data.count ? 'error' : 'ok');
}
```

---

## Support

Questions?
- Check `docs/` for architecture
- Read code comments in HTML
- Run tests: `poetry run pytest tests/test_web_verifier_crypto.py -v`
- Open GitHub issue

---

**Deployed:** https://userf8a2c4.github.io/centinel-engine/  
**Source:** This repo (`web/` directory)  
**License:** AGPL-3.0
