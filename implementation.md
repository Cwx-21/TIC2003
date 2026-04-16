# HypeCheck — Implementation Reference

This document provides an end-to-end implementation reference for Tasks 2.1–2.7, including database verification queries, API test commands, design pattern locations, and test runner commands. Intended for academic assessment and senior code review.

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│  Frontend (React + Vite, port 5173)                          │
│  Dual-axis charts: Sentiment Score vs. Asset Price           │
└─────────────────────────┬────────────────────────────────────┘
                          │ HTTP REST
┌─────────────────────────▼────────────────────────────────────┐
│  Backend API (Node.js + Express, port 3000)                  │
│                                                              │
│  /api/assets        /api/sentiment    /api/prices            │
│  /api/correlation   /api/backtests    /api/sessions          │
│  /api/alerts        /api/streams      /api/streams/tweet     │
│                                                              │
│  Middleware: CORS · Rate Limit · HMAC Signature (Task 2.7)   │
│  Services:   StreamIngestionFacade · StreamParserFactory     │
└─────────────────────────┬────────────────────────────────────┘
                          │ Sequelize ORM / pg
┌─────────────────────────▼────────────────────────────────────┐
│  PostgreSQL 15 (Docker, port 5432)                           │
│  11 tables · 18+ indexes · JSONB payload storage             │
└─────────────────────────┬────────────────────────────────────┘
                          │ psycopg2
┌─────────────────────────▼────────────────────────────────────┐
│  ETL Pipeline (Python 3, VADER NLP)                          │
│  Backtest: Reddit CSV → sentiment_logs                       │
│  Live:     Telegram  → sentiment_logs (real-time)            │
└──────────────────────────────────────────────────────────────┘
```

---

## Design Patterns — Full Reference

| Task | Pattern | Class / Function | File |
| :--- | :------ | :--------------- | :--- |
| 2.5 | **Facade** | `StreamIngestionFacade.ingest()` | `apps/api/services/streams/streamIngestionFacade.js` |
| 2.5 | **Factory** | `StreamParserFactory.getParser(format)` | `apps/api/services/streams/streamParsers.js` |
| 2.5 | **Strategy** | `BaseStreamParser` + concrete subclasses | `apps/api/services/streams/streamParsers.js` |
| 2.5 | **Repository** | `StreamEventRepository` | `apps/api/services/streams/streamEventRepository.js` |
| 2.5 | **Singleton** | Sequelize pool (`db`) + psycopg2 `SimpleConnectionPool` | `apps/api/database/index.js`, `apps/etl/db.py` |
| 2.5 | **Pipeline** | `BacktestRunner.run()` — three sequential post-processing phases | `apps/etl/backtest_engine.py` |
| ETL | **Observer** | `AlertObserver` / `DatabaseAlertObserver` | `apps/etl/live_engine.py` |
| 2.6 | **Template Method** | `TweetStreamParser.parse()` with overridable hooks | `apps/api/services/streams/streamParsers.js` |
| 2.6 | **Chain of Responsibility** | `TweetRequiredFieldsValidator → TweetTextLengthValidator → TweetTimestampValidator` | `apps/api/services/streams/streamIngestionFacade.js` |
| 2.6 | **Builder** | `TweetEnvelopeBuilder` | `apps/api/services/streams/streamIngestionFacade.js` |
| 2.6 | **Decorator** | `RetryingStreamIngestionFacade` | `apps/api/services/streams/streamIngestionFacade.js` |
| 2.7 | **Strategy** | `HmacSignatureVerifier` / `NullSignatureVerifier` | `apps/api/middleware/tweetSignature.js` |
| 2.7 | **Null Object** | `NullSignatureVerifier` (dev-mode pass-through) | `apps/api/middleware/tweetSignature.js` |

---

## Database Verification Queries

Connect to PostgreSQL:

```bash
docker exec -it hypecheck-postgres psql -U user -d hypecheck
```

### 1. Schema — verify all 11 tables exist

```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
```

Expected tables: `alerts`, `assets`, `author_credibility`, `backtest_runs`,
`historical_prices`, `live_sessions`, `price_history`, `sentiment_aggregations`,
`sentiment_logs`, `sentiment_price_correlation`, `stream_ingestion_events`.

### 2. Indexes — verify 18+ indexes

```sql
SELECT indexname, tablename
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;
```

### 3. stream_ingestion_events — verify schema columns (Task 2.5–2.7)

```sql
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'stream_ingestion_events'
ORDER BY ordinal_position;
```

Expected columns include: `id`, `source`, `stream_name`, `format`,
`content_type`, `structure_kind`, `parser_key`, `payload_json`, `payload_text`,
`payload_base64`, `payload_hash`, `metadata`, `original_size_bytes`,
`record_count`, `status`, `received_at`, `created_at`.

### 4. Ingestion events — recent records with non-repudiation fields (Task 2.7)

```sql
SELECT
    id,
    source,
    format,
    structure_kind,
    parser_key,
    record_count,
    status,
    payload_hash,
    received_at
FROM stream_ingestion_events
ORDER BY received_at DESC
LIMIT 10;
```

### 5. Tweet events — with audit metadata (Task 2.6 + 2.7)

```sql
SELECT
    id,
    source,
    metadata->>'ingested_via'  AS ingested_via,
    metadata->>'source_ip'     AS source_ip,
    metadata->>'user_agent'    AS user_agent,
    metadata->>'tweet_id'      AS tweet_id,
    payload_hash,
    received_at
FROM stream_ingestion_events
WHERE format = 'tweet'
ORDER BY received_at DESC
LIMIT 10;
```

### 6. Structure kind distribution

```sql
SELECT structure_kind, COUNT(*) AS event_count
FROM stream_ingestion_events
GROUP BY structure_kind
ORDER BY event_count DESC;
```

### 7. Non-repudiation integrity check — count records missing hash

```sql
SELECT COUNT(*) AS missing_hash
FROM stream_ingestion_events
WHERE payload_hash IS NULL;
```

Expected: `0` for all records ingested after Task 2.7 deployment.

### 8. Sentiment logs — total records per asset

```sql
SELECT asset_symbol, COUNT(*) AS post_count,
       ROUND(AVG(sentiment_score)::numeric, 4) AS avg_sentiment
FROM sentiment_logs
GROUP BY asset_symbol
ORDER BY post_count DESC;
```

### 9. Sentiment aggregations — latest bucket per asset

```sql
SELECT DISTINCT ON (asset_symbol)
    asset_symbol,
    time_bucket,
    bucket_interval,
    avg_sentiment_score,
    message_volume
FROM sentiment_aggregations
ORDER BY asset_symbol, time_bucket DESC;
```

### 10. Price vs Sentiment correlation — top divergence alerts

```sql
SELECT
    s.asset_symbol,
    s.time_bucket,
    s.avg_sentiment_score,
    c.price_at_bucket,
    c.divergence_score,
    c.alert_triggered
FROM sentiment_aggregations s
JOIN sentiment_price_correlation c
  ON s.asset_symbol = c.asset_symbol
 AND s.time_bucket  = c.time_bucket
WHERE c.alert_triggered = TRUE
ORDER BY ABS(c.divergence_score) DESC
LIMIT 10;
```

### 11. Author credibility — top ranked authors

```sql
SELECT author_id, credibility_score, post_count, avg_sentiment
FROM author_credibility
ORDER BY credibility_score DESC
LIMIT 10;
```

### 12. Backtest run status

```sql
SELECT id, status, total_posts_processed, total_sentiment_logs, started_at, completed_at
FROM backtest_runs
ORDER BY started_at DESC
LIMIT 5;
```

---

## API Endpoints — Quick Test Commands

Assumes API is running on `http://localhost:3000`.

```bash
# Health
curl -s http://localhost:3000/ | jq

# Assets
curl -s http://localhost:3000/api/assets | jq

# Sentiment for BTC
curl -s http://localhost:3000/api/sentiment/BTC | jq

# Historical prices for TSLA
curl -s "http://localhost:3000/api/prices/TSLA?limit=5" | jq

# Correlation for ETH
curl -s "http://localhost:3000/api/correlation/ETH?limit=5" | jq

# Latest backtests
curl -s "http://localhost:3000/api/backtests?limit=5" | jq

# Latest alerts
curl -s "http://localhost:3000/api/alerts?limit=10" | jq

# Stream health (Task 2.5)
curl -s http://localhost:3000/api/streams/health | jq

# Tweet health (Task 2.6)
curl -s http://localhost:3000/api/streams/tweet/health | jq

# Recent tweet events with non-repudiation hash (Task 2.7)
curl -s "http://localhost:3000/api/streams/events?format=tweet&limit=5" | jq '.data[] | {id, payload_hash, metadata}'
```

---

## Running All Tests

### Unit Tests (no database required)

```bash
npm run test:task2_5:unit
```

Covers all 21 unit tests for Tasks 2.5, 2.6, and 2.7.

### Integration Tests (database + API required)

```bash
# Task 2.5
python3 task_2_5_tests/main.py
pytest task_2_5_tests -q

# Task 2.6
python3 task_2_6_tests/main.py
pytest task_2_6_tests -q

# Task 2.7
python3 task_2_7_tests/main.py
pytest task_2_7_tests -q

# All integration tests at once
pytest task_2_5_tests task_2_6_tests task_2_7_tests -v
```

### Frontend E2E Tests (Playwright)

Playwright tests verify the frontend dashboard loads and charts render.
Requires the API and frontend to be running (`npm run dev:api` + `npm run dev:web`).

```bash
# Install Playwright (one-time)
npx playwright install

# Run E2E tests
npx playwright test

# Run with UI mode for visual debugging
npx playwright test --ui
```

Key scenarios to verify manually at `http://localhost:5173`:

1. Dashboard loads without errors
2. Asset selector (BTC, ETH, TSLA, NVDA, GME, AMC) populates charts
3. Dual-axis chart shows both sentiment score and price on the same timeline
4. Alerts table loads recent alert entries

### Scripted Smoke Check

```bash
bash scripts/task_2_5_check.sh
```

---

## Environment Variables

| Variable | Required | Default | Purpose |
| :------- | :------- | :------ | :------ |
| `DATABASE_URL` | Yes | — | PostgreSQL connection string |
| `PORT` | No | `3000` | API listen port |
| `API_JSON_LIMIT` | No | `1mb` | Max JSON body size for generic routes |
| `STREAM_MAX_BODY_BYTES` | No | `1048576` | Max body size for stream ingest |
| `TWEET_WEBHOOK_SECRET` | No | — | HMAC secret for tweet signature verification (Task 2.7) |
| `TELEGRAM_API_ID` | Live mode | — | Telegram API credentials |
| `TELEGRAM_API_HASH` | Live mode | — | Telegram API credentials |

---

## Security Notes (Task 2.7)

### Non-Repudiation

Every ingested event stores a `payload_hash` (SHA-256 hex digest). To verify what was received:

```python
import hashlib, json
payload = {"id": "1", "text": "BTC to the moon"}
computed = hashlib.sha256(json.dumps(payload).encode()).hexdigest()
# Compare computed against stored payload_hash from the database
```

### Signature Verification Mode

| `TWEET_WEBHOOK_SECRET` set? | Active verifier | Behaviour |
| :--- | :--- | :--- |
| No | `NullSignatureVerifier` | All requests pass; warning logged |
| Yes | `HmacSignatureVerifier` | Requests without valid `x-twitter-webhooks-signature` rejected with 401 |

### Audit Trail per Ingest

The `metadata` JSONB column stores:

```json
{
  "ingested_via": "tweet_route",
  "source_ip": "::1",
  "user_agent": "curl/8.1.2",
  "tweet_id": "1234567890",
  "author_id": "987654321"
}
```
