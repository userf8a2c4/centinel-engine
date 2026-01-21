import logger from "./logger.js";
import scheduler from "./scheduler.js";
import config from "./config.js";

const validateConfig = () => {
  if (!config.rpcUrl) {
    logger.warn({ msg: "RPC_URL missing, blockchain uploads will fail." });
  }
  if (!config.privateKey) {
    logger.warn({ msg: "PRIVATE_KEY missing, blockchain uploads will fail." });
  }
  if (config.urls.length !== 19) {
    logger.warn({ msg: "Expected 19 URLs", count: config.urls.length });
  }
};

validateConfig();
logger.info({ msg: "Centinel Engine starting", version: config.version, chain: config.chain });

scheduler.start();
