/**
 * CORS Middleware
 *
 * Builds an Express CORS middleware that restricts cross-origin requests to
 * a fixed set of allowed origins. The default set covers the local Vite dev
 * server; additional origins can be injected at runtime via the CORS_ORIGINS
 * environment variable (comma-separated list).
 *
 * Requests with no Origin header (e.g., server-to-server or curl) are
 * permitted unconditionally. All other origins are compared against the
 * allowedOrigins Set for O(1) lookup.
 */

import cors from "cors";
import dotenv from "dotenv";

dotenv.config();

const defaultOrigins = ["http://localhost:5173", "http://127.0.0.1:5173"];

// Additional origins injected from the runtime environment
const extraOrigins = (process.env.CORS_ORIGINS || "")
  .split(",")
  .map((origin) => origin.trim())
  .filter(Boolean);

const allowedOrigins = new Set([...defaultOrigins, ...extraOrigins]);

const corsOptions = {
  /**
   * Validates the incoming Origin header against the allowedOrigins Set.
   * Requests without an Origin (e.g., same-origin or non-browser) are
   * passed through without restriction.
   *
   * @param {string|undefined} origin - The value of the request Origin header.
   * @param {Function} callback - CORS callback: callback(err, allowed).
   */
  origin(origin, callback) {
    if (!origin) {
      return callback(null, true);
    }
    if (allowedOrigins.has(origin)) {
      return callback(null, true);
    }
    return callback(null, false);
  },
  credentials: true,
};

export const corsMiddleware = cors(corsOptions);
export { allowedOrigins, corsOptions };
