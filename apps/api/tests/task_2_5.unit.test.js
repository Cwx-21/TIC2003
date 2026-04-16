import test from "node:test";
import assert from "node:assert/strict";
import { createHmac } from "node:crypto";
import {
  StreamParserFactory,
  StreamValidationError,
} from "../services/streams/streamParsers.js";
import {
  StreamIngestionFacade,
  TweetEnvelopeBuilder,
  createTweetValidationChain,
  RetryingStreamIngestionFacade,
} from "../services/streams/streamIngestionFacade.js";
import { computePayloadHash, verifyHmacSignature } from "../utils/crypto.js";

test("StreamParserFactory selects the CSV parser and parses rows", () => {
  const factory = new StreamParserFactory();
  const parser = factory.getParser("csv");
  const result = parser.parse({
    payload: "symbol,price\nBTC,65000\nETH,3000",
    format: "csv",
    contentType: "text/csv",
  });

  assert.equal(parser.key, "csv_parser");
  assert.equal(result.record_count, 2);
  assert.deepEqual(result.payload_json.headers, ["symbol", "price"]);
  assert.deepEqual(result.payload_json.rows[0], {
    symbol: "BTC",
    price: "65000",
  });
});

test("StreamIngestionFacade persists normalized JSON ingestion records", async () => {
  const persisted = [];
  const repository = {
    async create(record) {
      const saved = { id: persisted.length + 1, ...record };
      persisted.push(saved);
      return {
        toJSON() {
          return saved;
        },
      };
    },
  };

  const facade = new StreamIngestionFacade({ repository });
  const result = await facade.ingest({
    source: "unit-test",
    streamName: "task-2-5",
    format: "json",
    contentType: "application/json",
    metadata: { test_case: "json" },
    payload: [{ asset: "BTC", score: 0.82 }],
  });

  assert.equal(result.id, 1);
  assert.equal(result.source, "unit-test");
  assert.equal(result.stream_name, "task-2-5");
  assert.equal(result.format, "json");
  assert.equal(result.structure_kind, "structured");
  assert.equal(result.record_count, 1);
  assert.deepEqual(result.payload_json, [{ asset: "BTC", score: 0.82 }]);
});

test("StreamIngestionFacade rejects records without a source", async () => {
  const facade = new StreamIngestionFacade({
    repository: {
      async create() {
        throw new Error("should not be called");
      },
    },
  });

  await assert.rejects(
    () =>
      facade.ingest({
        contentType: "text/plain",
        payload: "missing source",
      }),
    StreamValidationError
  );
});

// ─── Task 2.6: Twitter/X Tweet Ingestion Tests ────────────────────────────────

test("TweetStreamParser extracts tweet fields via Template Method hooks", () => {
  const factory = new StreamParserFactory();
  const parser = factory.getParser("tweet");
  const tweet = {
    id: "123456789",
    text: "Bitcoin is mooning #BTC",
    author_id: "987654321",
    created_at: "2026-04-06T00:00:00.000Z",
    public_metrics: {
      retweet_count: 5,
      like_count: 23,
      reply_count: 2,
      quote_count: 1,
    },
    entities: {
      hashtags: [{ tag: "BTC" }],
      mentions: [],
      urls: [],
    },
  };

  const result = parser.parse({
    payload: tweet,
    format: "tweet",
    contentType: "application/json",
  });

  assert.equal(parser.key, "tweet_parser");
  assert.equal(result.structure_kind, "semi_structured");
  assert.equal(result.record_count, 1);
  assert.equal(result.payload_json.tweet_id, "123456789");
  assert.equal(result.payload_json.text, "Bitcoin is mooning #BTC");
  assert.deepEqual(result.payload_json.entities.hashtags, ["BTC"]);
  assert.equal(result.payload_json.metrics.like_count, 23);
  assert.equal(result.payload_text, "Bitcoin is mooning #BTC");
});

test("TweetStreamParser throws on missing id or text", () => {
  const factory = new StreamParserFactory();
  const parser = factory.getParser("tweet");

  assert.throws(
    () =>
      parser.parse({
        payload: { text: "no id here" },
        format: "tweet",
        contentType: "application/json",
      }),
    StreamValidationError
  );
});

test("TweetEnvelopeBuilder produces a valid ingest envelope", () => {
  const tweet = { id: "111", text: "ETH gas fees are high", author_id: "222" };
  const envelope = new TweetEnvelopeBuilder()
    .withTweet(tweet)
    .withSource("twitter-stream")
    .withStreamName("crypto-tweets")
    .withMetadata({ region: "sg" })
    .build();

  assert.equal(envelope.source, "twitter-stream");
  assert.equal(envelope.streamName, "crypto-tweets");
  assert.equal(envelope.format, "tweet");
  assert.equal(envelope.metadata.tweet_id, "111");
  assert.equal(envelope.metadata.region, "sg");
  assert.deepEqual(envelope.payload, tweet);
});

test("TweetEnvelopeBuilder throws StreamValidationError when tweet is not set", () => {
  assert.throws(() => new TweetEnvelopeBuilder().build(), StreamValidationError);
});

test("createTweetValidationChain rejects a tweet missing id", () => {
  const chain = createTweetValidationChain();
  assert.throws(
    () => chain.validate({ text: "no id here" }),
    StreamValidationError
  );
});

test("createTweetValidationChain rejects a tweet with text over 280 characters", () => {
  const chain = createTweetValidationChain();
  assert.throws(
    () => chain.validate({ id: "1", text: "x".repeat(281) }),
    StreamValidationError
  );
});

test("createTweetValidationChain rejects a tweet with an invalid created_at timestamp", () => {
  const chain = createTweetValidationChain();
  assert.throws(
    () =>
      chain.validate({ id: "1", text: "valid text", created_at: "not-a-date" }),
    StreamValidationError
  );
});

test("createTweetValidationChain passes a well-formed tweet through all handlers", () => {
  const chain = createTweetValidationChain();
  assert.doesNotThrow(() =>
    chain.validate({
      id: "999",
      text: "GME to the moon!",
      created_at: "2026-04-06T00:00:00.000Z",
    })
  );
});

test("RetryingStreamIngestionFacade retries on transient error and succeeds", async () => {
  let calls = 0;
  const unstableFacade = {
    async ingest(envelope) {
      calls += 1;
      if (calls < 3) throw new Error("transient DB timeout");
      return { id: 42, source: envelope.source };
    },
    listRecent: () => [],
    getHealthSnapshot: () => ({}),
  };

  const retrying = new RetryingStreamIngestionFacade(unstableFacade, 3, 0);
  const result = await retrying.ingest({ source: "test" });

  assert.equal(result.id, 42);
  assert.equal(calls, 3);
});

test("RetryingStreamIngestionFacade does not retry StreamValidationError", async () => {
  let calls = 0;
  const facade = {
    async ingest() {
      calls += 1;
      throw new StreamValidationError("bad input — do not retry");
    },
  };

  const retrying = new RetryingStreamIngestionFacade(facade, 3, 0);
  await assert.rejects(() => retrying.ingest({}), StreamValidationError);
  assert.equal(calls, 1);
});

// ─── Task 2.7: CIA Security & Non-Repudiation Tests ──────────────────────────

test("computePayloadHash returns a 64-character hex SHA-256 digest", () => {
  const hash = computePayloadHash({ asset: "BTC", score: 0.9 });
  assert.equal(typeof hash, "string");
  assert.equal(hash.length, 64);
  assert.match(hash, /^[0-9a-f]{64}$/);
});

test("computePayloadHash is deterministic for identical inputs", () => {
  const input = { id: "1", text: "BTC to the moon" };
  assert.equal(computePayloadHash(input), computePayloadHash(input));
});

test("computePayloadHash produces different digests for different inputs", () => {
  assert.notEqual(
    computePayloadHash({ text: "BTC" }),
    computePayloadHash({ text: "ETH" })
  );
});

test("verifyHmacSignature returns true for a valid HMAC-SHA256 signature", () => {
  const secret = "test-secret";
  const payload = '{"id":"1","text":"BTC pumping"}';
  const signature = createHmac("sha256", secret).update(payload).digest("hex");
  assert.equal(verifyHmacSignature(secret, payload, signature), true);
});

test("verifyHmacSignature returns false for a tampered payload", () => {
  const secret = "test-secret";
  const original = '{"id":"1","text":"BTC pumping"}';
  const tampered = '{"id":"1","text":"ETH pumping"}';
  const signature = createHmac("sha256", secret).update(original).digest("hex");
  assert.equal(verifyHmacSignature(secret, tampered, signature), false);
});

test("verifyHmacSignature returns false for a wrong secret", () => {
  const payload = '{"id":"1","text":"BTC pumping"}';
  const signature = createHmac("sha256", "correct-secret").update(payload).digest("hex");
  assert.equal(verifyHmacSignature("wrong-secret", payload, signature), false);
});

test("StreamIngestionFacade stores a 64-char payload_hash in the persisted record", async () => {
  const persisted = [];
  const repository = {
    async create(record) {
      const saved = { id: 1, ...record };
      persisted.push(saved);
      return { toJSON() { return saved; } };
    },
  };

  const facade = new StreamIngestionFacade({ repository });
  await facade.ingest({
    source: "unit-test-hash",
    format: "json",
    contentType: "application/json",
    payload: { asset: "BTC", score: 0.9 },
  });

  const record = persisted[0];
  assert.equal(typeof record.payload_hash, "string");
  assert.equal(record.payload_hash.length, 64);
  assert.match(record.payload_hash, /^[0-9a-f]{64}$/);
});
