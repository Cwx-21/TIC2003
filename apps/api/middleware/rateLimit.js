import dotenv from "dotenv";

dotenv.config();

const WINDOW_MS = Number.parseInt(process.env.RATE_LIMIT_WINDOW_MS ?? "60000", 10);
const MAX_REQUESTS = Number.parseInt(process.env.RATE_LIMIT_MAX ?? "120", 10);
const CLEANUP_THRESHOLD = 5000;

const store = new Map();

const cleanupExpired = (now) => {
  for (const [key, entry] of store.entries()) {
    if (now - entry.startedAt > WINDOW_MS) {
      store.delete(key);
    }
  }
};

const getClientKey = (req) => {
  const forwarded = req.headers["x-forwarded-for"];
  if (typeof forwarded === "string" && forwarded.length > 0) {
    return forwarded.split(",")[0].trim();
  }
  return req.ip || req.connection?.remoteAddress || "unknown";
};

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
