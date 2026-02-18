/**
 * Batcher Module
 * AUTO-DOC-INDEX
 *
 * ES: Índice rápido
 *   1) Propósito del módulo
 *   2) Componentes principales
 *   3) Puntos de extensión
 *
 * EN: Quick index
 *   1) Module purpose
 *   2) Main components
 *   3) Extension points
 *
 * Secciones / Sections:
 *   - Configuración / Configuration
 *   - Lógica principal / Core logic
 *   - Integraciones / Integrations
 */

/**
 * Construye lotes y heartbeats para anclaje en blockchain.
 *
 * Build batches and heartbeats for blockchain anchoring.
 */

import { MerkleTree } from "merkletreejs";
import keccak256 from "keccak256";
import config from "./config.js";
import logger from "./logger.js";
import { getWallet, sendBatchToChain, sendHeartbeatToChain } from "./blockchain.js";

/**
 * Acumula hashes y publica lotes con Merkle root.
 *
 * Accumulate hashes and publish batches with a Merkle root.
 */
class Batcher {
  constructor() {
    this.entries = [];
    this.batchId = 1;
    this.batchTimer = null;
    this.heartbeatTimer = null;
  }

  /**
   * Agrega entradas de hash al lote actual.
   *
   * Add hash entries to the current batch.
   */
  addEntries(entries) {
    this.entries.push(...entries);
  }

  /**
   * Calcula el Merkle root para un conjunto de entradas.
   *
   * Compute the Merkle root for a set of entries.
   */
  buildMerkleRoot(entries) {
    const leaves = entries.map((entry) => keccak256(entry.hash));
    if (leaves.length === 0) {
      return "0x";
    }
    const tree = new MerkleTree(leaves, keccak256, { sortPairs: true });
    return `0x${tree.getRoot().toString("hex")}`;
  }

  /**
   * Crea y envía un batch firmado a la cadena.
   *
   * Create and send a signed batch to the chain.
   */
  async createBatch() {
    const wallet = getWallet();
    if (!wallet) {
      logger.warn({ msg: "Batch skipped - missing wallet" });
      return;
    }

    const batchEntries = [...this.entries];
    this.entries = [];

    const batch = {
      timestamp: new Date().toISOString(),
      root: this.buildMerkleRoot(batchEntries),
      batchId: this.batchId,
      hashes: batchEntries
    };

    const signature = await wallet.signMessage(JSON.stringify(batch));
    batch.signature = signature;

    logger.info({ msg: "Batch created", batchId: this.batchId, size: batchEntries.length });
    await sendBatchToChain(batch);

    this.batchId += 1;
  }

  /**
   * Emite un heartbeat firmado para demostrar continuidad.
   *
   * Emit a signed heartbeat to prove continuity.
   */
  async createHeartbeat() {
    const wallet = getWallet();
    if (!wallet) {
      logger.warn({ msg: "Heartbeat skipped - missing wallet" });
      return;
    }

    const heartbeat = {
      timestamp: new Date().toISOString()
    };

    heartbeat.signature = await wallet.signMessage(JSON.stringify(heartbeat));

    logger.info({ msg: "Heartbeat created" });
    await sendHeartbeatToChain(heartbeat);
  }

  /**
   * Inicia los temporizadores de batch y heartbeat.
   *
   * Start the batch and heartbeat timers.
   */
  start() {
    const batchIntervalMs = config.batchIntervalHours * 60 * 60 * 1000;
    this.batchTimer = setInterval(() => {
      this.createBatch().catch((error) => {
        logger.error({ msg: "Batch failed", error: error.message });
      });
    }, batchIntervalMs);

    const heartbeatIntervalMs = config.heartbeatIntervalHours * 60 * 60 * 1000;
    this.heartbeatTimer = setInterval(() => {
      this.createHeartbeat().catch((error) => {
        logger.error({ msg: "Heartbeat failed", error: error.message });
      });
    }, heartbeatIntervalMs);
  }
}

export default new Batcher();
