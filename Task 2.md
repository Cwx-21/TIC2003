Task 2.1: Database ORM Models & Migrations

- Deliverable: Sequelize models defined for all 10 tables documented in ETL_DB_SCHEMA.md.
- Dependencies: None (can work off schema docs before DB is fully populated).
- Tech: Node.js, Sequelize.
- Success Criteria: Sequelize successfully syncs with the Dockerized PostgreSQL instance without errors.

Task 2.2: Core REST Endpoints Implementation

- Deliverable: API endpoints routing for /api/assets, /api/sentiment/:symbol, /api/prices/:symbol, and /api/correlation/:symbol.
- Dependencies: Task 2.1 (can map routes to dummy data before DB models are ready).
- Tech: Node.js, Express.
- Success Criteria: Endpoints return cleanly formatted JSON payloads matching UI data requirements.

Task 2.3: Complex Query Optimization & Aggregation Service

- Deliverable: Services that query sentiment_aggregations and historical_prices efficiently, utilizing indexes.
- Dependencies: Task 2.1.
- Tech: Node.js, Sequelize/Raw SQL.
- Success Criteria: DB Queries return aggregated payload.

Task 2.4: Session, Alert & Middleware Endpoints

- Deliverable: Formal implementation of the /api/backtests, /api/sessions, and /api/alerts endpoints, complemented by cross-origin resource sharing (CORS) and rate-limiting middleware to ensure controlled and standards-compliant access.
- Dependencies: Task 2.3.
- Tech: Node.js, Express.
- Success Criteria: The API layer reliably retrieves backtest metrics and system alerts with validated response structures, while CORS explicitly permits requests from http://localhost:5173.

Testing (Quick Commands)

1) Verify API health

```bash
curl -s http://localhost:3000/ | jq
```

2) Fetch backtests (latest 10)

```bash
curl -s "http://localhost:3000/api/backtests?limit=10" | jq
```

3) Fetch live sessions (latest 10)

```bash
curl -s "http://localhost:3000/api/sessions?limit=10" | jq
```

4) Fetch alerts (latest 20)

```bash
curl -s "http://localhost:3000/api/alerts?limit=20" | jq
```

5) Confirm CORS preflight from localhost:5173

```bash
curl -i -X OPTIONS "http://localhost:3000/api/alerts" \
  -H "Origin: http://localhost:5173" \
  -H "Access-Control-Request-Method: GET"
```

6) Run Task 2.4 pytest checks only

```bash
pytest task_2_4_tests -q
```

7) Run Task 2.4 standalone checker

```bash
python3 task_2_4_tests/main.py
```

Task 2.4 Technical Workflow

1) Start PostgreSQL and initialize schema.
2) Start the API with `DATABASE_URL` pointing at the local Postgres instance.
3) Verify health endpoint returns 200.
4) Verify Task 2.4 endpoints return JSON:
5) `/api/backtests`
6) `/api/sessions`
7) `/api/alerts`
8) Verify CORS allows `http://localhost:5173` (OPTIONS preflight).
9) Verify rate limiting returns `429` after exceeding the request limit.

Task 2.4 New Files (Purpose)

- `apps/api/database/index.js` — Task 2.4 DB connector used by the new endpoints.
- `apps/api/middleware/cors.js` — Task 2.4 CORS allowlist (permits `http://localhost:5173`).
- `apps/api/middleware/rateLimit.js` — Task 2.4 rate limiting middleware (protects `/api/*`).
- `apps/api/routes/backtests.js` — Task 2.4 `/api/backtests` endpoint.
- `apps/api/routes/sessions.js` — Task 2.4 `/api/sessions` endpoint.
- `apps/api/routes/alerts.js` — Task 2.4 `/api/alerts` endpoint.
- `apps/api/utils/query.js` — Task 2.4 query parsing helpers (limit/id/status filters).
- `postman/HypeCheck_Task2_4.postman_collection.json` — Task 2.4 Postman collection for quick tests.
- `Task_2_4_Testing.md` — Task 2.4 test workflow and commands.

Task 2.7: Backend CIA Security & Non-Repudiation

- Deliverable: A security hardening layer on the tweet ingestion endpoint covering Confidentiality (HMAC-SHA256 signature verification), Integrity (SHA-256 payload hash), Availability (existing rate limiting), and Non-repudiation (hash + source IP + user-agent audit trail stored per event).
- Dependencies: Task 2.6 (`POST /api/streams/tweet/ingest`).
- Tech: Node.js, `node:crypto` (built-in), Express middleware.
- Success Criteria: Every accepted ingest stores a 64-character `payload_hash`; source_ip and user_agent appear in metadata; HMAC verification activates when `TWEET_WEBHOOK_SECRET` is set; all unit and integration tests pass.

Design Patterns (Task 2.7 additions):

| Pattern | Implementation | Location |
| :------ | :------------- | :------- |
| **Strategy** | `BaseSignatureVerifier` interface with `HmacSignatureVerifier` (production) and `NullSignatureVerifier` (development) — selected at startup based on `TWEET_WEBHOOK_SECRET` | `apps/api/middleware/tweetSignature.js` |
| **Null Object** | `NullSignatureVerifier` satisfies the full Strategy interface but passes all requests through, eliminating null-check branches in the route handler | `apps/api/middleware/tweetSignature.js` |

CIA Mapping:

- **Confidentiality** — `HmacSignatureVerifier` ensures only authorised senders (holding the shared secret) can ingest tweets.
- **Integrity** — SHA-256 `payload_hash` detects post-receipt tampering. The stored hash is recomputable from the original payload.
- **Availability** — Task 2.4 rate limiting already protects `/api/*`. The signature check adds negligible overhead.
- **Non-repudiation** — `payload_hash` + `metadata.source_ip` + `metadata.user_agent` stored per event proves what was received, who sent it, and when.

Testing (Quick Commands):

1. Ingest with non-repudiation hash visible

```bash
curl -s -X POST "http://localhost:3000/api/streams/tweet/ingest" \
  -H "Content-Type: application/json" \
  -d '{"id":"1","text":"BTC breaks resistance"}' | jq '.data.payload_hash'
```

1. Verify hash in events list

```bash
curl -s "http://localhost:3000/api/streams/events?format=tweet&limit=1" \
  | jq '.data[0] | {payload_hash, metadata}'
```

1. Run all unit tests (Tasks 2.5 + 2.6 + 2.7)

```bash
npm run test:task2_5:unit
```

1. Run integration tests

```bash
pytest task_2_7_tests -q
python3 task_2_7_tests/main.py
```

See [Task_2_7_Testing.md](Task_2_7_Testing.md) for full curl commands including HMAC signature production mode testing.

Task 2.7 Modified Files:

- `apps/api/utils/crypto.js` — NEW: `computePayloadHash()`, `verifyHmacSignature()`
- `apps/api/middleware/tweetSignature.js` — NEW: Strategy + Null Object middleware
- `apps/api/schemas/stream_ingestion_events.js` — added `payload_hash CHAR(64)` column
- `apps/api/services/streams/streamEventRepository.js` — `payload_hash` in DEFAULT_ATTRIBUTES
- `apps/api/services/streams/streamIngestionFacade.js` — computes hash before persistence
- `apps/etl/db.py` — `payload_hash CHAR(64)` in CREATE TABLE DDL
- `apps/api/routes/streams.js` — `tweetSignatureMiddleware` mounted; source_ip + user_agent in metadata
- `apps/api/tests/task_2_5.unit.test.js` — 7 new unit tests for Task 2.7

Task 2.6: Twitter/X Live Tweet Stream Ingestion

- Deliverable: A specialised ingestion route (`POST /api/streams/tweet/ingest`) for Twitter API v2 tweet payloads, built on top of the Task 2.5 streaming infrastructure with four additional design patterns that improve robustness and maintainability.
- Dependencies: Task 2.5 (StreamIngestionFacade, StreamParserFactory, StreamEventRepository).
- Tech: Node.js, Express, Sequelize, Twitter API v2 JSON format.
- Success Criteria: `/api/streams/tweet/ingest` validates, parses, and persists tweet payloads; `/api/streams/tweet/health` reports endpoint configuration; all new unit tests pass.

Design Patterns (Task 2.6 additions):

| Pattern | Implementation | Location |
| :------------------------ | :-------------------------------------------------------------------------------------------------- | :----------------------------------------------- |
| **Template Method** | `TweetStreamParser.parse()` defines the fixed parsing skeleton; `extractText()`, `extractMetrics()`, `extractEntities()` are overridable hooks | `apps/api/services/streams/streamParsers.js` |
| **Chain of Responsibility** | `TweetRequiredFieldsValidator → TweetTextLengthValidator → TweetTimestampValidator` — each handler validates one rule and passes to the next | `apps/api/services/streams/streamIngestionFacade.js` |
| **Builder** | `TweetEnvelopeBuilder` constructs the ingest envelope from a raw Twitter API v2 tweet object via fluent method chaining | `apps/api/services/streams/streamIngestionFacade.js` |
| **Decorator** | `RetryingStreamIngestionFacade` wraps any facade instance with exponential-backoff retry logic for transient DB errors, without modifying the inner facade | `apps/api/services/streams/streamIngestionFacade.js` |

Testing (Quick Commands):

1. Tweet ingestion health

```bash
curl -s "http://localhost:3000/api/streams/tweet/health" | jq
```

1. Ingest a tweet payload

```bash
curl -s -X POST "http://localhost:3000/api/streams/tweet/ingest" \
  -H "Content-Type: application/json" \
  -H "x-source: twitter-stream" \
  -d '{
    "id": "1234567890",
    "text": "Bitcoin is going to the moon! #BTC #crypto",
    "author_id": "987654321",
    "created_at": "2026-04-06T00:00:00.000Z",
    "public_metrics": {"retweet_count": 5, "like_count": 23, "reply_count": 2, "quote_count": 1},
    "entities": {"hashtags": [{"tag": "BTC"}, {"tag": "crypto"}], "mentions": [], "urls": []}
  }' | jq
```

1. Query stored tweet events

```bash
curl -s "http://localhost:3000/api/streams/events?format=tweet&limit=10" | jq
```

1. Run all unit tests (Task 2.5 + Task 2.6)

```bash
npm run test:task2_5 --prefix apps/api
```

Task 2.6 Technical Workflow:

1. Client POSTs a Twitter API v2 tweet JSON body to `/api/streams/tweet/ingest`.
1. The Chain of Responsibility validates: required fields → text length → timestamp format.
1. The Builder (TweetEnvelopeBuilder) constructs the standard ingest envelope.
1. The Facade (StreamIngestionFacade) delegates to the Factory and TweetStreamParser.
1. The Template Method parser extracts text, metrics, and entities via hook methods.
1. The Repository persists the event as `format=tweet`, `structure_kind=semi_structured`.
1. The event is queryable via `/api/streams/events?format=tweet`.

See [Task_2_6_Testing.md](Task_2_6_Testing.md) for the full test guide (curl commands, validation chain tests, unit test reference).

Task 2.6 Modified Files (no new files — all integrated into existing code):

- `apps/api/services/streams/streamParsers.js` — Added `TweetStreamParser` (Template Method) and registered it in `DEFAULT_PARSERS`.
- `apps/api/services/streams/streamIngestionFacade.js` — Added `TweetEnvelopeBuilder` (Builder), `createTweetValidationChain` (Chain of Responsibility), `RetryingStreamIngestionFacade` (Decorator).
- `apps/api/routes/streams.js` — Added `GET /tweet/health` and `POST /tweet/ingest` endpoints.
- `apps/api/utils/streaming.js` — Registered `tweet` format in `FORMAT_ALIASES` and `STRUCTURE_BY_FORMAT`.
- `apps/api/tests/task_2_5.unit.test.js` — Added 9 new unit tests covering all four Task 2.6 patterns.

Task 2.5: Generic Streaming Ingestion for PostgreSQL

- Deliverable: A new generic ingestion route that accepts structured, semi-structured, and unstructured streaming payloads (`json`, `csv`, `xml`, `txt`, `xls`, `xlsx`, and raw binary), persists them in PostgreSQL, and exposes health/list endpoints for validation.
- Dependencies: Task 2.1 and Task 2.4.
- Tech: Node.js, Express, Sequelize, PostgreSQL JSONB/TEXT storage.
- Success Criteria: `/api/streams/ingest` stores ingestion events consistently, `/api/streams/health` reports supported formats, `/api/streams/events` lists recent records, and unit/API tests pass.

Testing (Quick Commands)

1) Verify streams health

```bash
curl -s "http://localhost:3000/api/streams/health" | jq
```

2) Run Task 2.5 CLI checker

```bash
bash scripts/task_2_5_check.sh
```

3) Run Task 2.5 unit test

```bash
npm run test:task2_5 --prefix apps/api
```

4) Run Task 2.5 standalone checker

```bash
python3 task_2_5_tests/main.py
```

5) Run Task 2.5 pytest

```bash
pytest task_2_5_tests -q
```

Task 2.5 Technical Workflow

1) Client sends a payload to `/api/streams/ingest`.
2) The route builds a request envelope from headers, query params, and JSON/raw body content.
3) The `StreamIngestionFacade` validates input and coordinates the ingestion flow.
4) The `StreamParserFactory` selects a parser by format.
5) The parser normalizes the payload into JSON/text/base64 fields.
6) The repository writes the event into `stream_ingestion_events`.
7) `/api/streams/events` and `/api/streams/health` verify the result.

Task 2.5 New Files (Purpose)

- `apps/api/routes/streams.js` — Task 2.5 health, ingest, and list endpoints.
- `apps/api/schemas/stream_ingestion_events.js` — Task 2.5 Sequelize model for the streaming landing table.
- `apps/api/services/streams/streamIngestionFacade.js` — Facade that coordinates validation, parser selection, and persistence.
- `apps/api/services/streams/streamParsers.js` — Factory-driven parser registry for JSON, CSV, XML, TXT, XLS/XLSX, and binary payloads.
- `apps/api/services/streams/streamEventRepository.js` — Repository layer for Task 2.5 persistence and queries.
- `apps/api/utils/streaming.js` — Shared streaming helpers for format detection and request normalization.
- `apps/api/tests/task_2_5.unit.test.js` — Task 2.5 unit tests for the facade and factory flow.
- `task_2_5_tests/test_task_2_5_api.py` — Task 2.5 pytest suite for API ingestion checks.
- `task_2_5_tests/main.py` — Task 2.5 standalone checker.
- `scripts/task_2_5_check.sh` — Task 2.5 CLI smoke test.
- `Task_2_5_Testing.md` — Task 2.5 test workflow and commands.
- `docs/uml/hypecheck_object_diagram.puml` — PlantUML object/component diagram for the project.
- `docs/uml/task_2_2_2_4_2_5_workflow.puml` — PlantUML workflow for Tasks 2.2, 2.4, and 2.5.
