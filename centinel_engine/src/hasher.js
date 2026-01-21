import crypto from "crypto";

export const sha256Hex = (input) => {
  return `0x${crypto.createHash("sha256").update(input).digest("hex")}`;
};
