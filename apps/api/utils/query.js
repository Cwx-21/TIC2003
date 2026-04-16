/**
 * Query Parameter Parsing Utilities
 *
 * Provides typed, safe parsers for common query string values used across
 * all route handlers. Each function returns null (or a safe default) rather
 * than throwing, so callers can apply conditional WHERE clause filtering
 * without additional try/catch blocks.
 *
 * All values passed to SQL queries should go through these helpers to ensure
 * that only well-formed scalars reach the parameterised query replacements.
 */

/**
 * Parses a string value into a positive integer.
 *
 * @param {string|undefined} value - Raw query parameter value.
 * @returns {number|null} Parsed positive integer, or null if invalid.
 */
export const parsePositiveInt = (value) => {
  const parsed = Number.parseInt(value, 10);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    return null;
  }
  return parsed;
};

/**
 * Parses a LIMIT query parameter, clamping the result to a safe maximum.
 *
 * Returns defaultValue when the input is missing or invalid, and caps
 * the result at maxValue to prevent unbounded result sets.
 *
 * @param {string|undefined} value - Raw query parameter value.
 * @param {number} [defaultValue=50] - Fallback when value is absent or invalid.
 * @param {number} [maxValue=200] - Upper bound for the returned limit.
 * @returns {number} A safe, clamped limit value.
 */
export const parseLimit = (value, defaultValue = 50, maxValue = 200) => {
  const parsed = parsePositiveInt(value);
  if (!parsed) {
    return defaultValue;
  }
  return Math.min(parsed, maxValue);
};

/**
 * Parses and trims a string query parameter.
 *
 * @param {string|undefined} value - Raw query parameter value.
 * @returns {string|null} Trimmed non-empty string, or null if empty or not a string.
 */
export const parseString = (value) => {
  if (typeof value !== "string") {
    return null;
  }
  const trimmed = value.trim();
  return trimmed.length ? trimmed : null;
};
