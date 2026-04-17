# Task 2.2 Testing Guide (CLI + Pytest)

This guide provides an academic, instructional checklist to validate Task 2.2 endpoints and response shape.

## 0) Technical Workflow (Task 2.2)

1) Start PostgreSQL (Docker) and initialize schema.
2) Start the API with `DATABASE_URL` pointing at the local Postgres instance.
3) Verify `/api/assets` returns JSON.
4) Verify `/api/sentiment/:symbol` returns JSON.
5) Verify `/api/prices/:symbol` returns JSON.
6) Verify `/api/correlation/:symbol` returns JSON.

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

If 404 responses appear, ensure the Task 2.2 routes are mounted in `apps/api/index.js`.

## 2) CLI Tests (curl)

Assets:

```bash
curl -s "http://localhost:3000/api/assets?limit=10" | jq
```

Sentiment:

```bash
curl -s "http://localhost:3000/api/sentiment/BTC?limit=10" | jq
```

Prices:

```bash
curl -s "http://localhost:3000/api/prices/BTC?limit=10" | jq
```

Correlation:

```bash
curl -s "http://localhost:3000/api/correlation/BTC?limit=10" | jq
```

### Combined CLI Check (with clear comments)

```bash
# Assets
curl -s -w '\nstatus=%{http_code}\n' "http://localhost:3000/api/assets?limit=10"

# Sentiment
curl -s -w '\nstatus=%{http_code}\n' "http://localhost:3000/api/sentiment/BTC?limit=10"

# Prices
curl -s -w '\nstatus=%{http_code}\n' "http://localhost:3000/api/prices/BTC?limit=10"

# Correlation
curl -s -w '\nstatus=%{http_code}\n' "http://localhost:3000/api/correlation/BTC?limit=10"
```

## 3) Pytest Checks (Task 2.2 Only)

```bash
pytest task_2_2_tests -q
```

Optional environment variables:

- `API_BASE_URL` (default `http://localhost:3000`)
- `API_TIMEOUT` (seconds, default `5`)

## 4) Combined Checker (Task 2.2 + 2.4)

```bash
python3 task_2_4_tests/main.py
```

For the new streaming-ingestion checks, see `Task_2_5_Testing.md`.

## Scripted Check (Task 2.2)

Run the script:

```bash
bash scripts/task_2_2_check.sh
```

Optional base URL override:

```bash
API_BASE_URL=http://localhost:3000 bash scripts/task_2_2_check.sh
```
