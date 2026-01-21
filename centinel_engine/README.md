# Centinel Engine v1.0

## Español

Motor ciudadano open source para monitorear portales de transparencia en Honduras, generar hashes inmutables y anclar evidencia en redes blockchain de bajo costo. Se entrega como paquete Node.js independiente porque requiere dependencias y ciclos de ejecución distintos al pipeline principal.

### Objetivo
- Monitorear 19 endpoints públicos de portales de transparencia.
- Scraping defensivo con delays y rotación de User-Agent.
- Subir hashes SHA-256 a L2 (Base por defecto) usando batches y Merkle roots.
- Heartbeat periódico para demostrar operación continua.

### Cadencia operativa recomendada
- **Modo mantenimiento/desarrollo:** scraping y anclaje en L2 **1 vez al mes**.
- **Modo monitoreo normal:** entre **24 y 72 horas**.
- **Modo elección activa:** entre **5 y 15 minutos**.

### Marco legal y límites de operación (Honduras)
Este proyecto se sustenta en el derecho de acceso a la información pública y en la obligación de publicar información por medios electrónicos.

Referencias normativas principales:
- **Ley de Transparencia y Acceso a la Información Pública** (Decreto 170-2006, reformas Decreto 60-2022).
- **Art. 3 y 4:** Reconocen el derecho ciudadano a acceder a información pública.
- **Art. 5:** Establece la obligación de facilitar el acceso por medios electrónicos.

Alcance operativo:
- Finalidad de auditoría técnica y evidencia reproducible.
- Sin interferir con sistemas oficiales ni sustituir autoridades.
- Sin tratamiento de datos personales; solo fuentes públicas.
- Scraping defensivo con ventanas y retardos para evitar sobrecargas.

### Cómo verificar los datos públicamente
1. Cada batch contiene un **Merkle root** y una firma ECDSA del JSON completo.
2. En el explorer (BaseScan o ArbitrumScan) revisa la transacción y copia el `input`.
3. Decodifica el JSON y verifica:
   - Que el `root` coincide con el Merkle root calculado a partir de los hashes.
   - Que la `signature` es válida para la wallet configurada.
4. Con el Merkle proof puedes demostrar que un hash individual pertenecía al batch (MerkleTreeJS).

### Instalación
```bash
npm install
```

### Variables de entorno
Copia `.env.example` a `.env` y completa los valores:

- `CENTINEL_MODE`: `maintenance`, `monitoring` o `election`.
- `RPC_URL`: endpoint RPC (Alchemy/Infura).
- `CHAIN`: `base` o `arbitrum`.
- `PRIVATE_KEY`: clave privada de la wallet dedicada.
- `BATCH_INTERVAL_HOURS`: intervalo de batch (opcional, override del modo).
- `HEARTBEAT_INTERVAL_HOURS`: intervalo de heartbeat (opcional, override del modo).
- `ENABLE_BLOB_TX`: `true` para intentar blob tx si está disponible.
- `MAX_FEE_GWEI` y `MAX_PRIORITY_FEE_GWEI`: límites de gas.

### Ejecución
```bash
npm start
```

### Estructura
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
  docs/
    BLOCKCHAIN_SETUP.md
  .env.example
  README.md
  LICENSE
```

### Licencia
GNU General Public License v3 (o posterior). Consulte el archivo [LICENSE](LICENSE).

---

## English

Open-source civic engine to monitor transparency portals in Honduras, generate immutable hashes, and anchor evidence on low-cost blockchain networks. It ships as a separate Node.js package because it requires distinct dependencies and execution cycles from the main pipeline.

### Goals
- Monitor 19 public transparency endpoints.
- Defensive scraping with delays and User-Agent rotation.
- Upload SHA-256 hashes to L2 (Base by default) using batches and Merkle roots.
- Periodic heartbeat to prove continuous operation.

### Recommended operating cadence
- **Maintenance/development mode:** scraping and L2 anchoring **once per month**.
- **Normal monitoring mode:** between **24 and 72 hours**.
- **Active election mode:** between **5 and 15 minutes**.

### Legal basis and operating boundaries (Honduras)
This project is grounded in the right to access public information and the obligation to publish information through electronic means.

Primary legal references:
- **Law on Transparency and Access to Public Information** (Decree 170-2006, amended by Decree 60-2022).
- **Arts. 3 & 4:** Recognize the citizen right to access public information.
- **Art. 5:** Establishes the obligation to facilitate access through electronic means.

Operational scope:
- Technical auditing and reproducible evidence purposes.
- No interference with official systems or replacement of authorities.
- No personal data processing; public sources only.
- Defensive scraping windows and delays to avoid overload.

### How to verify data publicly
1. Each batch contains a **Merkle root** and an ECDSA signature of the full JSON.
2. In the explorer (BaseScan or ArbitrumScan) review the transaction and copy the `input`.
3. Decode the JSON and verify:
   - The `root` matches the Merkle root computed from the hashes.
   - The `signature` is valid for the configured wallet.
4. With the Merkle proof you can show that an individual hash belonged to the batch (MerkleTreeJS).

### Installation
```bash
npm install
```

### Environment variables
Copy `.env.example` to `.env` and fill in the values:

- `CENTINEL_MODE`: `maintenance`, `monitoring`, or `election`.
- `RPC_URL`: RPC endpoint (Alchemy/Infura).
- `CHAIN`: `base` or `arbitrum`.
- `PRIVATE_KEY`: private key for the dedicated wallet.
- `BATCH_INTERVAL_HOURS`: batch interval (optional mode override).
- `HEARTBEAT_INTERVAL_HOURS`: heartbeat interval (optional mode override).
- `ENABLE_BLOB_TX`: `true` to attempt blob tx if available.
- `MAX_FEE_GWEI` and `MAX_PRIORITY_FEE_GWEI`: gas limits.

### Run
```bash
npm start
```

### Structure
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
  docs/
    BLOCKCHAIN_SETUP.md
  .env.example
  README.md
  LICENSE
```

### License
GNU General Public License v3 (or later). See [LICENSE](LICENSE).
