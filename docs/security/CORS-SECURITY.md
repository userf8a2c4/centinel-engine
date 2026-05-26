# CORS Security Configuration

**ES: Configuración de Seguridad CORS**

## Overview

Cross-Origin Resource Sharing (CORS) controls which domains can make HTTP requests to your Centinel witness server. This document explains the risk model and configuration.

**ES: CORS controla qué dominios pueden hacer requests HTTP a tu servidor testigo Centinel. Este documento explica el modelo de riesgo y configuración.**

---

## The Attack: Verifier Hijacking

If your witness has `CORS_ORIGINS=*` (wildcard), an attacker can:

1. Publish a malicious web verifier on their own domain (e.g., `evil.com/verifier.html`)
2. The verifier in the browser makes CORS requests to your witness (e.g., `centinel-witness.example.com/audit/timeline`)
3. Because CORS allows `*`, the browser permits it
4. Your witness data is now being queried by an attacker-controlled verifier

The attacker can:
- Cache or archive your data
- Inject fake anomalies or alerts
- Confuse auditors about the source of verification

**Solution:** Whitelist only the domains you trust.

---

## Configuration

### Priority

Centinel reads CORS origins in this priority order:

1. **Environment variable `CORS_ORIGINS`** (runtime override)
   ```bash
   CORS_ORIGINS=https://example.com,http://localhost:3000
   ```
2. **Config file** (`command_center/advanced_security_config.yaml`)
   ```yaml
   cors_allowed_origins:
     - "https://userf8a2c4.github.io/centinel-engine"
     - "http://localhost:3000"
   ```
3. **Default: Empty list** (CORS disabled — no cross-origin requests allowed)

### Recommended Configuration

For the public GitHub Pages verifier + local development:

```yaml
cors_allowed_origins:
  - "https://userf8a2c4.github.io/centinel-engine"
  - "http://localhost:3000"
```

**For production:** Replace with your deployment domain and remove localhost.

---

## What Happens

### When CORS is disabled (empty list)

- Browser blocks cross-origin requests
- Web verifier **must** be served from the same origin as your witness API
  (e.g., both at `https://witness.example.com/`)
- Or use a proxy that sets `Access-Control-Allow-Origin` header

### When CORS is enabled (explicit whitelist)

- Browser permits cross-origin requests from whitelisted domains
- Web verifier can be served from GitHub Pages, CDN, or separate domain
- Auditors can verify your witness from multiple verifier implementations

---

## Examples

### ✅ Secure: Explicit whitelist

```yaml
cors_allowed_origins:
  - "https://userf8a2c4.github.io/centinel-engine"
  - "https://auditor-org.org/verifier"
```

Browser behavior:
- ✓ Request from `https://userf8a2c4.github.io/...` → **allowed**
- ✓ Request from `https://auditor-org.org/...` → **allowed**
- ✗ Request from `https://evil.com/verifier` → **blocked**

### ❌ Insecure: Wildcard (DEPRECATED)

```yaml
cors_allowed_origins:
  - "*"
```

**Do not use this.** Any domain can query your witness.

### ❌ Insecure: Missing config

If you do not set `CORS_ORIGINS` or config, CORS is **disabled** (empty list).
- Web verifier running on GitHub Pages cannot reach your witness
- You must use a same-origin proxy or deploy verifier on same server

---

## For Witness Operators

**When setting up a witness:**

1. Decide which verifier implementations should be able to query your witness
   - Public GitHub Pages verifier (required): `https://userf8a2c4.github.io/centinel-engine`
   - Academic auditors: `https://university-auditor.org/verify`
   - Your own auditor tools: `http://localhost:3000` (dev only)

2. Add them to `cors_allowed_origins` in config

3. Test:
   ```bash
   # Open web verifier in browser, check Network tab
   # Look for requests to your witness
   # Status 200 = CORS allowed
   # Status 0 (blocked) = CORS issue
   ```

---

## For Verifier Implementers

If you're building a new verifier and want to query a witness:

1. Ensure the witness has your domain in `cors_allowed_origins`
2. Contact the witness operator if not
3. Do not assume `CORS_ORIGINS=*` — it may be removed at any time for security

---

## Related

- [OWASP: Cross-Origin Resource Sharing (CORS)](https://owasp.org/www-community/Cross-Origin_Resource_Sharing_(CORS))
- Mozilla MDN: [CORS](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS)
- Centinel API: `src/centinel/api/main.py` (function `_load_cors_origins`)
