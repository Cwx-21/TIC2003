/**
 * Shared Route Utilities
 *
 * Provides helper functions used across multiple route handlers for
 * database access validation, symbol normalisation, and boolean
 * query parameter parsing.
 */

import sequelize, { hasDbConfig } from "../database/index.js";

/**
 * Guards a route handler against requests made when the database is
 * not configured. Sends a 500 response and returns null so callers
 * can short-circuit with an early return.
 *
 * @param {import('express').Response} res - Express response object.
 * @returns {import('sequelize').Sequelize|null} The Sequelize instance, or null.
 */
export const getDbOrError = (res) => {
  if (!hasDbConfig || !sequelize) {
    res.status(500).json({ error: "DATABASE_URL is not configured" });
    return null;
  }
  return sequelize;
};

/**
 * Normalises an asset symbol to uppercase, trimming surrounding whitespace.
 *
 * Used to ensure consistent symbol casing before building SQL WHERE clauses
 * (e.g., 'btc' and ' BTC ' both resolve to 'BTC').
 *
 * @param {unknown} value - Raw value from route params or query string.
 * @returns {string|null} Uppercased non-empty symbol string, or null if invalid.
 */
export const normalizeSymbol = (value) => {
  if (typeof value !== "string") {
    return null;
  }
  const trimmed = value.trim().toUpperCase();
  return trimmed.length ? trimmed : null;
};

/**
 * Parses a boolean-like query string value.
 *
 * Accepts truthy representations ('true', '1', 'yes') and falsy ones
 * ('false', '0', 'no'). Returns null for any unrecognised value so that
 * callers can distinguish "not provided" from "explicitly false".
 *
 * @param {unknown} value - Raw query parameter value.
 * @returns {boolean|null} Parsed boolean, or null if unrecognised.
 */
export const parseBoolean = (value) => {
  if (typeof value !== "string") {
    return null;
  }
  const normalized = value.trim().toLowerCase();
  if (["true", "1", "yes"].includes(normalized)) {
    return true;
  }
  if (["false", "0", "no"].includes(normalized)) {
    return false;
  }
  return null;
};
