/**
 * Configuración centralizada de Centinel Engine.
 *
 * Central configuration for Centinel Engine.
 */

import dotenv from "dotenv";

dotenv.config();

const urls = [
  "https://transparencia.portal-1.example/api/datos",
  "https://transparencia.portal-2.example/api/datos",
  "https://transparencia.portal-3.example/api/datos",
  "https://transparencia.portal-4.example/api/datos",
  "https://transparencia.portal-5.example/api/datos",
  "https://transparencia.portal-6.example/api/datos",
  "https://transparencia.portal-7.example/api/datos",
  "https://transparencia.portal-8.example/api/datos",
  "https://transparencia.portal-9.example/api/datos",
  "https://transparencia.portal-10.example/api/datos",
  "https://transparencia.portal-11.example/api/datos",
  "https://transparencia.portal-12.example/api/datos",
  "https://transparencia.portal-13.example/api/datos",
  "https://transparencia.portal-14.example/api/datos",
  "https://transparencia.portal-15.example/api/datos",
  "https://transparencia.portal-16.example/api/datos",
  "https://transparencia.portal-17.example/api/datos",
  "https://transparencia.portal-18.example/api/datos",
  "https://transparencia.portal-19.example/api/datos"
];

const userAgents = [
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/120.0",
  "Centinel-Engine/1.0 (proyecto ciudadano open source de transparencia pública - https://github.com/tu-usuario/centinel-engine)"
];

const minutesToMs = (minutes) => minutes * 60 * 1000;
const hoursToMs = (hours) => hours * 60 * 60 * 1000;
const daysToMs = (days) => days * 24 * 60 * 60 * 1000;

const mode = process.env.CENTINEL_MODE || "maintenance";
const cadenceByMode = {
  maintenance: {
    cycleIntervalMs: daysToMs(30),
    degradedIntervalRangeMs: [daysToMs(31), daysToMs(35)],
    batchIntervalHours: 24 * 30,
    heartbeatIntervalHours: 24 * 7
  },
  monitoring: {
    cycleIntervalMs: hoursToMs(24),
    degradedIntervalRangeMs: [hoursToMs(36), hoursToMs(72)],
    batchIntervalHours: 24,
    heartbeatIntervalHours: 24
  },
  election: {
    cycleIntervalMs: minutesToMs(5),
    degradedIntervalRangeMs: [minutesToMs(7), minutesToMs(15)],
    batchIntervalHours: 1,
    heartbeatIntervalHours: 6
  }
};
const cadence = cadenceByMode[mode] || cadenceByMode.maintenance;

const config = {
  appName: "centinel-engine",
  version: "1.0",
  mode,
  urls,
  userAgents,
  requestTimeoutMs: 30_000,
  baseDelayMs: 2000,
  jitterMs: 500,
  cycleIntervalMs: cadence.cycleIntervalMs,
  degradedIntervalRangeMs: cadence.degradedIntervalRangeMs,
  maxErrorsBeforeDegrade: 3,
  maxFailedCyclesBeforeWarn: 5,
  batchIntervalHours: Number(
    process.env.BATCH_INTERVAL_HOURS || cadence.batchIntervalHours
  ),
  heartbeatIntervalHours: Number(
    process.env.HEARTBEAT_INTERVAL_HOURS || cadence.heartbeatIntervalHours
  ),
  rpcUrl: process.env.RPC_URL || "",
  chain: process.env.CHAIN || "base",
  privateKey: process.env.PRIVATE_KEY || "",
  enableBlobTx: process.env.ENABLE_BLOB_TX === "true",
  maxFeePerGasGwei: Number(process.env.MAX_FEE_GWEI || 0.05),
  maxPriorityFeePerGasGwei: Number(process.env.MAX_PRIORITY_FEE_GWEI || 0.01)
};

export default config;
