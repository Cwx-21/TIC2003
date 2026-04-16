# Task 2.7 Testing Guide (CIA Security & Non-Repudiation)

This guide verifies the backend security hardening layer added in Task 2.7 to the tweet ingestion endpoint. All changes are additive — existing Task 2.5 and 2.6 behaviour is preserved.

## 0) Technical Overview

Task 2.7 applies CIA security principles and non-repudiation to the live tweet stream backend:

| CIA Property | Implementation | Pattern |
| :----------- | :------------- | :------ |
| **Confidentiality** | HMAC-SHA256 signature verification on `POST /tweet/ingest` | Strategy + Null Object |
| **Integrity** | SHA-256 `payload_hash` stored with every record — detects post-receipt tampering | Utility function |
| **Availability** | Existing rate limiting (Task 2.4) applies to `/api/*`; signature check is fast | Existing |
| **Non-repudiation** | `payload_hash` + `source_ip` + `user_agent` stored per event — proves what was received, who sent it, and when | Facade + Builder |

## 1) Prerequisite: Database + API Running

```bash
# Start PostgreSQL
docker compose up -d postgres

# Initialize schema (run once — adds payload_hash column)
docker compose run --rm etl python -c "from db import init_db; init_db()"

# Start API
DATABASE_URL=postgres://user:password@localhost:5432/hypecheck npm run dev:api
```

## 2) CLI Tests (curl)

### Ingest a tweet and inspect the payload_hash

```bash
curl -s -X POST "http://localhost:3000/api/streams/tweet/ingest" \
  -H "Content-Type: application/json" \
  -H "x-source: manual-test" \
  -d '{"id":"1","text":"BTC breaks 70k resistance"}' | jq '.data | {payload_hash, status, source_ip: .metadata.source_ip}'
```

Expected: `payload_hash` is a 64-character lowercase hex string.

### Verify non-repudiation audit fields in metadata

```bash
curl -s "http://localhost:3000/api/streams/events?format=tweet&include_payload=false&limit=1" \
  | jq '.data[0] | {payload_hash, metadata}'
```

Expected: `metadata` contains `ingested_via`, `source_ip`, and `user_agent`.

### Test signature middleware in dev mode (no secret — NullSignatureVerifier)

```bash
# No x-twitter-webhooks-signature header — passes in dev mode
curl -s -X POST "http://localhost:3000/api/streams/tweet/ingest" \
  -H "Content-Type: application/json" \
  -d '{"id":"2","text":"ETH drops to support"}' | jq '.data.status'
```

Expected: `"accepted"` (NullSignatureVerifier allows through with a console warning).

### Test signature middleware in production mode (with secret)

Set the environment variable and restart the API:

```bash
TWEET_WEBHOOK_SECRET=my-secret DATABASE_URL=postgres://user:password@localhost:5432/hypecheck npm run dev:api
```

Then send a request **without** a signature — expect 401:

```bash
curl -s -X POST "http://localhost:3000/api/streams/tweet/ingest" \
  -H "Content-Type: application/json" \
  -d '{"id":"3","text":"GME squeezing"}' | jq
```

Expected: `{"error": "Missing x-twitter-webhooks-signature header."}`

Send a request **with** a valid HMAC-SHA256 signature:

```bash
PAYLOAD='{"id":"3","text":"GME squeezing"}'
SECRET="my-secret"
SIG=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$SECRET" | awk '{print $2}')

curl -s -X POST "http://localhost:3000/api/streams/tweet/ingest" \
  -H "Content-Type: application/json" \
  -H "x-twitter-webhooks-signature: sha256=$SIG" \
  -d "$PAYLOAD" | jq '.data.status'
```

Expected: `"accepted"`

### Regression — generic ingest also stores payload_hash

```bash
curl -s -X POST "http://localhost:3000/api/streams/ingest" \
  -H "Content-Type: application/json" \
  -d '{"source":"regression-test","format":"json","payload":{"asset":"NVDA","score":0.7}}' \
  | jq '.data.payload_hash'
```

Expected: 64-character hex string (proves the hash is format-agnostic).

## 3) Database Verification Queries

Connect to the database and verify payload_hash is populated:

```bash
docker exec -it hypecheck-postgres psql -U user -d hypecheck
```

```sql
-- Verify payload_hash column exists and is populated
SELECT id, source, format, payload_hash, received_at
FROM stream_ingestion_events
ORDER BY received_at DESC
LIMIT 5;

-- Check for any records missing a hash (should be 0 after Task 2.7)
SELECT COUNT(*) AS missing_hash
FROM stream_ingestion_events
WHERE payload_hash IS NULL;

-- Inspect non-repudiation audit metadata for tweet events
SELECT id, source,
       metadata->>'source_ip' AS source_ip,
       metadata->>'user_agent' AS user_agent,
       metadata->>'ingested_via' AS ingested_via,
       payload_hash
FROM stream_ingestion_events
WHERE format = 'tweet'
ORDER BY received_at DESC
LIMIT 5;
```

## 4) Unit Tests (all tasks including 2.7)

```bash
npm run test:task2_5:unit
```

### Task 2.7 unit tests verify

| Test | What it checks |
| :--- | :------------- |
| `computePayloadHash returns a 64-character hex SHA-256 digest` | Hash format |
| `computePayloadHash is deterministic for identical inputs` | Reproducibility |
| `computePayloadHash produces different digests for different inputs` | Collision resistance |
| `verifyHmacSignature returns true for a valid HMAC-SHA256 signature` | HMAC success path |
| `verifyHmacSignature returns false for a tampered payload` | Integrity check |
| `verifyHmacSignature returns false for a wrong secret` | Key mismatch |
| `StreamIngestionFacade stores a 64-char payload_hash in the persisted record` | End-to-end hash storage |

## 5) pytest Integration Tests

```bash
pytest task_2_7_tests -q
python3 task_2_7_tests/main.py
```

### Recommended full test order

```bash
# Unit tests first (no DB needed)
npm run test:task2_5:unit

# Integration tests (DB required)
python3 task_2_7_tests/main.py
pytest task_2_7_tests -q

# Regression — ensure 2.5 and 2.6 tests still pass
pytest task_2_5_tests -q
pytest task_2_6_tests -q
```

## 6) Design Patterns Reference

| Pattern | Class | Location |
| :------ | :---- | :------- |
| **Strategy** | `BaseSignatureVerifier`, `HmacSignatureVerifier`, `NullSignatureVerifier` | `apps/api/middleware/tweetSignature.js` |
| **Null Object** | `NullSignatureVerifier` — passes all requests; no null-check needed in route handler | `apps/api/middleware/tweetSignature.js` |

## 7) Task 2.7 Modified / Created Files

**New files:**

- `apps/api/utils/crypto.js` — `computePayloadHash()`, `verifyHmacSignature()`
- `apps/api/middleware/tweetSignature.js` — Strategy + Null Object middleware
- `task_2_7_tests/test_task_2_7_api.py` — pytest integration tests
- `task_2_7_tests/main.py` — standalone checker

**Modified existing files:**

- `apps/api/schemas/stream_ingestion_events.js` — added `payload_hash CHAR(64)` column
- `apps/api/services/streams/streamEventRepository.js` — `payload_hash` in DEFAULT_ATTRIBUTES
- `apps/api/services/streams/streamIngestionFacade.js` — computes `payload_hash` before persistence
- `apps/etl/db.py` — `payload_hash CHAR(64)` added to CREATE TABLE DDL
- `apps/api/routes/streams.js` — `tweetSignatureMiddleware` mounted; source_ip + user_agent added to metadata
- `apps/api/tests/task_2_5.unit.test.js` — 7 new unit tests for Task 2.7
