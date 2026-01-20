# Configuración de Blockchain (Base / Arbitrum)

## 1. Crear wallet dedicada

- Use una wallet nueva exclusivamente para Centinel Engine.
- Nunca reutilice una wallet personal.
- Anote la clave privada y guárdela **offline**.

## 2. Financiar la wallet

- Base: use un bridge desde Ethereum mainnet o un exchange.
- Arbitrum One: bridge oficial o exchange.
- Mantenga fondos mínimos para cubrir transacciones esporádicas.

## 3. RPC Provider

Regístrese en Alchemy o Infura y copie el endpoint RPC para la red elegida.

Ejemplo (Base):

```
RPC_URL=https://base-mainnet.g.alchemy.com/v2/TU_API_KEY
```

## 4. Configuración de `.env`

```
RPC_URL=...
CHAIN=base
PRIVATE_KEY=0x...
BATCH_INTERVAL_HOURS=4
ENABLE_BLOB_TX=false
MAX_FEE_GWEI=0.05
MAX_PRIORITY_FEE_GWEI=0.01
```

## 5. Verificación en explorer

1. Abra BaseScan o ArbitrumScan.
2. Busque la transacción enviada por la wallet.
3. Copie el `input` (payload JSON).
4. Verifique:
   - `root` es el Merkle root de los hashes.
   - `signature` coincide con la wallet.

## 6. Heartbeat diario

El heartbeat crea una transacción diaria con:

```json
{
  "timestamp": "...",
  "signature": "..."
}
```

Sirve para demostrar que el sistema sigue activo incluso si no hay cambios en los endpoints.

## 7. Seguridad recomendada

- **Nunca** exponga `PRIVATE_KEY` en repositorios o logs.
- Use variables de entorno y secretos cifrados.
- Revise el costo de gas antes de activar blobs.
- Limite el balance de la wallet a lo estrictamente necesario.
