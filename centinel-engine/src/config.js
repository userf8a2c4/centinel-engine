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
  "Centinel-Engine/1.0 (proyecto ciudadano open source de transparencia en Honduras - https://github.com/tu-usuario/centinel-engine)"
];

const config = {
  appName: "centinel-engine",
  version: "1.0",
  urls,
  userAgents,
  requestTimeoutMs: 30_000,
  baseDelayMs: 2000,
  jitterMs: 500,
  cycleIntervalMs: 300_000,
  degradedIntervalRangeMs: [360_000, 420_000],
  maxErrorsBeforeDegrade: 3,
  maxFailedCyclesBeforeWarn: 5,
  batchIntervalHours: Number(process.env.BATCH_INTERVAL_HOURS || 4),
  heartbeatIntervalHours: 24,
  rpcUrl: process.env.RPC_URL || "",
  chain: process.env.CHAIN || "base",
  privateKey: process.env.PRIVATE_KEY || "",
  enableBlobTx: process.env.ENABLE_BLOB_TX === "true",
  maxFeePerGasGwei: Number(process.env.MAX_FEE_GWEI || 0.05),
  maxPriorityFeePerGasGwei: Number(process.env.MAX_PRIORITY_FEE_GWEI || 0.01),
  telegramToken: process.env.TELEGRAM_BOT_TOKEN || "",
  telegramChatId: process.env.TELEGRAM_CHAT_ID || ""
};

export default config;
