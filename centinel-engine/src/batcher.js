import { MerkleTree } from "merkletreejs";
import keccak256 from "keccak256";
import config from "./config.js";
import logger from "./logger.js";
import { getWallet, sendBatchToChain, sendHeartbeatToChain } from "./blockchain.js";

class Batcher {
  constructor() {
    this.entries = [];
    this.batchId = 1;
    this.batchTimer = null;
    this.heartbeatTimer = null;
  }

  addEntries(entries) {
    this.entries.push(...entries);
  }

  buildMerkleRoot(entries) {
    const leaves = entries.map((entry) => keccak256(entry.hash));
    if (leaves.length === 0) {
      return "0x";
    }
    const tree = new MerkleTree(leaves, keccak256, { sortPairs: true });
    return `0x${tree.getRoot().toString("hex")}`;
  }

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
