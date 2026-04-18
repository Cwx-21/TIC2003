# Task 2.6 Testing Guide (Twitter/X Live Tweet Stream Ingestion)

This guide verifies the Twitter/X tweet ingestion route built on top of the Task 2.5 streaming infrastructure, using four additional design patterns: Template Method, Chain of Responsibility, Builder, and Decorator.

## 0) Technical Workflow (Task 2.6)

1. Start PostgreSQL and initialize the schema.
2. Start the API with `DATABASE_URL` pointing at the local Postgres instance.
3. Verify `/api/streams/tweet/health` reports the tweet endpoint configuration.
4. Verify `/api/streams/tweet/ingest` accepts and persists a Twitter API v2 tweet payload.
5. Verify `/api/streams/events?format=tweet` returns the ingested tweet records.
6. Run the unit tests that validate all four Task 2.6 design patterns.

## 1) Prerequisite: Database + API Running

### Start PostgreSQL (Docker)

```bash
docker compose up -d postgres
```

### Initialize Schema (one-time)

```bash
docker compose run --rm etl python -c "from db import init_db; init_db()"
```

### Start API (local)

```bash
DATABASE_URL=postgres://user:password@localhost:5432/hypecheck npm run dev:api
```

Expected: API listens on `http://localhost:3000`.

## 2) CLI Tests (curl)

### Tweet endpoint health check

```bash
curl -s "http://localhost:3000/api/streams/tweet/health" | jq
```

Expected response:

```json
{
  "data": {
    "route": "/api/streams/tweet",
    "database_configured": true,
    "format": "tweet",
    "structure_kind": "semi_structured",
    "validation_chain": ["required_fields", "text_length", "timestamp"]
  }
}
```

### Ingest a minimal tweet (id + text only)

```bash
curl -s -X POST "http://localhost:3000/api/streams/tweet/ingest" \
  -H "Content-Type: application/json" \
  -d '{"id":"1001","text":"BTC looking bullish today"}' | jq
```

### Ingest a full Twitter API v2 tweet payload

```bash
curl -s -X POST "http://localhost:3000/api/streams/tweet/ingest" \
  -H "Content-Type: application/json" \
  -H "x-source: twitter-stream" \
  -d '{
    "id": "1234567890",
    "text": "Bitcoin is going to the moon! #BTC #crypto",
    "author_id": "987654321",
    "created_at": "2026-04-06T00:00:00.000Z",
    "public_metrics": {
      "retweet_count": 5,
      "like_count": 23,
      "reply_count": 2,
      "quote_count": 1
    },
    "entities": {
      "hashtags": [{"tag": "BTC"}, {"tag": "crypto"}],
      "mentions": [],
      "urls": []
    }
  }' | jq
```

Expected response:

```json
{
  "data": {
    "id": 1,
    "source": "twitter-stream",
    "stream_name": "tweets",
    "format": "tweet",
    "structure_kind": "semi_structured",
    "parser_key": "tweet_parser",
    "record_count": 1,
    "status": "accepted"
  }
}
```

### Ingest with custom source and stream_name

```bash
curl -s -X POST "http://localhost:3000/api/streams/tweet/ingest?stream_name=wsb-tweets" \
  -H "Content-Type: application/json" \
  -H "x-source: wsb-monitor" \
  -d '{"id":"9999","text":"GME is mooning #GME","author_id":"555"}' | jq
```

### Query ingested tweet events

```bash
curl -s "http://localhost:3000/api/streams/events?format=tweet&limit=10" | jq
```

### Query with payload included

```bash
curl -s "http://localhost:3000/api/streams/events?format=tweet&include_payload=true&limit=5" | jq
```

## 3) Validation Chain Tests (Chain of Responsibility)

These verify that the three validation handlers reject invalid input correctly.

### Missing id field — expect 400

```bash
curl -s -X POST "http://localhost:3000/api/streams/tweet/ingest" \
  -H "Content-Type: application/json" \
  -d '{"text":"no id here"}' | jq
```

Expected: `{"error": "Tweet must have id and text fields."}`

### Missing text field — expect 400

```bash
curl -s -X POST "http://localhost:3000/api/streams/tweet/ingest" \
  -H "Content-Type: application/json" \
  -d '{"id":"1"}' | jq
```

Expected: `{"error": "Tweet must have id and text fields."}`

### Text over 280 characters — expect 400

```bash
curl -s -X POST "http://localhost:3000/api/streams/tweet/ingest" \
  -H "Content-Type: application/json" \
  -d "{\"id\":\"1\",\"text\":\"$(python3 -c 'print("x"*281)')\"}" | jq
```

Expected: `{"error": "Tweet text exceeds the 280-character limit."}`

### Invalid created_at timestamp — expect 400

```bash
curl -s -X POST "http://localhost:3000/api/streams/tweet/ingest" \
  -H "Content-Type: application/json" \
  -d '{"id":"1","text":"valid text","created_at":"not-a-date"}' | jq
```

Expected: `{"error": "Tweet created_at is not a valid ISO timestamp."}`

## 4) Unit Tests (all Task 2.5 + Task 2.6)

```bash
npm run test:task2_5 --prefix apps/api
```

### Task 2.6 unit tests validate

| Test | Pattern Verified |
| :--- | :--- |
| `TweetStreamParser extracts tweet fields via Template Method hooks` | Template Method |
| `TweetStreamParser throws on missing id or text` | Template Method + Validation |
| `TweetEnvelopeBuilder produces a valid ingest envelope` | Builder |
| `TweetEnvelopeBuilder throws StreamValidationError when tweet is not set` | Builder |
| `createTweetValidationChain rejects a tweet missing id` | Chain of Responsibility |
| `createTweetValidationChain rejects a tweet with text over 280 characters` | Chain of Responsibility |
| `createTweetValidationChain rejects a tweet with an invalid created_at timestamp` | Chain of Responsibility |
| `createTweetValidationChain passes a well-formed tweet through all handlers` | Chain of Responsibility |
| `RetryingStreamIngestionFacade retries on transient error and succeeds` | Decorator |
| `RetryingStreamIngestionFacade does not retry StreamValidationError` | Decorator |

## 5) Design Patterns Reference

| Pattern | Class / Function | Location |
| :------------------------ | :------------------------------------------------------------------------------------------------- | :------------------------------------------- |
| **Template Method** | `TweetStreamParser` — `parse()` skeleton calls `extractText()`, `extractMetrics()`, `extractEntities()` hooks | `apps/api/services/streams/streamParsers.js` |
| **Chain of Responsibility** | `TweetRequiredFieldsValidator → TweetTextLengthValidator → TweetTimestampValidator` | `apps/api/services/streams/streamIngestionFacade.js` |
| **Builder** | `TweetEnvelopeBuilder` — fluent `.withTweet().withSource().withStreamName().build()` | `apps/api/services/streams/streamIngestionFacade.js` |
| **Decorator** | `RetryingStreamIngestionFacade` — wraps any facade with exponential-backoff retry | `apps/api/services/streams/streamIngestionFacade.js` |

## 6) Payload Structure

Tweet events are stored as `structure_kind = semi_structured`:

- `payload_json` — extracted fields: `tweet_id`, `author_id`, `created_at`, `text`, `metrics`, `entities`
- `payload_text` — raw tweet text string
- `parser_key` — always `tweet_parser`

## 7) Task 2.6 Modified Files

All Task 2.6 code was integrated into existing files (no new source files added):

- `apps/api/services/streams/streamParsers.js` — `TweetStreamParser` (Template Method)
- `apps/api/services/streams/streamIngestionFacade.js` — Builder, Chain of Responsibility, Decorator
- `apps/api/routes/streams.js` — `GET /tweet/health`, `POST /tweet/ingest`
- `apps/api/utils/streaming.js` — `tweet` format registered in aliases and structure map
- `apps/api/tests/task_2_5.unit.test.js` — 9 new unit tests for Task 2.6 patterns
