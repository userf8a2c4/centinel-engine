/**
 * Logger Module
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
