/**
 * Index Module
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
 * Punto de entrada del motor: valida configuración y arranca el scheduler.
 *
 * Engine entry point: validate configuration and start the scheduler.
 */

import logger from "./logger.js";
import scheduler from "./scheduler.js";
import config from "./config.js";

/**
 * Valida configuración mínima y registra advertencias.
 *
 * Validate minimum configuration and log warnings.
 */
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
