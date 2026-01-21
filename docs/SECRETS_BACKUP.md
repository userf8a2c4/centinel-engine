# Gestión y Backup de Secrets

## Reglas básicas
- **Nunca** guardes secrets en Git o en archivos versionados.
- Usa gestores seguros como **1Password**, **Bitwarden** o **LastPass**.
- Si necesitas un backup alterno, cifra los secrets con **age** o **gpg** y guarda el
  archivo cifrado en un repositorio privado o en un drive cifrado.

## Secrets requeridos
- `ARBITRUM_PK`
- `R2_KEY_ID`
- `R2_ACCESS_KEY`
- `TELEGRAM_TOKEN`
- `TELEGRAM_CHAT_ID`
- `HEALTHCHECKS_UUID`

## Recomendación de backup cifrado
1. Crea un archivo `secrets.env` local (no versionado).
2. Cifra el archivo:
   ```bash
   age -r <RECIPIENT> -o secrets.env.age secrets.env
   ```
3. Guarda `secrets.env.age` en un storage privado y seguro.
