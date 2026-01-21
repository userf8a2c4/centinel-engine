/**
 * Logger estructurado para Centinel Engine.
 *
 * Structured logger for Centinel Engine.
 */

import winston from "winston";

/**
 * Instancia de logger configurada con JSON y timestamps.
 *
 * Logger instance configured with JSON and timestamps.
 */
const logger = winston.createLogger({
  level: "info",
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.errors({ stack: true }),
    winston.format.json()
  ),
  transports: [new winston.transports.Console()]
});

export default logger;
