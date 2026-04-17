/**
 * Streams Route — /api/streams
 *
 * Provides endpoints for the generic stream ingestion pipeline (Task 2.5)
 * and the Twitter/X live tweet ingestion pipeline (Task 2.6):
 *
 *   GET  /api/streams/health         — Generic ingestion health and format list.
 *   GET  /api/streams/events         — Lists recent stream_ingestion_events records.
 *   POST /api/streams/ingest         — Accepts and persists any supported format.
 *   GET  /api/streams/tweet/health   — Tweet-specific ingestion health metadata.
 *   POST /api/streams/tweet/ingest   — Validates and ingests a Twitter API v2 tweet.
 *
 * The router registers format-specific body parsers for text and binary content
 * types before the route handlers run, ensuring the raw payload is available
 * on req.body regardless of content type. JSON payloads are handled by the
 * global express.json() middleware registered in index.js.
 *
 * Design patterns applied:
 *   Facade               — route handlers delegate to StreamIngestionFacade.
 *   Chain of Responsibility — tweetValidationChain validates tweet fields.
 *   Builder              — TweetEnvelopeBuilder constructs the ingest envelope.
 */

import express from "express";
import { hasDbConfig } from "../database/index.js";
import { parseBoolean, getDbOrError } from "../utils/task2_2.js";
import { parseLimit, parseString } from "../utils/query.js";
import {
  buildEnvelopeFromRequest,
  MAX_STREAM_BODY_BYTES,
} from "../utils/streaming.js";
import {
  streamIngestionFacade,
  StreamValidationError,
  TweetEnvelopeBuilder,
  createTweetValidationChain,
} from "../services/streams/streamIngestionFacade.js";
import { tweetSignatureMiddleware } from "../middleware/tweetSignature.js";

const router = express.Router();

/**
 * Singleton validation chain for tweet ingestion — created once at module
 * load so the Chain of Responsibility nodes are not re-allocated per request.
 */
const tweetValidationChain = createTweetValidationChain();

// Body parser for text-based formats (plain text, XML, CSV sent as text)
router.use(
  express.text({
    type: [
      "text/*",
      "application/xml",
      "text/xml",
      "application/csv",
      "application/*+xml",
    ],
    limit: MAX_STREAM_BODY_BYTES,
  })
);

// Body parser for binary formats (octet-stream, XLS, XLSX)
router.use(
  express.raw({
    type: [
      "application/octet-stream",
      "application/vnd.ms-excel",
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ],
    limit: MAX_STREAM_BODY_BYTES,
  })
);

/**
 * GET /api/streams/health
 * Returns a snapshot of the stream ingestion configuration including
 * supported formats and database availability.
 */
router.get("/health", (req, res) => {
  res.json({
    data: {
      route: "/api/streams",
      database_configured: hasDbConfig,
      max_body_bytes: MAX_STREAM_BODY_BYTES,
      ...streamIngestionFacade.getHealthSnapshot(),
    },
  });
});

/**
 * GET /api/streams/events
 * Returns recent stream ingestion event records. Payload columns are
 * excluded by default and must be requested explicitly via include_payload.
 */
router.get("/events", async (req, res) => {
  const db = getDbOrError(res);
  if (!db) return;

  try {
    const rows = await streamIngestionFacade.listRecent({
      source: parseString(req.query.source),
      format: parseString(req.query.format),
      structureKind: parseString(req.query.structure_kind),
      includePayload: parseBoolean(req.query.include_payload) ?? false,
      limit: parseLimit(req.query.limit, 20, 100),
    });

    return res.json({ data: rows });
  } catch (error) {
    console.error("Failed to list stream events", error);
    return res.status(500).json({ error: "Failed to list stream events" });
  }
});

/**
 * POST /api/streams/ingest
 * Accepts a streaming payload and persists it via the StreamIngestionFacade.
 * Returns 201 with the created record on success, or 400 for validation errors.
 *
 * The facade (Facade pattern) orchestrates format inference, parser selection,
 * payload parsing, and database persistence behind this single endpoint.
 */
router.post("/ingest", async (req, res) => {
  const db = getDbOrError(res);
  if (!db) return;

  try {
    const record = await streamIngestionFacade.ingest(buildEnvelopeFromRequest(req));
    return res.status(201).json({ data: record });
  } catch (error) {
    if (error instanceof StreamValidationError || error instanceof SyntaxError) {
      return res.status(400).json({ error: error.message });
    }

    console.error("Failed to ingest stream payload", error);
    return res.status(500).json({ error: "Failed to ingest stream payload" });
  }
});

/**
 * GET /api/streams/tweet/health
 * Returns the tweet-specific ingestion endpoint configuration including
 * the expected format, structure classification, and validation chain nodes.
 */
router.get("/tweet/health", (req, res) => {
  res.json({
    data: {
      route: "/api/streams/tweet",
      database_configured: hasDbConfig,
      format: "tweet",
      structure_kind: "semi_structured",
      validation_chain: ["required_fields", "text_length", "timestamp"],
    },
  });
});

/**
 * POST /api/streams/tweet/ingest
 * Accepts a Twitter API v2 tweet JSON payload, validates it through the
 * Chain of Responsibility, constructs the ingest envelope via the Builder,
 * and delegates persistence to StreamIngestionFacade (Facade pattern).
 *
 * Request body fields (Twitter API v2):
 *   id          {string}  Required — tweet snowflake ID.
 *   text        {string}  Required — tweet body text (max 280 chars).
 *   author_id   {string}  Optional — author snowflake ID.
 *   created_at  {string}  Optional — ISO 8601 timestamp.
 *   public_metrics {object} Optional — retweet_count, like_count, etc.
 *   entities    {object}  Optional — hashtags, mentions, urls arrays.
 *
 * Optional headers / query params:
 *   x-source       / source      — upstream source label (default: 'twitter').
 *   stream_name                  — stream group label (default: 'tweets').
 */
router.post("/tweet/ingest", tweetSignatureMiddleware, async (req, res) => {
  const db = getDbOrError(res);
  if (!db) return;

  try {
    const tweet = req.body;

    // Chain of Responsibility: validate required fields → text length → timestamp
    tweetValidationChain.validate(tweet);

    // Builder: construct the standard ingest envelope from raw tweet data.
    // Non-repudiation: source_ip and user_agent are stored in metadata to
    // create an audit trail proving who sent the payload and when.
    const envelope = new TweetEnvelopeBuilder()
      .withTweet(tweet)
      .withSource(
        parseString(req.headers["x-source"]) ??
          parseString(req.query.source) ??
          "twitter"
      )
      .withStreamName(parseString(req.query.stream_name) ?? "tweets")
      .withMetadata({
        ingested_via: "tweet_route",
        source_ip: req.ip ?? null,
        user_agent: parseString(req.headers["user-agent"]) ?? null,
      })
      .build();

    // Facade: delegate the full ingestion pipeline to StreamIngestionFacade
    const record = await streamIngestionFacade.ingest(envelope);
    return res.status(201).json({ data: record });
  } catch (error) {
    if (error instanceof StreamValidationError) {
      return res.status(400).json({ error: error.message });
    }
    console.error("Failed to ingest tweet payload", error);
    return res.status(500).json({ error: "Failed to ingest tweet payload" });
  }
});

export default router;
