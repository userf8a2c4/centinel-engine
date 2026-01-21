/**
 * Utilidades de publicación en blockchain para Centinel Engine.
 *
 * Blockchain publishing utilities for Centinel Engine.
 */

import { ethers } from "ethers";
import config from "./config.js";
import logger from "./logger.js";

const provider = new ethers.JsonRpcProvider(config.rpcUrl);
const wallet = config.privateKey ? new ethers.Wallet(config.privateKey, provider) : null;

/**
 * Convierte gwei a wei.
 *
 * Convert gwei to wei.
 */
const toWei = (gwei) => ethers.parseUnits(gwei.toString(), "gwei");

/**
 * Calcula overrides de tarifas para la transacción.
 *
 * Compute fee overrides for the transaction.
 */
const getFeeOverrides = () => {
  return {
    maxFeePerGas: toWei(config.maxFeePerGasGwei),
    maxPriorityFeePerGas: toWei(config.maxPriorityFeePerGasGwei)
  };
};

/**
 * Verifica soporte de transacciones blob.
 *
 * Check for blob transaction support.
 */
const supportsBlobTx = async () => {
  try {
    await provider.send("eth_blobGasPrice", []);
    return true;
  } catch (error) {
    return false;
  }
};

/**
 * Envía un payload a la cadena con el label indicado.
 *
 * Send a payload to the chain with the given label.
 */
const sendTransaction = async (payload, label) => {
  if (!wallet) {
    throw new Error("Missing PRIVATE_KEY for blockchain operations");
  }

  const payloadHex = ethers.hexlify(ethers.toUtf8Bytes(payload));
  const feeOverrides = getFeeOverrides();

  if (config.enableBlobTx && (await supportsBlobTx())) {
    try {
      const tx = await wallet.sendTransaction({
        type: 3,
        to: wallet.address,
        value: 0,
        data: "0x",
        blobs: [payloadHex],
        ...feeOverrides
      });
      logger.info({ msg: "Blob transaction sent", label, hash: tx.hash });
      return tx;
    } catch (error) {
      logger.warn({ msg: "Blob transaction failed, falling back", error: error.message });
    }
  }

  const gasLimit = await provider.estimateGas({
    from: wallet.address,
    to: wallet.address,
    data: payloadHex,
    value: 0
  });

  const tx = await wallet.sendTransaction({
    to: wallet.address,
    data: payloadHex,
    value: 0,
    gasLimit,
    ...feeOverrides
  });

  logger.info({ msg: "Calldata transaction sent", label, hash: tx.hash });
  return tx;
};

/**
 * Envía un batch firmado a la cadena.
 *
 * Send a signed batch to the chain.
 */
export const sendBatchToChain = async (batch) => {
  const payload = JSON.stringify(batch);
  return sendTransaction(payload, "batch");
};

/**
 * Envía un heartbeat firmado a la cadena.
 *
 * Send a signed heartbeat to the chain.
 */
export const sendHeartbeatToChain = async (heartbeat) => {
  const payload = JSON.stringify(heartbeat);
  return sendTransaction(payload, "heartbeat");
};

/**
 * Devuelve la wallet configurada (o null si falta).
 *
 * Return the configured wallet (or null if missing).
 */
export const getWallet = () => wallet;
