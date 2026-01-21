# Centinel Engine v1.0

Motor ciudadano open source para monitorear portales de transparencia en Honduras, generar hashes inmutables y anclar evidencia en Ethereum L2 de forma ultra-económica.

## Objetivo

- Monitorear 19 endpoints públicos de portales de transparencia.
- Scraping defensivo cada 5 minutos con delays y rotación de User-Agent.
- Subir hashes SHA-256 a Ethereum L2 (Base por defecto) usando batches y Merkle roots.
- Heartbeat diario para demostrar operación continua.

## Fundamento legal (Honduras)

Este proyecto se apoya en la **Ley de Transparencia y Acceso a la Información Pública** (Decreto 170-2006, reformado por Decreto 60-2022):

- **Art. 3 y 4:** Derecho ciudadano al acceso a la información pública.
- **Art. 5:** Obligación de facilitar el acceso por medios electrónicos.

El scraping es moderado y defensivo: ciclo cada 5 minutos, delays aleatorios de 1.5–2.5 segundos, y orden aleatorio de solicitudes para evitar sobrecargas.

## Cómo verificar los datos públicamente

1. Cada batch contiene un **Merkle root** y una firma ECDSA del JSON completo.
2. En el explorer (BaseScan o ArbitrumScan) revisa la transacción y copia el `input` de la transacción.
3. Decodifica el JSON y verifica:
   - Que el `root` coincide con el Merkle root calculado a partir de los hashes.
   - Que la `signature` es válida para la wallet configurada.
4. Con el Merkle proof puedes demostrar que un hash individual pertenecía al batch (MerkleTreeJS).

## Instalación

```bash
npm install
```

## Variables de entorno

Copia `.env.example` a `.env` y completa los valores:

- `RPC_URL`: endpoint RPC (Alchemy/Infura).
- `CHAIN`: `base` o `arbitrum`.
- `PRIVATE_KEY`: clave privada de la wallet dedicada.
- `BATCH_INTERVAL_HOURS`: intervalo de batch (default 4).
- `ENABLE_BLOB_TX`: `true` para intentar blob tx si está disponible.
- `MAX_FEE_GWEI` y `MAX_PRIORITY_FEE_GWEI`: límites de gas.

## Ejecución

```bash
npm start
```

## Estructura

```
centinel-engine/
  src/
    config.js
    scraper.js
    hasher.js
    batcher.js
    blockchain.js
    scheduler.js
    logger.js
    alerts.js
  docs/
    BLOCKCHAIN_SETUP.md
  .env.example
  README.md
  LICENSE
```

## Licencia

GNU General Public License v3 (o posterior). Consulte el archivo [LICENSE](LICENSE).
