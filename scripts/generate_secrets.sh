#!/usr/bin/env bash
# Genera .env con todos los secretos necesarios para centinel-engine.
# Ejecutar UNA VEZ en el servidor. Guardar .env de forma segura (no commitear).

set -euo pipefail

if [ -f .env ]; then
  echo "ADVERTENCIA: .env ya existe. Renombrando a .env.backup.$(date +%s)"
  cp .env ".env.backup.$(date +%s)"
fi

python3 - <<'PYEOF'
import secrets, base64, sys
from datetime import datetime, timezone

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import (
        Encoding, PublicFormat, PrivateFormat, NoEncryption
    )
except ImportError:
    print("ERROR: instala cryptography primero: pip install cryptography", file=sys.stderr)
    sys.exit(1)

key = Ed25519PrivateKey.generate()
priv_pem = key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()).decode().strip()
pub_pem  = key.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo).decode().strip()

jwt_secret      = secrets.token_urlsafe(48)
encryption_key  = base64.b64encode(secrets.token_bytes(32)).decode()
api_admin_token = secrets.token_urlsafe(32)
generated_at    = datetime.now(timezone.utc).isoformat()

lines = [
    f"# Generado por generate_secrets.sh el {generated_at}",
    "# NO commitear este archivo. Agregarlo a .gitignore.",
    "",
    "# ── Claves de firma Ed25519 ────────────────────────────────",
    f'CENTINEL_SIGNING_KEY="{priv_pem}"',
    "",
    f'CENTINEL_PUBLIC_KEY="{pub_pem}"',
    "",
    "# ── Autenticación interna ──────────────────────────────────",
    f"JWT_SECRET={jwt_secret}",
    f"API_ADMIN_TOKEN={api_admin_token}",
    "",
    "# ── Cifrado en reposo ──────────────────────────────────────",
    f"ENCRYPTION_KEY={encryption_key}",
    "",
    "# ── Supabase (completar con valores del proyecto) ──────────",
    "SUPABASE_URL=https://PROYECTO.supabase.co",
    "SUPABASE_ANON_KEY=eyJ...",
    "SUPABASE_SERVICE_KEY=eyJ...",
    "",
    "# ── OpenTimestamps (opcional: fuerza un calendario específico)",
    "# OTS_SERVER=https://alice.btc.calendar.opentimestamps.org",
]

with open(".env", "w") as f:
    f.write("\n".join(lines) + "\n")

print("✓ .env generado.")
print("")
print("IMPORTANTE:")
print("  1. Completa SUPABASE_URL, SUPABASE_ANON_KEY y SUPABASE_SERVICE_KEY")
print("     con los valores de tu proyecto en supabase.com → Project Settings → API")
print("")
print("  2. Comparte CENTINEL_PUBLIC_KEY con cada testigo que quieras agregar.")
print("     La clave PRIVADA (CENTINEL_SIGNING_KEY) NUNCA se comparte.")
print("")
print("  3. Agrega .env a .gitignore para no commitearla accidentalmente.")
PYEOF

echo ""
echo "Archivo .env creado en $(pwd)/.env"
