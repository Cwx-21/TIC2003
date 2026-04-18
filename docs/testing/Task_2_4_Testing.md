# Task 2.4 Testing Guide (CLI + Postman)

This guide provides a concise, reliable checklist to verify Task 2.4 endpoints and middleware in an academic, instructional tone.

## 0) Technical Workflow (Task 2.4)

1) Start PostgreSQL (Docker) and initialize schema.
2) Start the API with `DATABASE_URL` pointing at the local Postgres instance.
3) Verify the health endpoint returns 200.
4) Verify `/api/backtests` returns JSON.
5) Verify `/api/sessions` returns JSON.
6) Verify `/api/alerts` returns JSON.
7) Verify CORS allows `http://localhost:5173` (OPTIONS preflight).
8) Verify rate limiting returns `429` after exceeding the request limit.

## 1) Prerequisite: Database + API Running

### Start PostgreSQL (Docker)

```bash
docker compose up -d postgres
```

### Initialize Schema (one-time)

```bash
docker compose run --rm etl python -c "from db import init_db; init_db()"
```

### Optional: Seed Minimal Test Data (enables filter checks)

```bash
docker compose exec -T postgres psql -U user -d hypecheck -c "INSERT INTO backtest_runs (id, name, dataset_source, status, start_time) VALUES (9001, 'Sample Backtest', 'sample.csv', 'completed', NOW()) ON CONFLICT (id) DO NOTHING; INSERT INTO live_sessions (id, name, status, started_at) VALUES (9001, 'Sample Session', 'running', NOW()) ON CONFLICT (id) DO NOTHING; INSERT INTO sentiment_price_correlation (asset_symbol, time_bucket, bucket_interval, avg_sentiment, price_change_pct, sentiment_price_divergence, backtest_id, session_id) SELECT 'BTC', NOW(), '1h', 0.2, 1.5, 0.3, 9001, 9001 WHERE NOT EXISTS (SELECT 1 FROM sentiment_price_correlation WHERE backtest_id = 9001 AND session_id = 9001); INSERT INTO alerts (asset_symbol, alert_type, severity, message, event_timestamp, backtest_id, session_id) SELECT 'BTC', 'divergence', 'warning', 'Sample alert', NOW(), 9001, 9001 WHERE NOT EXISTS (SELECT 1 FROM alerts WHERE backtest_id = 9001 AND session_id = 9001);"
```

### Start API (local)

```bash
DATABASE_URL=postgres://user:password@localhost:5432/hypecheck npm run dev:api
```

Expected: API listens on `http://localhost:3000`.

## 2) CLI Tests (curl)

Health check:

```bash
curl -s http://localhost:3000/ | jq
```

Backtests:

```bash
curl -s "http://localhost:3000/api/backtests?limit=10" | jq
```

Sessions:

```bash
curl -s "http://localhost:3000/api/sessions?limit=10" | jq
```

Alerts:

```bash
curl -s "http://localhost:3000/api/alerts?limit=20" | jq
```

CORS preflight (must allow localhost:5173):

```bash
curl -i -X OPTIONS "http://localhost:3000/api/alerts" \
  -H "Origin: http://localhost:5173" \
  -H "Access-Control-Request-Method: GET"
```

If `curl` reports `Failed to connect`, the API is not running.

### Combined CLI Check (with clear comments)

```bash
# Health
curl -s -w '\nstatus=%{http_code}\n' http://localhost:3000/

# Backtests
curl -s -w '\nstatus=%{http_code}\n' "http://localhost:3000/api/backtests?limit=10"

# Sessions
curl -s -w '\nstatus=%{http_code}\n' "http://localhost:3000/api/sessions?limit=10"

# Alerts
curl -s -w '\nstatus=%{http_code}\n' "http://localhost:3000/api/alerts?limit=20"

# CORS preflight
curl -i -X OPTIONS "http://localhost:3000/api/alerts" \
  -H "Origin: http://localhost:5173" \
  -H "Access-Control-Request-Method: GET"
```

## 2.1) Pytest Checks (Task 2.4 Only)

Run pytest against Task 2.4 checks:

```bash
pytest task_2_4_tests -q
```

Optional environment variables:

- `API_BASE_URL` (default `http://localhost:3000`)
- `API_TIMEOUT` (seconds, default `5`)
- `SKIP_RATE_LIMIT=1` (skip rate-limit test)

## 2.2) Main Script Check (Task 2.4 Only)

Run the standalone checker:

```bash
python3 task_2_4_tests/main.py
```

Recommended order:

```bash
python3 task_2_4_tests/main.py
pytest task_2_4_tests -q
```

### Edge-Case Checks

Invalid parameters should still return 200 with a valid JSON shape:

```bash
curl -s "http://localhost:3000/api/alerts?limit=0&backtest_id=abc" | jq
```

Filter checks (applicable after seeding data):

```bash
curl -s "http://localhost:3000/api/backtests?id=9001" | jq
curl -s "http://localhost:3000/api/sessions?id=9001" | jq
curl -s "http://localhost:3000/api/alerts?asset_symbol=BTC&alert_type=divergence&severity=warning&backtest_id=9001&session_id=9001" | jq
```

### Rate-Limit Check (default = 120 requests/min)

Send 121 rapid requests and confirm at least one `429` response:

```bash
sh -c 'count=0; last=200; for i in $(seq 1 121); do last=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/api/alerts); if [ "$last" = "429" ]; then count=$((count+1)); fi; done; echo "429_count=$count last_status=$last"'
```

## 3) Postman Tests

### Import Collection

Import the following file in Postman:

`postman/HypeCheck_Task2_4.postman_collection.json`

### Set Base URL

In the collection variables (or environment), set:

- `baseUrl = http://localhost:3000`

### Run Requests

Run the requests in the following order:

1) Health Check
2) Backtests
3) Sessions
4) Alerts
5) CORS Preflight

Expected: 200 responses for GETs and a successful OPTIONS response with CORS headers when `Origin` is `http://localhost:5173`.

## 4) Common Failure Causes

- API not running (port 3000 closed).
- Wrong `DATABASE_URL` (queries fail with 500).
- CORS origin not on allowlist.
- Rate limit (429) after excessive requests.

## Task 2.4 — New Files (Purpose)

- `apps/api/database/index.js` — Task 2.4 DB connector used by the new endpoints.
- `apps/api/middleware/cors.js` — Task 2.4 CORS allowlist (permits `http://localhost:5173`).
- `apps/api/middleware/rateLimit.js` — Task 2.4 rate limiting middleware (protects `/api/*`).
- `apps/api/routes/backtests.js` — Task 2.4 `/api/backtests` endpoint.
- `apps/api/routes/sessions.js` — Task 2.4 `/api/sessions` endpoint.
- `apps/api/routes/alerts.js` — Task 2.4 `/api/alerts` endpoint.
- `apps/api/utils/query.js` — Task 2.4 query parsing helpers (limit/id/status filters).
- `postman/HypeCheck_Task2_4.postman_collection.json` — Task 2.4 Postman collection for quick tests.
- `Task_2_4_Testing.md` — Task 2.4 test workflow and commands.
- `task_2_4_tests/test_task_2_4_api.py` — Task 2.4 pytest suite (API checks only).
- `task_2_4_tests/main.py` — Task 2.4 standalone checker (no pytest required).

## Scripted Check (Task 2.4)

Run the script:

```bash
bash scripts/task_2_4_check.sh
```

Optional base URL override:

```bash
API_BASE_URL=http://localhost:3000 bash scripts/task_2_4_check.sh
```

For the Task 2.5 streaming ingestion workflow, commands, and unit test, see `Task_2_5_Testing.md`.
