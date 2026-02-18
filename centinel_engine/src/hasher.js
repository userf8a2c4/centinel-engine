/**
 * Hasher Module
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
 * Utilidades de hashing para Centinel Engine.
 *
 * Hashing utilities for Centinel Engine.
 */

import crypto from "crypto";

/**
 * Calcula SHA-256 en formato hexadecimal con prefijo 0x.
 *
 * Compute SHA-256 in hex format with 0x prefix.
 */
export const sha256Hex = (input) => {
  return `0x${crypto.createHash("sha256").update(input).digest("hex")}`;
};
