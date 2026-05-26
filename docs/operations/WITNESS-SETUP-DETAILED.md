# Witness Setup — Detailed Step-by-Step Guide

**ES: Configuración de Testigo — Guía Paso a Paso Detallada**

Instructions for a new organization becoming a Centinel witness operator.

**ES: Instrucciones para que una nueva organización se convierta en operador de testigo Centinel.**

---

## Pre-Requisites

- **Server:** Linux (Ubuntu 20.04+, Debian, RHEL)
  - 2+ CPU cores
  - 8 GB RAM
  - 50+ GB disk (grows ~1–2 GB per election night)
  - Stable network connection (2 Mbps+ upload/download)
  
- **Software:** Python 3.10+, Git, Docker (optional)

- **Network:** Public IP or fixed DNS, port 443 (HTTPS) open to internet

- **Authorization:** Electoral authority approval to act as witness

---

## Step 1: Clone Repository

```bash
cd /opt
git clone https://github.com/userf8a2c4/centinel-engine.git
cd centinel-engine
```

**Verify:**
```bash
ls -la
# Should show: docs/, src/, tests/, pyproject.toml, etc.
```

---

## Step 2: Install Dependencies

```bash
# Install Poetry
pip install poetry

# Install project dependencies
poetry install

# Activate virtual environment
poetry shell
```

**Verify:**
```bash
poetry run python -c "import centinel; print('Centinel core OK')"
```

---

## Step 3: Create Directories & Config

```bash
# Create data directories
mkdir -p hashes/{snapshots,transparency,mirrors}
mkdir -p logs
mkdir -p data

# Copy example config
cp command_center/advanced_security_config.yaml.example \
   command_center/advanced_security_config.yaml

# Edit config
nano command_center/advanced_security_config.yaml
```

**Key settings to update:**
```yaml
enabled: true
honeypot_enabled: false  # Set to false unless you want honeypot
cors_allowed_origins:
  - "https://verifier-domain.example.com"  # Your verifier
  - "http://localhost:3000"                 # Dev only
prometheus_enabled: true                    # For monitoring
```

---

## Step 4: Generate Operator Key (Optional)

If you want to sign snapshots with operator identity:

```bash
# Generate Ed25519 key pair
poetry run python -c "
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

private_key = ed25519.Ed25519PrivateKey.generate()
public_key = private_key.public_key()

# Save private key (KEEP SECURE)
pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
)
with open('hashes/operator_private.pem', 'wb') as f:
    f.write(pem)

# Save public key (share with auditors)
pub_pem = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
)
with open('hashes/operator_public.pem', 'wb') as f:
    f.write(pub_pem)

print('Keys generated.')
"

chmod 600 hashes/operator_private.pem
chmod 644 hashes/operator_public.pem
```

---

## Step 5: Initialize Mirror Repository

Your witness will push checkpoints to a git repository (for redundancy):

```bash
# Create local mirror repo
cd hashes/mirrors
git init --initial-branch=main
git config user.name "Witness Operator"
git config user.email "witness@example.com"

# Create README
cat > README.md << 'EOF'
# Centinel Mirror — [Your Organization]

Checkpoint mirror for Centinel witness operated by [Your Organization].

Checkpoints updated weekly (or more frequently during elections).

Public Merkle root verification:
```bash
jq .merkle_root checkpoint-*.json | tail -1
```
EOF

git add README.md
git commit -m "Initial mirror repository"

# Add remote (GitHub, GitLab, etc.)
git remote add origin https://github.com/your-org/centinel-mirror.git
git push -u origin main

cd ../..  # Back to centinel-engine root
```

---

## Step 6: Configure Automated Snapshots

Create a cron job to run `centinel snapshot` every 5 minutes:

```bash
# Edit crontab
crontab -e

# Add line:
*/5 * * * * cd /opt/centinel-engine && poetry run centinel snapshot >> logs/cron.log 2>&1
```

**Verify cron is running:**
```bash
# Check recent cron output
tail -20 /opt/centinel-engine/logs/cron.log

# Should see snapshot creation messages
```

---

## Step 7: Set Up Backups

Backups protect against disk failure:

```bash
# Edit backup config
nano command_center/advanced_security_config.yaml

# Set backup provider (S3, B2, etc.)
backup_provider: "s3"  # or "b2"
backup_interval: 3600  # Every hour (in seconds)
auto_backup_forensic_logs: true

# Configure credentials
export AWS_ACCESS_KEY_ID="your-key"
export AWS_SECRET_ACCESS_KEY="your-secret"
export AWS_DEFAULT_REGION="us-west-2"

# Or for Backblaze B2:
export B2_ACCOUNT_ID="your-id"
export B2_APPLICATION_KEY="your-key"
```

**Test backup:**
```bash
poetry run python -c "
from centinel.backup import backup_hashes
backup_hashes()
print('Backup successful')
"
```

---

## Step 8: Test Snapshot Capture

```bash
# Manual snapshot (one-off)
poetry run centinel snapshot

# Check result
ls -lh hashes/*/snapshot_*.json | tail -1

# Verify chain
poetry run centinel verify --chain
```

**Expected output:**
```
Chain valid: 1/1 links
Merkle root: aaaa...aaaa
```

---

## Step 9: Set Up Weekly Checkpoints

Create a cron job for weekly checkpoints (e.g., Sunday at 00:00 UTC):

```bash
# Edit crontab
crontab -e

# Add line (Sunday at 00:00 UTC):
0 0 * * 0 cd /opt/centinel-engine && \
  poetry run centinel checkpoint --create && \
  git -C hashes/mirrors add checkpoint-*.json && \
  git -C hashes/mirrors commit -m "Weekly checkpoint" && \
  git -C hashes/mirrors push origin main \
  >> logs/checkpoint.log 2>&1
```

**Manual test:**
```bash
poetry run centinel checkpoint --create

# Verify checkpoint
ls -lh hashes/transparency/checkpoint-*.json
cat hashes/transparency/checkpoint-*.json | jq .
```

---

## Step 10: Deploy API (For Public Querying)

If you want auditors to query your witness via REST API:

```bash
# Start API server
poetry run uvicorn centinel.api.main:app --host 0.0.0.0 --port 8000 &

# Test endpoint
curl -s http://localhost:8000/api/health

# Expected: {"status": "ok"}
```

**For production, use systemd:**

```bash
# Create service file
sudo tee /etc/systemd/system/centinel.service > /dev/null << 'EOF'
[Unit]
Description=Centinel Witness Engine
After=network.target

[Service]
User=centinel
WorkingDirectory=/opt/centinel-engine
ExecStart=/opt/centinel-engine/.venv/bin/python \
  -m uvicorn centinel.api.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
sudo systemctl enable centinel
sudo systemctl start centinel
```

---

## Step 11: Configure TLS (HTTPS)

Users will connect via HTTPS. Set up a certificate:

```bash
# Option A: Let's Encrypt (free)
sudo apt-get install certbot python3-certbot-nginx
sudo certbot certonly --standalone -d witness.example.com

# Option B: Self-signed (for testing)
openssl req -new -x509 -days 365 -nodes \
  -out /opt/centinel-engine/cert.pem \
  -keyout /opt/centinel-engine/key.pem

# Configure nginx reverse proxy
sudo tee /etc/nginx/sites-available/centinel > /dev/null << 'EOF'
server {
    listen 443 ssl;
    server_name witness.example.com;
    
    ssl_certificate /etc/letsencrypt/live/witness.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/witness.example.com/privkey.pem;
    
    location /api {
        proxy_pass http://localhost:8000;
        add_header Access-Control-Allow-Origin "https://verifier.example.com";
    }
}

server {
    listen 80;
    server_name witness.example.com;
    return 301 https://$server_name$request_uri;  # Redirect HTTP → HTTPS
}
EOF

sudo systemctl restart nginx
```

---

## Step 12: Create Witness Documentation

Create a public file announcing your witness:

```bash
cat > hashes/WITNESS.md << 'EOF'
# Centinel Witness — [Your Organization]

Operated by: [Organization Name]  
Public key: [operator_public.pem]  
Operator contact: [email@example.com]  
Mirror repository: [GitHub URL]  

## Verification

To verify this witness:

1. Download latest checkpoint:
   ```bash
   curl -s https://witness.example.com/api/checkpoint
   ```

2. Compare Merkle root with other witnesses:
   ```bash
   curl -s https://sibling-witness.example.com/api/checkpoint | jq .merkle_root
   ```

3. If all agree: integrity is established (Theorem T3)

## Updates

- Weekly checkpoint every Sunday 00:00 UTC
- Emergency checkpoints during elections (every 3–4 hours)
- OpenTimestamps proofs for Bitcoin anchoring

---

For questions contact: witness-ops@example.com
EOF

git -C hashes add WITNESS.md && git -C hashes commit -m "Add witness documentation"
```

---

## Step 13: Register with Electoral Authority & Auditors

Once your witness is live:

1. **Email electoral authority:** Announce your witness, provide URL + public key
2. **Email auditors:** Provide witness URL + instructions to verify
3. **Update Centinel registry:** PR to add your mirror to master list (https://github.com/userf8a2c4/centinel-engine/pulls)

---

## Step 14: Monitor & Test

Before elections, run comprehensive tests:

```bash
# Health check
poetry run centinel status

# Verify chain integrity
poetry run centinel verify --chain

# Test API
curl -s https://witness.example.com/api/health

# Test backup
poetry run python -c "from centinel.backup import backup_hashes; backup_hashes()"

# Test sibling connectivity
for sibling in sibling-1.example.com sibling-2.example.com; do
  curl -s https://$sibling/api/health && echo "OK" || echo "FAIL: $sibling"
done
```

---

## Troubleshooting

### "Permission denied" on hashes/ directory

```bash
chmod 755 hashes
chmod 644 hashes/*
```

### "Poetry not found"

```bash
# Install Poetry
pip install poetry --user

# Add to PATH
export PATH="$HOME/.local/bin:$PATH"
```

### "API fails to start"

```bash
# Check port is available
lsof -i :8000

# Check logs
tail -50 logs/api.log
```

---

## Checklist Before Election Night

- [ ] Chain is long (≥100 snapshots)
- [ ] Snapshots run every 5 minutes (check cron logs)
- [ ] API responds to `/api/health`
- [ ] Backups are working
- [ ] Mirror repo is syncing
- [ ] HTTPS certificate is valid
- [ ] Sibling witnesses are reachable
- [ ] Operator key is secure (chmod 600 on private key)
- [ ] Runbook is printed and at operator station

---

**For more**, see:
- [OPERATOR-RUNBOOKS.md](OPERATOR-RUNBOOKS.md) — Election night procedures
- [ANOMALY-DETECTION.md](ANOMALY-DETECTION.md) — How to interpret alerts
- [CORS-SECURITY.md](CORS-SECURITY.md) — Verifier access control

---

**Questions?** Email: witness-setup@centinel.example.com  
**Last Updated:** May 2026
