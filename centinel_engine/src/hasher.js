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
