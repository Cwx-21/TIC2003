# HypeCheck — Professor Demo & Testing Guide

> **First-person narrative test walkthrough for Tasks 2.1 – 2.7.**
> Everything below is what I built, how I verify it works, and what each test proves.

---

## 1. System Overview

I built **HypeCheck**, a social-media sentiment vs. financial-price correlation platform.
The system is split into three layers:

| Layer | What I built |
|:------|:------------|
| **ETL Pipeline** (Python) | Ingests Reddit CSV and live Telegram messages; runs VADER NLP; writes to PostgreSQL |
| **REST API** (Node.js / Express) | 9 route groups, Sequelize ORM, 13 design patterns across Tasks 2.1–2.7 |
| **Frontend** (React + Vite) | Real-time dual-axis charts (Price vs. Sentiment) |

---

## 2. Start Everything First

Before any test I start these three services:

```bash
# Terminal 1 — PostgreSQL via Docker
npm run docker:up

# Terminal 2 — Express API (port 3000)
npm run dev:api

# Terminal 3 — React Frontend (port 5173)
npm run dev:web
```

Health check — the API should respond immediately:

```bash
curl -s http://localhost:3000/ | jq
```

Expected: `{ "status": "ok", "message": "HypeCheck API is running" }`

---

## 3. Task 2.1 — Database ORM Models

I defined Sequelize models for all 10 database tables so the API layer never writes raw SQL.
The models sync automatically when the API starts.

**Verify the sync worked (check API startup log):**

```
✔  PostgreSQL connected
✔  Sequelize sync complete (10 models)
```

**Directly query the database to confirm tables exist:**

```bash
psql postgres://user:password@localhost:5432/hypecheck \
  -c "\dt" | grep -E 'assets|sentiment|prices|stream'
```

---

## 4. Task 2.2 & 2.3 — Core REST Endpoints

I implemented four data endpoints using the **Repository** pattern so route handlers never touch raw SQL.

```bash
# Assets catalogue
curl -s "http://localhost:3000/api/assets" | jq '.data[0]'

# Sentiment for Bitcoin (aggregated from sentiment_aggregations table)
curl -s "http://localhost:3000/api/sentiment/BTC?limit=5" | jq '.data[0]'

# Price history for Tesla
curl -s "http://localhost:3000/api/prices/TSLA?limit=5" | jq '.data[0]'

# Sentiment–price correlation for NVIDIA
curl -s "http://localhost:3000/api/correlation/NVDA?limit=5" | jq '.data[0]'
```

Each returns structured JSON; empty array if no ETL data has been loaded yet.

---

## 5. Task 2.4 — Session, Alert & Middleware Endpoints

I added three operational endpoints plus **CORS** and **rate-limiting** middleware.

### 5.1 Backtests, Sessions, Alerts

```bash
curl -s "http://localhost:3000/api/backtests?limit=10" | jq
curl -s "http://localhost:3000/api/sessions?limit=10"  | jq
curl -s "http://localhost:3000/api/alerts?limit=20"    | jq
```

### 5.2 CORS Middleware — I allow only `http://localhost:5173`

```bash
curl -i -X OPTIONS "http://localhost:3000/api/alerts" \
  -H "Origin: http://localhost:5173" \
  -H "Access-Control-Request-Method: GET"
```

Expected response headers:
```
Access-Control-Allow-Origin: http://localhost:5173
Access-Control-Allow-Methods: GET,POST,OPTIONS
```

A request from a different origin is blocked:

```bash
curl -i -X OPTIONS "http://localhost:3000/api/alerts" \
  -H "Origin: http://evil.com" \
  -H "Access-Control-Request-Method: GET"
```

Expected: no `Access-Control-Allow-Origin` header returned.

### 5.3 Rate Limiting — I cap at 100 requests/15 min per IP

```bash
for i in $(seq 1 105); do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/api/assets)
  echo "Request $i: $STATUS"
done | tail -10
```

Expected: the last few requests return `429 Too Many Requests`.

---

## 6. Task 2.5 — Generic Streaming Ingestion

I implemented a generic streaming landing zone using **Facade**, **Factory**, **Strategy**, and **Repository** patterns.

### 6.1 Health check — lists all supported formats

```bash
curl -s "http://localhost:3000/api/streams/health" | jq
```

Expected: `supported_formats: ["json","csv","xml","txt","xls","xlsx","binary","tweet"]`

### 6.2 JSON ingestion (structured)

```bash
curl -s -X POST "http://localhost:3000/api/streams/ingest" \
  -H "Content-Type: application/json" \
  -H "x-stream-name: demo-json" \
  -H "x-format: json" \
  -d '{"symbol":"BTC","price":65000,"volume":1200}' | jq '{id: .data.id, structure_kind: .data.structure_kind, record_count: .data.record_count}'
```

Expected: `structure_kind: "structured"`, `record_count: 1`.

### 6.3 CSV ingestion (structured)

```bash
curl -s -X POST "http://localhost:3000/api/streams/ingest" \
  -H "Content-Type: text/plain" \
  -H "x-stream-name: demo-csv" \
  -H "x-format: csv" \
  --data-binary $'symbol,price\nBTC,65000\nETH,3200' | jq '{structure_kind: .data.structure_kind, record_count: .data.record_count}'
```

Expected: `structure_kind: "structured"`, `record_count: 2`.

### 6.4 XML ingestion (semi-structured)

```bash
curl -s -X POST "http://localhost:3000/api/streams/ingest" \
  -H "Content-Type: application/xml" \
  -H "x-stream-name: demo-xml" \
  -H "x-format: xml" \
  --data-binary '<feed><item><symbol>BTC</symbol><price>65000</price></item></feed>' | jq '{structure_kind: .data.structure_kind}'
```

Expected: `structure_kind: "semi_structured"`.

### 6.5 Plain-text ingestion (unstructured)

```bash
curl -s -X POST "http://localhost:3000/api/streams/ingest" \
  -H "Content-Type: text/plain" \
  -H "x-stream-name: demo-txt" \
  -H "x-format: txt" \
  --data-binary 'Bitcoin is surging past all-time highs!' | jq '{structure_kind: .data.structure_kind}'
```

Expected: `structure_kind: "unstructured"`.

### 6.6 List recent events (with format filter)

```bash
curl -s "http://localhost:3000/api/streams/events?limit=5" | jq '.data | length'
curl -s "http://localhost:3000/api/streams/events?format=json&limit=5" | jq '.data[0].format'
```

### 6.7 Reject unknown format

```bash
curl -s -X POST "http://localhost:3000/api/streams/ingest" \
  -H "Content-Type: application/json" \
  -H "x-format: pdf" \
  -d '{}' | jq '.error'
```

Expected: error message — `"Unsupported format: pdf"`.

---

## 7. Task 2.6 — Twitter Tweet Stream Ingestion

I added specialised tweet handling using four additional design patterns:
**Template Method** (parser), **Chain of Responsibility** (validator), **Builder** (envelope), **Decorator** (retry).

### 7.1 Tweet endpoint health

```bash
curl -s "http://localhost:3000/api/streams/tweet/health" | jq
```

Expected shows: `validation_chain: ["required_fields","text_length","timestamp"]`

### 7.2 Ingest a full Twitter API v2 tweet payload

```bash
curl -s -X POST "http://localhost:3000/api/streams/tweet/ingest" \
  -H "Content-Type: application/json" \
  -H "x-source: twitter-stream" \
  -d '{
    "id": "1234567890",
    "text": "Bitcoin is going to the moon! #BTC #crypto",
    "author_id": "987654321",
    "created_at": "2026-04-06T00:00:00.000Z",
    "public_metrics": {"retweet_count":5,"like_count":23,"reply_count":2,"quote_count":1},
    "entities": {
      "hashtags": [{"tag":"BTC"},{"tag":"crypto"}],
      "mentions": [],
      "urls": []
    }
  }' | jq '.data | {id, format, structure_kind, payload_hash}'
```

Expected: `format: "tweet"`, `structure_kind: "semi_structured"`, `payload_hash` is a 64-char hex string.

### 7.3 Chain of Responsibility — validation rejection tests

**Missing required fields (no `id`):**

```bash
curl -s -X POST "http://localhost:3000/api/streams/tweet/ingest" \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello world"}' | jq '.error'
```

Expected: `"Tweet must have an id field."`

**Text too long (> 280 characters):**

```bash
curl -s -X POST "http://localhost:3000/api/streams/tweet/ingest" \
  -H "Content-Type: application/json" \
  -d "{\"id\":\"1\",\"text\":\"$(python3 -c 'print("X"*281)')\"}" | jq '.error'
```

Expected: `"Tweet text exceeds 280 characters."`

**Invalid timestamp format:**

```bash
curl -s -X POST "http://localhost:3000/api/streams/tweet/ingest" \
  -H "Content-Type: application/json" \
  -d '{"id":"1","text":"Hello","created_at":"not-a-date"}' | jq '.error'
```

Expected: `"Tweet created_at is not a valid ISO 8601 timestamp."`

### 7.4 Query stored tweet events

```bash
curl -s "http://localhost:3000/api/streams/events?format=tweet&limit=5" | jq '.data[0] | {format, structure_kind, payload_hash}'
```

---

## 8. Task 2.7 — Backend CIA Security & Non-Repudiation

I hardened the tweet ingest endpoint with **HMAC-SHA256 signature verification** (Confidentiality), **SHA-256 payload hash** (Integrity + Non-repudiation), and audited metadata.

### 8.1 Non-repudiation — every ingest stores a SHA-256 hash

```bash
curl -s -X POST "http://localhost:3000/api/streams/tweet/ingest" \
  -H "Content-Type: application/json" \
  -d '{"id":"nr-demo","text":"BTC breaks resistance"}' \
  | jq '.data.payload_hash'
```

Expected: a 64-character hex string, e.g. `"a3f2c1..."`.

**Verify the hash is deterministic** — same payload always produces the same hash:

```bash
HASH1=$(curl -s -X POST "http://localhost:3000/api/streams/tweet/ingest" \
  -H "Content-Type: application/json" \
  -d '{"id":"det-1","text":"determinism test"}' | jq -r '.data.payload_hash')

HASH2=$(curl -s -X POST "http://localhost:3000/api/streams/tweet/ingest" \
  -H "Content-Type: application/json" \
  -d '{"id":"det-2","text":"determinism test"}' | jq -r '.data.payload_hash')

echo "Hash 1: $HASH1"
echo "Hash 2: $HASH2"
[ "$HASH1" = "$HASH2" ] && echo "MATCH — hash is deterministic" || echo "MISMATCH"
```

### 8.2 Audit trail — source IP and user-agent stored per record

```bash
curl -s "http://localhost:3000/api/streams/events?format=tweet&limit=1" \
  | jq '.data[0] | {payload_hash, metadata}'
```

Expected metadata contains: `source_ip`, `user_agent`, `ingested_via: "tweet_route"`.

### 8.3 Availability — rate limiting already protects the endpoint

```bash
for i in $(seq 1 105); do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
    "http://localhost:3000/api/streams/tweet/ingest" \
    -H "Content-Type: application/json" \
    -d '{"id":"rl-'$i'","text":"rate limit test"}')
  echo "Request $i: $STATUS"
done | grep 429 | head -3
```

### 8.4 HMAC Signature Verification — production mode

Set the secret and test both valid and invalid signatures:

```bash
export TWEET_WEBHOOK_SECRET="my-super-secret"
# Restart the API with the secret set, then:

PAYLOAD='{"id":"sec-1","text":"Verified tweet"}'
SIG=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "my-super-secret" | awk '{print $2}')

# Valid signature — should succeed (201)
curl -s -X POST "http://localhost:3000/api/streams/tweet/ingest" \
  -H "Content-Type: application/json" \
  -H "x-twitter-webhooks-signature: sha256=$SIG" \
  -d "$PAYLOAD" | jq '{status: .data.id}'

# Invalid signature — should be rejected (401)
curl -s -X POST "http://localhost:3000/api/streams/tweet/ingest" \
  -H "Content-Type: application/json" \
  -H "x-twitter-webhooks-signature: sha256=deadbeefdeadbeef" \
  -d "$PAYLOAD" | jq '.error'
```

### 8.5 Null Object (dev mode) — no secret, no errors

Without `TWEET_WEBHOOK_SECRET` set the `NullSignatureVerifier` passes all requests through and logs a warning. Check the API terminal for:

```
[TweetSignature] TWEET_WEBHOOK_SECRET not set — signature check skipped.
```

---

## 9. Unit Tests (Jest) — Tasks 2.5, 2.6, 2.7

I wrote all unit tests using Jest. They run entirely in-process — no database or network required.

```bash
npm run test:task2_5:unit
# or equivalently:
npm run test:task2_5 --prefix apps/api
```

### What each test covers

| # | Test name | Pattern verified |
|:-:|:----------|:----------------|
| 1 | `JsonStreamParser.parse()` returns structured result | Strategy |
| 2 | `CsvStreamParser.parse()` counts rows correctly | Strategy |
| 3 | `XmlStreamParser.parse()` returns semi_structured | Strategy |
| 4 | `TextStreamParser.parse()` returns unstructured | Strategy |
| 5 | `StreamParserFactory.getParser("json")` returns JsonStreamParser | Factory |
| 6 | `StreamParserFactory.getParser("unknown")` throws StreamValidationError | Factory |
| 7 | `StreamIngestionFacade.ingest()` calls factory and repository | Facade |
| 8 | `TweetStreamParser.parse()` extracts text, metrics, entities | Template Method |
| 9 | `TweetStreamParser` subclass can override `extractText()` | Template Method |
| 10 | `TweetEnvelopeBuilder.build()` produces valid envelope | Builder |
| 11 | `TweetEnvelopeBuilder` fluent chaining returns self | Builder |
| 12 | Chain rejects tweet missing `id` | Chain of Responsibility |
| 13 | Chain rejects tweet text > 280 chars | Chain of Responsibility |
| 14 | Chain rejects invalid `created_at` | Chain of Responsibility |
| 15 | Chain passes a valid tweet | Chain of Responsibility |
| 16 | `RetryingStreamIngestionFacade` retries on transient error | Decorator |
| 17 | `RetryingStreamIngestionFacade` does not retry `StreamValidationError` | Decorator |
| 18 | `computePayloadHash()` returns 64-char hex string | Non-repudiation |
| 19 | Same data always produces same hash | Non-repudiation |
| 20 | Different data produces different hashes | Integrity |
| 21 | `verifyHmacSignature()` returns true for correct secret | HMAC Strategy |
| 22 | `verifyHmacSignature()` returns false for tampered payload | HMAC Strategy |
| 23 | `verifyHmacSignature()` returns false for wrong secret | HMAC Strategy |
| 24 | Facade stores 64-char `payload_hash` on every ingest | Non-repudiation |

---

## 10. Integration Tests (pytest) — API Level

I wrote pytest suites that hit the live API and verify end-to-end behaviour.

### 10.1 Prerequisites

```bash
# Install test dependencies (already in apps/etl/venv)
pip install requests pytest
```

### 10.2 Task 2.5 API integration tests

```bash
pytest task_2_5_tests -v
```

Tests: health returns 200, JSON ingest returns 201, CSV row count, XML semi_structured, txt unstructured, unknown format 400.

**Standalone checker (no pytest needed):**

```bash
python3 task_2_5_tests/main.py
```

### 10.3 Task 2.6 API integration tests

```bash
pytest task_2_6_tests -v
```

Tests: tweet health 200, minimal tweet ingest, full tweet with metrics/entities, validation rejection (missing id), validation rejection (text too long), events queryable by `format=tweet`.

**Standalone checker:**

```bash
python3 task_2_6_tests/main.py
```

### 10.4 Task 2.7 API integration tests

```bash
pytest task_2_7_tests -v
```

Tests: payload_hash is stored and is 64 chars, hash matches recomputed SHA-256, different tweets produce different hashes, audit metadata contains source_ip + user_agent, dev-mode pass-through (no secret needed), generic ingest also stores payload_hash.

**Standalone checker:**

```bash
python3 task_2_7_tests/main.py
```

### 10.5 Run all pytest suites at once

```bash
pytest task_2_5_tests task_2_6_tests task_2_7_tests -v
```

---

## 11. CLI Script Smoke Tests

I also wrote bash scripts for quick sanity checks.

```bash
# Task 2.5 — 7 curl checks in sequence
bash scripts/task_2_5_check.sh

# Task 2.5–2.7 combined
bash scripts/task_2_all_check.sh
```

---

## 12. Database Verification Queries

I can demonstrate the data is actually persisted in PostgreSQL by querying directly.

```bash
psql postgres://user:password@localhost:5432/hypecheck
```

Once inside `psql`:

```sql
-- Count all ingested stream events
SELECT COUNT(*), format, structure_kind
FROM stream_ingestion_events
GROUP BY format, structure_kind
ORDER BY COUNT(*) DESC;

-- Verify payload_hash is populated (non-repudiation check)
SELECT id, format, LENGTH(payload_hash) AS hash_len, payload_hash
FROM stream_ingestion_events
WHERE format = 'tweet'
ORDER BY created_at DESC
LIMIT 5;

-- Confirm no nulls in payload_hash (all events have non-repudiation)
SELECT COUNT(*) AS missing_hash
FROM stream_ingestion_events
WHERE payload_hash IS NULL;

-- Verify audit metadata is stored
SELECT id, metadata->>'source_ip' AS source_ip,
       metadata->>'user_agent' AS user_agent,
       metadata->>'ingested_via' AS ingested_via
FROM stream_ingestion_events
WHERE format = 'tweet'
ORDER BY created_at DESC
LIMIT 3;

-- Inspect a tweet's parsed payload_json
SELECT id, payload_json->'tweet_id' AS tweet_id,
       payload_json->'text' AS text,
       payload_json->'metrics' AS metrics
FROM stream_ingestion_events
WHERE format = 'tweet'
ORDER BY created_at DESC
LIMIT 1;

-- Confirm structure_kind classification is correct
SELECT format, structure_kind, COUNT(*)
FROM stream_ingestion_events
GROUP BY format, structure_kind;

-- Check assets table is seeded
SELECT symbol, name, type FROM assets ORDER BY symbol;

-- Check sentiment aggregations exist (after ETL run)
SELECT symbol, COUNT(*) FROM sentiment_aggregations GROUP BY symbol;

-- Check correlation data
SELECT symbol, AVG(correlation_coefficient)
FROM sentiment_price_correlation
GROUP BY symbol;

-- List recent alerts
SELECT id, symbol, alert_type, severity, created_at
FROM alerts
ORDER BY created_at DESC
LIMIT 10;

-- Verify live_sessions tracking
SELECT id, status, started_at, ended_at
FROM live_sessions
ORDER BY started_at DESC
LIMIT 5;
```

---

## 13. Design Patterns — Quick Demo Talking Points

When demoing to my professor I walk through each pattern with a specific evidence command:

| Pattern | Where I show it | Evidence |
|:--------|:----------------|:---------|
| **Facade** | `streamIngestionFacade.js` | One `ingest()` call coordinates validate → parse → hash → persist |
| **Factory** | `streamParsers.js` | `getParser("csv")` returns `CsvStreamParser` without caller knowing the class |
| **Strategy** | Parser subclasses | Swapping `format=json` vs `format=csv` uses different class, same interface |
| **Repository** | `streamEventRepository.js` | Route handler calls `repository.create()`; no raw SQL in route |
| **Singleton** | `apps/api/database/index.js` | One Sequelize pool shared across all route handlers |
| **Observer** | `live_engine.py` | `LiveProcessor` calls `_notify_divergence()` → observers write to DB |
| **Pipeline** | `backtest_engine.py` | `BacktestRunner.run()` = price → aggregation → correlation stages |
| **Template Method** | `TweetStreamParser` | `parse()` calls `extractText()`, `extractMetrics()`, `extractEntities()` |
| **Chain of Responsibility** | `createTweetValidationChain()` | RequiredFields → TextLength → Timestamp — each handler checks one rule |
| **Builder** | `TweetEnvelopeBuilder` | Fluent `.withTweet().withSource().withMetadata().build()` |
| **Decorator** | `RetryingStreamIngestionFacade` | Wraps facade; adds retry logic without changing inner class |
| **Strategy + Null Object** | `tweetSignature.js` | `HmacSignatureVerifier` in prod; `NullSignatureVerifier` in dev — same interface |
| **Non-repudiation** | `payload_hash` column | 64-char SHA-256 proves exact bytes received, stored immutably |

---

## 14. Frontend Dashboard Verification

I can also show the frontend is live and connected:

1. Open `http://localhost:5173` in the browser.
2. The dashboard loads charts — if ETL has run in backtest mode, dual-axis price/sentiment charts appear for BTC, ETH, TSLA, NVDA, GME, AMC.
3. The Alerts panel lists any detected divergence or volume-spike alerts.
4. All data flows from the same PostgreSQL instance via the REST API.

---

## 15. Full Test Run — One-Liner Summary

```bash
# 1. Start infrastructure
npm run docker:up && npm run dev:api &

# 2. Unit tests (no DB needed)
npm run test:task2_5:unit

# 3. Integration tests (API must be running)
pytest task_2_5_tests task_2_6_tests task_2_7_tests -v

# 4. Smoke scripts
bash scripts/task_2_5_check.sh

# 5. DB queries (paste from Section 12 above into psql)
psql postgres://user:password@localhost:5432/hypecheck
```

All tests passing confirms: design patterns are correctly implemented, CIA security properties hold, non-repudiation hashes are stored, and the streaming ingestion pipeline handles all seven supported formats.
