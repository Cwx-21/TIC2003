/**
 * In-Memory Rate Limiter Middleware
 *
 * Implements a fixed-window rate limiter using a module-level Map as the
 * backing store. Each client is identified by its IP address (extracted from
 * the x-forwarded-for header when behind a proxy) and allowed a configurable
 * number of requests per time window.
 *
 * When the store exceeds CLEANUP_THRESHOLD entries, expired windows are
 * purged inline to prevent unbounded memory growth over long runtimes.
 *
 * Configuration (via environment variables):
 *   RATE_LIMIT_WINDOW_MS — window duration in milliseconds (default 60000)
 *   RATE_LIMIT_MAX       — maximum requests per window per client (default 120)
 *
 * Response headers set on every request:
 *   X-RateLimit-Limit     — configured maximum
 *   X-RateLimit-Remaining — requests remaining in the current window
 *   Retry-After           — seconds until the window resets (on 429 only)
 */

import dotenv from "dotenv";

dotenv.config();

const WINDOW_MS = Number.parseInt(process.env.RATE_LIMIT_WINDOW_MS ?? "60000", 10);
const MAX_REQUESTS = Number.parseInt(process.env.RATE_LIMIT_MAX ?? "120", 10);
const CLEANUP_THRESHOLD = 5000;

/** Per-client request counters keyed by IP address. */
const store = new Map();

/**
 * Removes all store entries whose time window has expired.
 *
 * @param {number} now - Current timestamp from Date.now().
 */
const cleanupExpired = (now) => {
  for (const [key, entry] of store.entries()) {
    if (now - entry.startedAt > WINDOW_MS) {
      store.delete(key);
    }
  }
};

/**
 * Derives a stable client key from the request, preferring the leftmost
 * IP in the x-forwarded-for chain (the original client IP when proxied).
 *
 * @param {import('express').Request} req
 * @returns {string} Client identifier string.
 */
const getClientKey = (req) => {
  const forwarded = req.headers["x-forwarded-for"];
  if (typeof forwarded === "string" && forwarded.length > 0) {
    return forwarded.split(",")[0].trim();
  }
  return req.ip || req.connection?.remoteAddress || "unknown";
};

/**
 * Express middleware that enforces the per-client request rate limit.
 *
 * Initialises a new window on the first request from a client or after the
 * previous window expires. Returns HTTP 429 with a Retry-After header once
 * the limit is reached.
 *
 * @param {import('express').Request} req
 * @param {import('express').Response} res
 * @param {import('express').NextFunction} next
 */
const rateLimit = (req, res, next) => {
  const now = Date.now();
  const key = getClientKey(req);
  const entry = store.get(key);

  if (!entry || now - entry.startedAt > WINDOW_MS) {
    store.set(key, { startedAt: now, count: 1 });
    res.set("X-RateLimit-Limit", String(MAX_REQUESTS));
    res.set("X-RateLimit-Remaining", String(MAX_REQUESTS - 1));
    return next();
  }

  if (entry.count >= MAX_REQUESTS) {
    const retryAfterSeconds = Math.max(
      1,
      Math.ceil((WINDOW_MS - (now - entry.startedAt)) / 1000)
    );
    res.set("Retry-After", String(retryAfterSeconds));
    res.set("X-RateLimit-Limit", String(MAX_REQUESTS));
    res.set("X-RateLimit-Remaining", "0");
    return res.status(429).json({
      error: "Rate limit exceeded",
      retry_after_seconds: retryAfterSeconds,
    });
  }

  entry.count += 1;
  res.set("X-RateLimit-Limit", String(MAX_REQUESTS));
  res.set("X-RateLimit-Remaining", String(Math.max(0, MAX_REQUESTS - entry.count)));

  if (store.size > CLEANUP_THRESHOLD) {
    cleanupExpired(now);
  }

  return next();
};

export default rateLimit;
