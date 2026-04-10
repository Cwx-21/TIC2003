/**
 * Stream Ingestion Utilities
 *
 * Provides format normalisation, content-type inference, structure
 * classification, and request envelope extraction for the stream ingestion
 * pipeline. These helpers are consumed by both the route handler and the
 * StreamIngestionFacade, keeping parsing logic centralised and testable
 * independent of the Express request lifecycle.
 *
 * Format Resolution Order (inferFormat):
 *   1. Explicit x-stream-format header / query param / body field.
 *   2. Content-Type header inference via FORMAT_ALIASES or substring matching.
 *   3. Fallback to 'binary' for unrecognised content types.
 */

import { parseString } from "./query.js";

/** Maximum accepted payload size in bytes (default 1 MB). */
export const MAX_STREAM_BODY_BYTES = Number.parseInt(
  process.env.STREAM_MAX_BODY_BYTES ?? "1048576",
  10
);

/**
 * Maps MIME types and shorthand format strings to canonical format identifiers.
 * Used by normalizeFormat() and inferFormatFromContentType().
 */
const FORMAT_ALIASES = new Map([
  ["json", "json"],
  ["application/json", "json"],
  ["application/ld+json", "json"],
  ["application/x-ndjson", "json"],
  ["csv", "csv"],
  ["text/csv", "csv"],
  ["application/csv", "csv"],
  ["xml", "xml"],
  ["application/xml", "xml"],
  ["text/xml", "xml"],
  ["txt", "txt"],
  ["text", "txt"],
  ["text/plain", "txt"],
  ["xls", "xls"],
  ["application/vnd.ms-excel", "xls"],
  ["xlsx", "xlsx"],
  [
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "xlsx",
  ],
  ["binary", "binary"],
  ["application/octet-stream", "binary"],
  /** Twitter API v2 tweet payload — semi-structured (text + metrics schema). */
  ["tweet", "tweet"],
]);

/**
 * Maps each canonical format to its default structure classification.
 * Can be overridden by the caller via the x-structure-kind header.
 */
const STRUCTURE_BY_FORMAT = Object.freeze({
  json: "structured",
  csv: "structured",
  xls: "structured",
  xlsx: "structured",
  xml: "semi_structured",
  /** Tweet payloads are semi-structured: raw text + partial metrics schema. */
  tweet: "semi_structured",
  txt: "unstructured",
  binary: "unstructured",
});

/**
 * Strips charset and parameter suffixes from a Content-Type header value.
 *
 * @param {string|undefined} value - Raw Content-Type string.
 * @returns {string} Normalised MIME type (e.g., 'application/json').
 */
export const normalizeContentType = (value) => {
  const normalized = parseString(value);
  if (!normalized) {
    return "application/octet-stream";
  }
  return normalized.split(";")[0].trim().toLowerCase();
};

/**
 * Resolves a shorthand or MIME format string to a canonical format identifier.
 *
 * @param {string|undefined} value - Raw format string from header, query, or body.
 * @returns {string|null} Canonical format, or null if unrecognised.
 */
export const normalizeFormat = (value) => {
  const normalized = parseString(value);
  if (!normalized) {
    return null;
  }
  return FORMAT_ALIASES.get(normalized.toLowerCase()) ?? null;
};

/**
 * Infers a canonical format from a Content-Type header.
 *
 * Performs an exact alias lookup first, then falls back to substring matching
 * for partial MIME types (e.g., 'application/vnd.api+json' → 'json').
 * Returns 'binary' for completely unrecognised types.
 *
 * @param {string} contentType - Normalised Content-Type string.
 * @returns {string} Canonical format identifier.
 */
export const inferFormatFromContentType = (contentType) => {
  const normalized = normalizeContentType(contentType);

  if (FORMAT_ALIASES.has(normalized)) {
    return FORMAT_ALIASES.get(normalized);
  }
  if (normalized.includes("json")) {
    return "json";
  }
  if (normalized.includes("csv")) {
    return "csv";
  }
  if (normalized.includes("xml")) {
    return "xml";
  }
  if (normalized.includes("excel")) {
    return "xls";
  }
  if (normalized.includes("spreadsheet")) {
    return "xlsx";
  }
  if (normalized.startsWith("text/")) {
    return "txt";
  }

  return "binary";
};

/**
 * Resolves the canonical format by checking the explicit requested format
 * first, then falling back to Content-Type inference.
 *
 * @param {object} options
 * @param {string|undefined} options.requestedFormat - Explicit format from header/query/body.
 * @param {string} options.contentType - Normalised Content-Type string.
 * @returns {string} Resolved canonical format.
 */
export const inferFormat = ({ requestedFormat, contentType }) =>
  normalizeFormat(requestedFormat) ?? inferFormatFromContentType(contentType);

/**
 * Resolves the structure classification for a given format.
 *
 * Uses the requested value if it matches a known classification, otherwise
 * falls back to the STRUCTURE_BY_FORMAT default for the format.
 *
 * @param {string} format - Canonical format identifier.
 * @param {string|undefined} requestedStructureKind - Override from request.
 * @returns {string} One of 'structured', 'semi_structured', or 'unstructured'.
 */
export const inferStructureKind = (format, requestedStructureKind) => {
  const requested = parseString(requestedStructureKind);
  if (
    requested &&
    ["structured", "semi_structured", "unstructured"].includes(requested)
  ) {
    return requested;
  }

  return STRUCTURE_BY_FORMAT[format] ?? "unstructured";
};

/**
 * Normalises metadata from the request body.
 * Rejects non-object values (arrays, primitives) and returns an empty object.
 *
 * @param {unknown} value - Raw metadata value from the request body.
 * @returns {object} Safe plain object.
 */
export const normalizeMetadata = (value) => {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return {};
  }
  return value;
};

/**
 * Returns the first non-null, non-empty string from a list of candidates.
 * Used to resolve fields that may appear in headers, query params, or body.
 *
 * @param {...(string|undefined)} values - Candidate values in priority order.
 * @returns {string|null} First resolved string, or null if all are empty.
 */
export const resolveStringCandidate = (...values) => {
  for (const value of values) {
    const parsed = parseString(value);
    if (parsed) {
      return parsed;
    }
  }
  return null;
};

/**
 * Calculates the byte size of a payload regardless of its type.
 *
 * @param {Buffer|string|object|null|undefined} payload - The raw payload.
 * @returns {number} Size in bytes.
 */
export const calculatePayloadSize = (payload) => {
  if (Buffer.isBuffer(payload)) {
    return payload.length;
  }
  if (typeof payload === "string") {
    return Buffer.byteLength(payload, "utf8");
  }
  if (payload === null || payload === undefined) {
    return 0;
  }
  return Buffer.byteLength(JSON.stringify(payload), "utf8");
};

/**
 * Extracts a normalised ingestion envelope from an Express request.
 *
 * Resolves each envelope field (source, format, metadata, payload, etc.)
 * by checking, in order: HTTP headers, query parameters, and the parsed
 * JSON body. This allows callers to specify routing metadata without
 * embedding it inside the payload itself.
 *
 * @param {import('express').Request} req - Express request object.
 * @returns {object} Normalised envelope ready for StreamIngestionFacade.ingest().
 */
export const buildEnvelopeFromRequest = (req) => {
  const bodyIsObject =
    req.body && typeof req.body === "object" && !Array.isArray(req.body) && !Buffer.isBuffer(req.body);
  const body = bodyIsObject ? req.body : null;

  const payload =
    body && Object.prototype.hasOwnProperty.call(body, "payload") ? body.payload : req.body;

  return {
    source: resolveStringCandidate(
      req.headers["x-stream-source"],
      req.query.source,
      body?.source
    ),
    streamName: resolveStringCandidate(
      req.headers["x-stream-name"],
      req.query.stream_name,
      body?.stream_name
    ),
    format: resolveStringCandidate(
      req.headers["x-stream-format"],
      req.query.format,
      body?.format
    ),
    structureKind: resolveStringCandidate(
      req.headers["x-structure-kind"],
      req.query.structure_kind,
      body?.structure_kind
    ),
    contentType: resolveStringCandidate(req.headers["content-type"], body?.content_type),
    metadata: normalizeMetadata(body?.metadata),
    payload,
  };
};
