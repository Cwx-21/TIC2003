/**
 * Stream Ingestion Facade
 *
 * Implements the Facade design pattern to provide a single, simplified entry
 * point (ingest()) that coordinates the full stream ingestion workflow:
 *
 *   1. Validation     — ensures required envelope fields are present.
 *   2. Normalisation  — resolves canonical format and content-type strings.
 *   3. Parser Selection — delegates to StreamParserFactory.getParser() (Factory pattern).
 *   4. Payload Parsing  — invokes the selected parser's parse() method (Strategy pattern).
 *   5. Persistence    — delegates database insertion to StreamEventRepository (Repository pattern).
 *
 * By centralising these steps behind ingest(), route handlers remain format-agnostic
 * and free of parsing or persistence logic. The facade also exposes listRecent()
 * for querying ingested events and getHealthSnapshot() for the health endpoint.
 *
 * Dependencies are injected via the constructor to support unit testing with
 * alternative parsers or repository implementations.
 */

import { parseString } from "../../utils/query.js";
import {
  inferFormat,
  inferStructureKind,
  normalizeContentType,
  normalizeMetadata,
} from "../../utils/streaming.js";
import { computePayloadHash } from "../../utils/crypto.js";
import {
  defaultStreamParserFactory,
  StreamValidationError,
} from "./streamParsers.js";
import { streamEventRepository } from "./streamEventRepository.js";

/**
 * Facade that orchestrates stream payload ingestion end-to-end.
 *
 * Accepts an envelope object (source, format, payload, metadata, etc.) and
 * returns the persisted database record. Validation errors are surfaced as
 * StreamValidationError so route handlers can return appropriate HTTP 400
 * responses without inspecting internal state.
 */
export class StreamIngestionFacade {
  /**
   * @param {object} [options]
   * @param {import('./streamParsers').StreamParserFactory} [options.parserFactory]
   *   - Parser factory to use for format resolution. Defaults to the shared instance.
   * @param {import('./streamEventRepository').StreamEventRepository} [options.repository]
   *   - Repository for persisting events. Defaults to the shared instance.
   */
  constructor({
    parserFactory = defaultStreamParserFactory,
    repository = streamEventRepository,
  } = {}) {
    this.parserFactory = parserFactory;
    this.repository = repository;
  }

  /**
   * Validates, parses, and persists a stream ingestion event.
   *
   * Coordinates the full pipeline: envelope validation → format normalisation →
   * parser selection (Factory) → payload parsing (Strategy) → DB persistence (Repository).
   *
   * @param {object} envelope - Normalised request envelope from buildEnvelopeFromRequest().
   * @param {string} envelope.source - Required data source identifier.
   * @param {string} [envelope.streamName] - Stream name label (defaults to 'default').
   * @param {string} [envelope.format] - Explicit format override.
   * @param {string} [envelope.structureKind] - Explicit structure classification override.
   * @param {string} [envelope.contentType] - Raw Content-Type header value.
   * @param {object} [envelope.metadata] - Arbitrary key-value metadata.
   * @param {*} envelope.payload - Raw request body payload.
   *
   * @returns {Promise<object>} The created stream_ingestion_events record as a plain object.
   * @throws {StreamValidationError} If source is missing or the format is unsupported.
   * @throws {SyntaxError} If a JSON payload cannot be parsed.
   */
  async ingest({
    source,
    streamName,
    format,
    structureKind,
    contentType,
    metadata,
    payload,
  }) {
    const normalizedSource = parseString(source);
    if (!normalizedSource) {
      throw new StreamValidationError("Stream source is required.");
    }

    const normalizedStreamName = parseString(streamName) ?? "default";
    const normalizedContentType = normalizeContentType(contentType);
    const normalizedFormat = inferFormat({
      requestedFormat: format,
      contentType: normalizedContentType,
    });

    // Factory pattern: parser selection is delegated to the factory
    const parser = this.parserFactory.getParser(normalizedFormat);

    // Strategy pattern: each parser encapsulates its own parsing algorithm
    const parsedPayload = parser.parse({
      payload,
      format: normalizedFormat,
      contentType: normalizedContentType,
    });

    // Non-repudiation: SHA-256 digest of the raw payload proves what was received
    const payloadHash = computePayloadHash(payload);

    // Repository pattern: persistence is encapsulated in the repository
    const record = await this.repository.create({
      source: normalizedSource,
      stream_name: normalizedStreamName,
      format: normalizedFormat,
      content_type: normalizedContentType,
      structure_kind: inferStructureKind(
        normalizedFormat,
        structureKind ?? parsedPayload.structure_kind
      ),
      parser_key: parsedPayload.parser_key,
      payload_json: parsedPayload.payload_json ?? null,
      payload_text: parsedPayload.payload_text ?? null,
      payload_base64: parsedPayload.payload_base64 ?? null,
      payload_hash: payloadHash,
      metadata: normalizeMetadata(metadata),
      original_size_bytes: parsedPayload.original_size_bytes,
      record_count: parsedPayload.record_count ?? 1,
      status: "accepted",
      received_at: new Date(),
    });

    return record.toJSON ? record.toJSON() : record;
  }

  /**
   * Returns recent stream ingestion events matching the given filters.
   *
   * @param {object} options
   * @param {string|null} options.source - Filter by source identifier.
   * @param {string|null} options.format - Filter by canonical format string.
   * @param {string|null} options.structureKind - Filter by structure classification.
   * @param {boolean} options.includePayload - Whether to include payload columns.
   * @param {number} options.limit - Maximum number of rows to return.
   *
   * @returns {Promise<object[]>} Array of plain event objects.
   */
  async listRecent({ source, format, structureKind, includePayload, limit }) {
    const rows = await this.repository.listRecent({
      source: parseString(source) ?? undefined,
      format: parseString(format) ?? undefined,
      structure_kind: parseString(structureKind) ?? undefined,
      includePayload,
      limit,
    });

    return rows.map((row) => (row.toJSON ? row.toJSON() : row));
  }

  /**
   * Returns a health snapshot describing supported formats and parser count.
   * Consumed by the GET /api/streams/health endpoint.
   *
   * @returns {{supported_formats: string[], parser_count: number}}
   */
  getHealthSnapshot() {
    const supported_formats = this.parserFactory.supportedFormats();
    return {
      supported_formats,
      parser_count: supported_formats.length,
    };
  }
}

/** Shared facade instance used by the streams route handler. */
export const streamIngestionFacade = new StreamIngestionFacade();
export { StreamValidationError };

// ─── Task 2.6: Twitter/X Live Tweet Ingestion ────────────────────────────────

/**
 * Tweet Validation Handler — Chain of Responsibility Pattern (Abstract)
 *
 * Defines the abstract handler node for the tweet validation chain.
 * Each concrete handler validates one concern and delegates to the next
 * handler in the chain, or throws StreamValidationError to short-circuit.
 * This decouples validation rules from each other and from the route handler.
 */
class TweetValidationHandler {
  /**
   * Links the next handler in the chain and returns it for fluent chaining.
   *
   * @param {TweetValidationHandler} handler - The successor handler.
   * @returns {TweetValidationHandler}
   */
  setNext(handler) {
    this._next = handler;
    return handler;
  }

  /**
   * Validates the tweet and passes it to the next handler.
   *
   * @param {object} tweet - Raw tweet data object.
   */
  validate(tweet) {
    if (this._next) {
      this._next.validate(tweet);
    }
  }
}

/** Concrete handler — checks that id and text fields are present. */
class TweetRequiredFieldsValidator extends TweetValidationHandler {
  validate(tweet) {
    if (!tweet || !tweet.id || !tweet.text) {
      throw new StreamValidationError(
        "Tweet must have id and text fields."
      );
    }
    super.validate(tweet);
  }
}

/** Concrete handler — checks that tweet text does not exceed 280 characters. */
class TweetTextLengthValidator extends TweetValidationHandler {
  validate(tweet) {
    if (tweet.text && tweet.text.length > 280) {
      throw new StreamValidationError(
        "Tweet text exceeds the 280-character limit."
      );
    }
    super.validate(tweet);
  }
}

/** Concrete handler — checks that created_at is a parseable ISO timestamp. */
class TweetTimestampValidator extends TweetValidationHandler {
  validate(tweet) {
    if (tweet.created_at && Number.isNaN(Date.parse(tweet.created_at))) {
      throw new StreamValidationError(
        "Tweet created_at is not a valid ISO timestamp."
      );
    }
    super.validate(tweet);
  }
}

/**
 * Wires the three tweet validators into a single chain and returns the head.
 * Callers invoke chain.validate(tweet) to run all rules in sequence.
 *
 * Chain order: RequiredFields → TextLength → Timestamp
 *
 * @returns {TweetValidationHandler} Head of the validation chain.
 */
export const createTweetValidationChain = () => {
  const required = new TweetRequiredFieldsValidator();
  const textLength = new TweetTextLengthValidator();
  const timestamp = new TweetTimestampValidator();
  required.setNext(textLength).setNext(timestamp);
  return required;
};

/**
 * Tweet Envelope Builder — Builder Pattern
 *
 * Constructs the normalised StreamIngestionFacade envelope from a raw
 * Twitter API v2 tweet object using a fluent method-chaining interface.
 * Separating envelope construction from ingestion keeps the route handler
 * free of field-mapping logic and makes the builder independently testable.
 */
export class TweetEnvelopeBuilder {
  constructor() {
    this._source = "twitter";
    this._streamName = "tweets";
    this._metadata = {};
    this._tweet = null;
  }

  /**
   * Sets the raw tweet object to build the envelope from.
   *
   * @param {object} tweet - Twitter API v2 tweet object.
   * @returns {this}
   */
  withTweet(tweet) {
    this._tweet = tweet;
    return this;
  }

  /**
   * Sets the upstream source identifier stored in stream_ingestion_events.
   *
   * @param {string} source - Source label (e.g., 'twitter-stream').
   * @returns {this}
   */
  withSource(source) {
    this._source = source;
    return this;
  }

  /**
   * Sets the logical stream name for grouping related events.
   *
   * @param {string} name - Stream name label (e.g., 'crypto-tweets').
   * @returns {this}
   */
  withStreamName(name) {
    this._streamName = name;
    return this;
  }

  /**
   * Merges additional metadata key-value pairs into the envelope.
   *
   * @param {object} meta - Arbitrary key-value pairs.
   * @returns {this}
   */
  withMetadata(meta) {
    this._metadata = { ...this._metadata, ...meta };
    return this;
  }

  /**
   * Builds and returns the completed ingest envelope.
   *
   * @returns {object} Normalised envelope for StreamIngestionFacade.ingest().
   * @throws {StreamValidationError} If withTweet() was not called before build().
   */
  build() {
    if (!this._tweet) {
      throw new StreamValidationError(
        "Tweet data is required to build the envelope."
      );
    }
    return {
      source: this._source,
      streamName: this._streamName,
      format: "tweet",
      contentType: "application/json",
      metadata: {
        ...this._metadata,
        tweet_id: this._tweet.id,
        author_id: this._tweet.author_id ?? null,
      },
      payload: this._tweet,
    };
  }
}

/**
 * Retrying Stream Ingestion Facade — Decorator Pattern
 *
 * Wraps any StreamIngestionFacade-compatible instance and transparently
 * retries transient database errors with exponential backoff. Validation
 * errors (StreamValidationError) and syntax errors are not retried because
 * repeating them would always yield the same failure.
 *
 * This decorator conforms to the same interface as StreamIngestionFacade,
 * so it can be stacked with other decorators or swapped in transparently.
 */
export class RetryingStreamIngestionFacade {
  /**
   * @param {StreamIngestionFacade} facade - The wrapped facade instance.
   * @param {number} [maxRetries=3] - Maximum number of retry attempts.
   * @param {number} [baseDelayMs=100] - Initial backoff delay in milliseconds.
   */
  constructor(facade, maxRetries = 3, baseDelayMs = 100) {
    this._facade = facade;
    this._maxRetries = maxRetries;
    this._baseDelayMs = baseDelayMs;
  }

  /**
   * Calls the wrapped facade's ingest() and retries on transient errors.
   * Backoff delay doubles on each attempt: baseDelayMs × 2^(attempt-1).
   *
   * @param {object} envelope - Ingest envelope passed to the inner facade.
   * @returns {Promise<object>} The persisted record from the inner facade.
   */
  async ingest(envelope) {
    let lastError;
    for (let attempt = 1; attempt <= this._maxRetries; attempt += 1) {
      try {
        return await this._facade.ingest(envelope);
      } catch (err) {
        if (err instanceof StreamValidationError || err instanceof SyntaxError) {
          throw err;
        }
        lastError = err;
        if (attempt < this._maxRetries) {
          await new Promise((resolve) =>
            setTimeout(resolve, this._baseDelayMs * 2 ** (attempt - 1))
          );
        }
      }
    }
    throw lastError;
  }

  /**
   * Delegates listRecent() directly to the wrapped facade.
   *
   * @param {object} options - Filter options passed through unchanged.
   * @returns {Promise<object[]>}
   */
  listRecent(options) {
    return this._facade.listRecent(options);
  }

  /**
   * Delegates getHealthSnapshot() directly to the wrapped facade.
   *
   * @returns {object}
   */
  getHealthSnapshot() {
    return this._facade.getHealthSnapshot();
  }
}
