/**
 * Tweet Signature Middleware — Strategy & Null Object Patterns
 *
 * Implements the Strategy pattern for pluggable HMAC-SHA256 signature
 * verification on the tweet ingestion endpoint. The active strategy is
 * selected once at module load based on the TWEET_WEBHOOK_SECRET environment
 * variable, and is then reused for every request.
 *
 * Strategy Pattern:
 *   BaseSignatureVerifier — defines the abstract verify(req, res, next) interface.
 *   HmacSignatureVerifier  — concrete strategy; validates the
 *     x-twitter-webhooks-signature header against the configured secret.
 *   NullSignatureVerifier  — Null Object strategy; passes all requests through
 *     with a console warning when no secret is set (development mode).
 *
 * Null Object Pattern:
 *   NullSignatureVerifier satisfies the same interface as HmacSignatureVerifier
 *   so the Express middleware export never contains a null-check branch. Route
 *   handlers receive req/res/next identically regardless of which strategy is active.
 *
 * CIA mapping:
 *   Confidentiality — only callers holding the shared secret can pass verification.
 *   Integrity       — HMAC covers the full serialised body, detecting tampering.
 */

import { verifyHmacSignature } from "../utils/crypto.js";

/**
 * Abstract base — declares the verifier interface.
 * Concrete subclasses must override verify().
 *
 * @abstract
 */
class BaseSignatureVerifier {
  /**
   * Verifies the request and either calls next() or responds with 401.
   *
   * @param {import('express').Request} req
   * @param {import('express').Response} res
   * @param {Function} next
   */
  verify(req, res, next) {
    throw new Error("verify() must be implemented by a concrete subclass.");
  }
}

/**
 * Null Object strategy — allows all requests through without verification.
 *
 * Used when TWEET_WEBHOOK_SECRET is absent (local development, test environments).
 * Emits a console warning so developers know signature checking is inactive.
 */
class NullSignatureVerifier extends BaseSignatureVerifier {
  verify(req, res, next) {
    console.warn(
      "[TweetSignature] TWEET_WEBHOOK_SECRET not set — signature check skipped."
    );
    next();
  }
}

/**
 * Concrete HMAC-SHA256 strategy.
 *
 * Reads the x-twitter-webhooks-signature header, strips the 'sha256=' prefix
 * Twitter prepends, then delegates to verifyHmacSignature() for constant-time
 * comparison. Falls back to re-serialising req.body when raw body bytes are
 * not available (i.e., when express.json() has already consumed the stream).
 */
class HmacSignatureVerifier extends BaseSignatureVerifier {
  /**
   * @param {string} secret - The HMAC secret key from TWEET_WEBHOOK_SECRET.
   */
  constructor(secret) {
    super();
    this._secret = secret;
  }

  /**
   * Verifies the HMAC signature on the incoming request.
   *
   * @param {import('express').Request} req
   * @param {import('express').Response} res
   * @param {Function} next
   */
  verify(req, res, next) {
    const header = req.headers["x-twitter-webhooks-signature"];
    if (!header) {
      return res.status(401).json({
        error: "Missing x-twitter-webhooks-signature header.",
      });
    }

    // Twitter prepends 'sha256=' — strip it before comparison
    const hexSignature = header.startsWith("sha256=")
      ? header.slice(7)
      : header;

    // Use the preserved raw body buffer if available; otherwise re-serialise
    const rawBody = req.rawBody ?? JSON.stringify(req.body);

    if (!verifyHmacSignature(this._secret, rawBody, hexSignature)) {
      return res.status(401).json({ error: "Invalid webhook signature." });
    }

    next();
  }
}

/**
 * Selects the active verifier based on environment configuration.
 * This factory function encapsulates the Strategy selection so the
 * middleware export remains a simple function reference.
 *
 * @returns {BaseSignatureVerifier}
 */
const createVerifier = () => {
  const secret = process.env.TWEET_WEBHOOK_SECRET;
  return secret
    ? new HmacSignatureVerifier(secret)
    : new NullSignatureVerifier();
};

/** Singleton verifier instance — resolved once at module load. */
const verifier = createVerifier();

/**
 * Express middleware that delegates to the active SignatureVerifier strategy.
 * Mount this before the tweet ingest route handler.
 *
 * @type {import('express').RequestHandler}
 */
export const tweetSignatureMiddleware = (req, res, next) =>
  verifier.verify(req, res, next);
