/**
 * Cryptographic Utilities — Non-Repudiation & Integrity Support
 *
 * Provides SHA-256 payload hashing and HMAC-SHA256 signature verification
 * for the Task 2.7 backend security layer. All functions are pure and
 * side-effect free, making them independently testable.
 *
 * CIA mapping:
 *   Integrity        — SHA-256 hash detects post-receipt payload tampering.
 *   Confidentiality  — HMAC-SHA256 ensures payloads originate from an
 *                      authorised sender holding the shared secret.
 *   Non-repudiation  — Storing the hash alongside the record proves exactly
 *                      what bytes were received, and when.
 */

import { createHash, createHmac, timingSafeEqual } from "node:crypto";

/**
 * Computes a SHA-256 hex digest of the given data.
 *
 * Accepts strings, Buffers, or any JSON-serialisable value. The digest
 * uniquely identifies the payload content and is stored in the database
 * to support non-repudiation: if a dispute arises over what was received,
 * the stored hash can be recomputed and compared against the original payload.
 *
 * @param {string|Buffer|object} data - The data to hash.
 * @returns {string} 64-character lowercase hex digest.
 */
export const computePayloadHash = (data) => {
  const input =
    typeof data === "string"
      ? data
      : Buffer.isBuffer(data)
      ? data
      : JSON.stringify(data);
  return createHash("sha256").update(input).digest("hex");
};

/**
 * Verifies an HMAC-SHA256 signature in constant time.
 *
 * Uses Node.js timingSafeEqual to prevent timing-based side-channel attacks
 * that could allow an attacker to guess the secret one character at a time.
 * Returns false rather than throwing when lengths differ, so callers do not
 * need to handle exceptions for routine invalid-signature cases.
 *
 * @param {string} secret - The shared HMAC secret key.
 * @param {string|Buffer} payload - The raw payload that was signed.
 * @param {string} signature - The hex-encoded HMAC to verify against.
 * @returns {boolean} True only if the signature is cryptographically valid.
 */
export const verifyHmacSignature = (secret, payload, signature) => {
  const expected = createHmac("sha256", secret).update(payload).digest("hex");
  const expectedBuf = Buffer.from(expected, "utf8");
  const providedBuf = Buffer.from(signature, "utf8");
  if (expectedBuf.length !== providedBuf.length) {
    return false;
  }
  return timingSafeEqual(expectedBuf, providedBuf);
};
