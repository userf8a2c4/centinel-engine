# Guía de configuración de anclaje en Arbitrum One

## [ES] Español

### Objetivo
Esta guía explica cómo preparar una wallet, desplegar el contrato `CentinelAnchor` y configurar `config/config.yaml` para anclar hashes en Arbitrum One.

### Pasos
1. **Crear una wallet dedicada en MetaMask.**
   - Genera una nueva cuenta exclusiva para C.E.N.T.I.N.E.L.
   - Guarda la seed phrase en un gestor seguro.

2. **Depositar ETH en Arbitrum One.**
   - Usa el bridge oficial: https://bridge.arbitrum.io/
   - Envía ETH desde Ethereum L1 a Arbitrum One.

3. **Deployar el contrato con Remix en Arbitrum One.**
   - Abre https://remix.ethereum.org/
   - Crea un archivo `CentinelAnchor.sol` y copia el contenido desde `contracts/CentinelAnchor.sol`.
   - Compila con Solidity ^0.8.20.
   - En "Deploy & Run", conecta MetaMask y selecciona la red Arbitrum One.
   - Despliega el contrato y confirma la transacción.

4. **Copiar el contract address.**
   - Guarda la dirección del contrato desplegado.

5. **Configurar `config/config.yaml` con las claves.**
   - Completa la sección `arbitrum` con `rpc_url`, `private_key`, `contract_address`.
   - Verifica `interval_minutes` y `batch_size`.
   - **Nunca** commitees la private key.

6. **Probar en testnet Arbitrum Sepolia.**
   - Cambia `rpc_url` a un RPC de Sepolia.
   - Despliega el contrato en Arbitrum Sepolia.
   - Ajusta `contract_address` y valida la transacción.

7. **Activar `enabled: true` y probar en mainnet.**
   - Cuando todo esté validado, activa `enabled: true`.
   - Ejecuta el pipeline y confirma el evento `HashRootAnchored` en Arbitrum One.

---

# Arbitrum One anchoring setup guide

## [EN] English

### Goal
This guide explains how to prepare a wallet, deploy the `CentinelAnchor` contract, and configure `config/config.yaml` to anchor hashes on Arbitrum One.

### Steps
1. **Create a dedicated wallet in MetaMask.**
   - Generate a new account solely for C.E.N.T.I.N.E.L.
   - Store the seed phrase in a secure vault.

2. **Deposit ETH on Arbitrum One.**
   - Use the official bridge: https://bridge.arbitrum.io/
   - Send ETH from Ethereum L1 to Arbitrum One.

3. **Deploy the contract with Remix on Arbitrum One.**
   - Open https://remix.ethereum.org/
   - Create a file `CentinelAnchor.sol` and paste the content from `contracts/CentinelAnchor.sol`.
   - Compile with Solidity ^0.8.20.
   - In "Deploy & Run", connect MetaMask and select Arbitrum One.
   - Deploy the contract and confirm the transaction.

4. **Copy the contract address.**
   - Save the deployed contract address.

5. **Configure `config/config.yaml` with keys.**
   - Fill in the `arbitrum` section (`rpc_url`, `private_key`, `contract_address`).
   - Review `interval_minutes` and `batch_size`.
   - **Never** commit the private key.

6. **Test on Arbitrum Sepolia testnet.**
   - Change `rpc_url` to a Sepolia RPC.
   - Deploy the contract on Arbitrum Sepolia.
   - Update `contract_address` and validate the transaction.

7. **Enable `enabled: true` and test on mainnet.**
   - Once validated, set `enabled: true`.
   - Run the pipeline and verify the `HashRootAnchored` event on Arbitrum One.
