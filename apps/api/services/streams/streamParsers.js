/**
 * Stream Parsers — Factory & Strategy Pattern
 *
 * Implements the Factory and Strategy design patterns for stream payload parsing:
 *
 *   Strategy Pattern — BaseStreamParser defines a common interface; each
 *     concrete subclass (JsonStreamParser, CsvStreamParser, etc.) encapsulates
 *     a distinct parsing algorithm. Callers depend only on the parse() interface,
 *     not on any specific parser implementation.
 *
 *   Factory Pattern — StreamParserFactory.getParser(format) selects and returns
 *     the appropriate concrete parser based on the requested format string.
 *     Adding a new format requires only a new parser subclass and registration
 *     in DEFAULT_PARSERS — no changes to the factory or the facade.
 *
 * Each parser's parse() method returns a normalised result object containing:
 *   payload_json    — Structured representation (for JSON/CSV/XML/text).
 *   payload_text    — Raw text string (for XML and text formats).
 *   payload_base64  — Base64-encoded binary (for XLS/XLSX/binary formats).
 *   record_count    — Number of logical records in the payload.
 *   structure_kind  — 'structured', 'semi_structured', or 'unstructured'.
 *   original_size_bytes — Byte size of the raw input payload.
 *   parser_key      — Identifier of the parser that processed the payload.
 */

import {
  calculatePayloadSize,
  inferStructureKind,
  normalizeContentType,
} from "../../utils/streaming.js";

/** Thrown by parsers and the facade when input fails validation. */
export class StreamValidationError extends Error {}

/**
 * Abstract base class for all stream parsers.
 *
 * Provides shared utilities for payload normalisation (text and binary)
 * and result finalisation. Concrete subclasses must override parse().
 *
 * @abstract
 */
class BaseStreamParser {
  /**
   * @param {string} key - Unique identifier for this parser (stored as parser_key).
   * @param {string[]} formats - List of canonical format strings this parser handles.
   */
  constructor(key, formats) {
    this.key = key;
    this.formats = new Set(formats);
  }

  /**
   * Returns true if this parser supports the given canonical format.
   *
   * @param {string} format - Canonical format string (e.g., 'json', 'csv').
   * @returns {boolean}
   */
  supports(format) {
    return this.formats.has(format);
  }

  /**
   * Parses a raw payload and returns a normalised result object.
   * Must be overridden by every concrete subclass.
   *
   * @abstract
   * @param {object} options
   * @param {*} options.payload - Raw request body.
   * @param {string} options.format - Canonical format string.
   * @param {string} options.contentType - Normalised Content-Type string.
   * @returns {object} Normalised parse result.
   */
  parse() {
    throw new Error("Parser must implement parse()");
  }

  /**
   * Coerces a payload to a UTF-8 string, accepting strings, Buffers,
   * or any JSON-serialisable value. Throws StreamValidationError if null.
   *
   * @param {*} payload
   * @returns {string}
   */
  normalizeTextPayload(payload) {
    if (typeof payload === "string") {
      return payload;
    }
    if (Buffer.isBuffer(payload)) {
      return payload.toString("utf8");
    }
    if (payload === null || payload === undefined) {
      throw new StreamValidationError("Payload is required.");
    }
    return JSON.stringify(payload);
  }

  /**
   * Coerces a payload to a Node.js Buffer, accepting Buffers, strings,
   * or any JSON-serialisable value. Throws StreamValidationError if null.
   *
   * @param {*} payload
   * @returns {Buffer}
   */
  normalizeBinaryPayload(payload) {
    if (Buffer.isBuffer(payload)) {
      return payload;
    }
    if (typeof payload === "string") {
      return Buffer.from(payload, "utf8");
    }
    if (payload === null || payload === undefined) {
      throw new StreamValidationError("Payload is required.");
    }
    return Buffer.from(JSON.stringify(payload), "utf8");
  }

  /**
   * Merges parser-specific fields with common metadata computed from the
   * raw payload (size, content_type, structure_kind, parser_key).
   *
   * @param {object} options
   * @param {string} options.format - Canonical format string.
   * @param {string} options.contentType - Normalised Content-Type string.
   * @param {*} options.payload - Raw payload used for size calculation.
   * @param {...*} options.rest - Parser-specific fields to merge in.
   * @returns {object} Fully populated parse result.
   */
  finalizeResult({ format, contentType, payload, ...result }) {
    return {
      ...result,
      format,
      content_type: normalizeContentType(contentType),
      original_size_bytes: calculatePayloadSize(payload),
      structure_kind:
        result.structure_kind ?? inferStructureKind(format, result.structure_kind),
      parser_key: this.key,
    };
  }
}

/**
 * Parses JSON payloads — both objects and arrays.
 * Stores the parsed value in payload_json and counts array elements as records.
 */
class JsonStreamParser extends BaseStreamParser {
  constructor() {
    super("json_parser", ["json"]);
  }

  /** @param {{payload: *, format: string, contentType: string}} options */
  parse({ payload, format, contentType }) {
    const parsed =
      typeof payload === "string"
        ? JSON.parse(payload)
        : payload;

    if (parsed === null || parsed === undefined) {
      throw new StreamValidationError("JSON payload is required.");
    }

    return this.finalizeResult({
      format,
      contentType,
      payload,
      payload_json: parsed,
      record_count: Array.isArray(parsed) ? parsed.length : 1,
      structure_kind: "structured",
    });
  }
}

/**
 * Splits a single CSV line into cells, correctly handling quoted fields
 * and escaped double-quote characters.
 *
 * @param {string} line - A single CSV row string.
 * @returns {string[]} Array of trimmed cell values.
 */
const splitCsvLine = (line) => {
  const cells = [];
  let current = "";
  let inQuotes = false;

  for (let index = 0; index < line.length; index += 1) {
    const character = line[index];

    if (character === "\"") {
      if (inQuotes && line[index + 1] === "\"") {
        current += "\"";
        index += 1;
        continue;
      }

      inQuotes = !inQuotes;
      continue;
    }

    if (character === "," && !inQuotes) {
      cells.push(current.trim());
      current = "";
      continue;
    }

    current += character;
  }

  cells.push(current.trim());
  return cells;
};

/**
 * Parses CSV payloads into a structured { headers, rows } object.
 * The first line is treated as the header row; subsequent lines become records.
 */
class CsvStreamParser extends BaseStreamParser {
  constructor() {
    super("csv_parser", ["csv"]);
  }

  /** @param {{payload: *, format: string, contentType: string}} options */
  parse({ payload, format, contentType }) {
    const text = this.normalizeTextPayload(payload).trim();
    if (!text) {
      throw new StreamValidationError("CSV payload is required.");
    }

    const lines = text.split(/\r?\n/).filter((line) => line.length > 0);
    const headers = splitCsvLine(lines[0]).map(
      (header, index) => header || `column_${index + 1}`
    );
    const rows = lines.slice(1).map((line) => {
      const values = splitCsvLine(line);
      return headers.reduce((record, header, index) => {
        record[header] = values[index] ?? null;
        return record;
      }, {});
    });

    return this.finalizeResult({
      format,
      contentType,
      payload,
      payload_json: {
        headers,
        rows,
      },
      payload_text: text,
      record_count: rows.length,
      structure_kind: "structured",
    });
  }
}

/**
 * Parses XML payloads using lightweight regex extraction.
 * Stores the raw XML text in payload_text and a structural summary in payload_json.
 */
class XmlStreamParser extends BaseStreamParser {
  constructor() {
    super("xml_parser", ["xml"]);
  }

  /** @param {{payload: *, format: string, contentType: string}} options */
  parse({ payload, format, contentType }) {
    const text = this.normalizeTextPayload(payload).trim();
    if (!text) {
      throw new StreamValidationError("XML payload is required.");
    }

    const rootMatch = text.match(/<([A-Za-z_][\w:.-]*)\b[^>]*>/);
    const tagMatches = text.match(/<([A-Za-z_][\w:.-]*)\b/g) ?? [];
    const attributeMatches =
      text.match(/\s[A-Za-z_:][\w:.-]*\s*=\s*["'][^"']*["']/g) ?? [];

    return this.finalizeResult({
      format,
      contentType,
      payload,
      payload_json: {
        root_tag: rootMatch?.[1] ?? null,
        tag_count: tagMatches.length,
        attribute_count: attributeMatches.length,
      },
      payload_text: text,
      record_count: 1,
      structure_kind: "semi_structured",
    });
  }
}

/**
 * Parses plain-text payloads.
 * Stores the raw string in payload_text and a line/character count in payload_json.
 */
class TextStreamParser extends BaseStreamParser {
  constructor() {
    super("text_parser", ["txt"]);
  }

  /** @param {{payload: *, format: string, contentType: string}} options */
  parse({ payload, format, contentType }) {
    const text = this.normalizeTextPayload(payload);
    if (!text.trim()) {
      throw new StreamValidationError("Text payload is required.");
    }

    const lines = text.split(/\r?\n/);

    return this.finalizeResult({
      format,
      contentType,
      payload,
      payload_json: {
        line_count: lines.length,
        character_count: text.length,
      },
      payload_text: text,
      record_count: lines.filter((line) => line.trim().length > 0).length || 1,
      structure_kind: "unstructured",
    });
  }
}

/**
 * Parses binary payloads (XLS, XLSX, and raw binary).
 * Encodes the raw bytes as Base64 and stores metadata in payload_json.
 */
class SpreadsheetBinaryParser extends BaseStreamParser {
  constructor() {
    super("spreadsheet_binary_parser", ["xls", "xlsx", "binary"]);
  }

  /** @param {{payload: *, format: string, contentType: string}} options */
  parse({ payload, format, contentType }) {
    const binary = this.normalizeBinaryPayload(payload);
    if (!binary.length) {
      throw new StreamValidationError("Binary payload is required.");
    }

    return this.finalizeResult({
      format,
      contentType,
      payload,
      payload_json: {
        byte_length: binary.length,
        encoding: "base64",
      },
      payload_base64: binary.toString("base64"),
      record_count: 1,
      structure_kind: format === "binary" ? "unstructured" : "structured",
    });
  }
}

/**
 * Parses Twitter API v2 tweet payloads using the Template Method pattern.
 *
 * The parse() method defines a fixed algorithm skeleton: normalise input →
 * call overridable extraction hooks → finalise result. Subclasses can override
 * extractText(), extractMetrics(), and extractEntities() to customise field
 * extraction without duplicating the outer orchestration logic.
 *
 * Classification: semi_structured — tweet text is free-form (unstructured),
 * but public_metrics and entities impose a partial, known schema.
 */
class TweetStreamParser extends BaseStreamParser {
  constructor() {
    super("tweet_parser", ["tweet"]);
  }

  /**
   * Template Method — orchestrates the tweet parsing algorithm.
   * Delegates field extraction to the three protected hook methods below.
   *
   * @param {{payload: *, format: string, contentType: string}} options
   * @returns {object} Normalised parse result.
   */
  parse({ payload, format, contentType }) {
    const tweet = typeof payload === "string" ? JSON.parse(payload) : payload;
    if (!tweet || !tweet.id || !tweet.text) {
      throw new StreamValidationError(
        "Tweet payload must contain id and text."
      );
    }

    const text = this.extractText(tweet);
    const metrics = this.extractMetrics(tweet);
    const entities = this.extractEntities(tweet);

    return this.finalizeResult({
      format,
      contentType,
      payload,
      payload_json: {
        tweet_id: tweet.id,
        author_id: tweet.author_id ?? null,
        created_at: tweet.created_at ?? null,
        text,
        metrics,
        entities,
      },
      payload_text: text,
      record_count: 1,
      structure_kind: "semi_structured",
    });
  }

  /**
   * Hook — extracts the tweet text body.
   * Override in a subclass to apply preprocessing (e.g., stripping URLs).
   *
   * @param {object} tweet - Raw Twitter API v2 tweet object.
   * @returns {string}
   */
  extractText(tweet) {
    return tweet.text ?? "";
  }

  /**
   * Hook — extracts engagement metrics from the public_metrics field.
   * Returns a zero-value object when public_metrics is absent.
   *
   * @param {object} tweet - Raw Twitter API v2 tweet object.
   * @returns {object}
   */
  extractMetrics(tweet) {
    return (
      tweet.public_metrics ?? {
        retweet_count: 0,
        like_count: 0,
        reply_count: 0,
        quote_count: 0,
      }
    );
  }

  /**
   * Hook — extracts hashtags, mentions, and expanded URLs from tweet entities.
   * Returns empty arrays when the entities field is absent.
   *
   * @param {object} tweet - Raw Twitter API v2 tweet object.
   * @returns {object}
   */
  extractEntities(tweet) {
    return {
      hashtags: tweet.entities?.hashtags?.map((h) => h.tag) ?? [],
      mentions: tweet.entities?.mentions?.map((m) => m.username) ?? [],
      urls: tweet.entities?.urls?.map((u) => u.expanded_url) ?? [],
    };
  }
}

/** Default parser registry — one instance per supported format group. */
const DEFAULT_PARSERS = [
  new JsonStreamParser(),
  new CsvStreamParser(),
  new XmlStreamParser(),
  new TextStreamParser(),
  new SpreadsheetBinaryParser(),
  new TweetStreamParser(),
];

/**
 * Factory that selects the appropriate stream parser for a given format.
 *
 * Implements the Factory pattern: the StreamIngestionFacade and route handlers
 * depend on this abstraction rather than instantiating concrete parsers directly.
 * New formats can be added by registering additional parser instances in the
 * constructor without modifying existing code.
 */
export class StreamParserFactory {
  /**
   * @param {BaseStreamParser[]} parsers - Ordered list of parser instances.
   */
  constructor(parsers = DEFAULT_PARSERS) {
    this.parsers = parsers;
  }

  /**
   * Returns the first parser that declares support for the given format.
   *
   * @param {string} format - Canonical format string (e.g., 'json', 'csv').
   * @returns {BaseStreamParser} Matching parser instance.
   * @throws {StreamValidationError} If no registered parser supports the format.
   */
  getParser(format) {
    const parser = this.parsers.find((candidate) => candidate.supports(format));
    if (!parser) {
      throw new StreamValidationError(`Unsupported stream format: ${format}`);
    }
    return parser;
  }

  /**
   * Returns a flat list of all canonical format strings supported by registered parsers.
   *
   * @returns {string[]}
   */
  supportedFormats() {
    return this.parsers.flatMap((parser) => Array.from(parser.formats));
  }
}

/** Shared factory instance used by the default StreamIngestionFacade. */
export const defaultStreamParserFactory = new StreamParserFactory();
