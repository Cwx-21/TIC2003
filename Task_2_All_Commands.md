# Task 2.2 + Task 2.4 — All Commands (Quick Reference)

This file consolidates all commands for Task 2.2 and Task 2.4 checks.

## 1) Start Services

```bash
# Start Postgres (Docker)
docker compose up -d postgres

# Initialize DB schema (one-time)
docker compose run --rm etl python -c "from db import init_db; init_db()"

# Start API with DB connection
DATABASE_URL=postgres://user:password@localhost:5432/hypecheck npm run dev:api
```

## 2) Health Check

```bash
# Health endpoint
curl -s -w '\nstatus=%{http_code}\n' http://localhost:3000/
```

## 3) Task 2.2 — CLI Script

```bash
# Task 2.2 endpoints quick check
bash scripts/task_2_2_check.sh
```

## 4) Task 2.4 — CLI Script

```bash
# Task 2.4 endpoints + CORS check
bash scripts/task_2_4_check.sh
```

## 5) Task 2.2 — Pytest

```bash
# Task 2.2 pytest suite
python3 -m pytest task_2_2_tests -q
```

## 6) Task 2.4 — Pytest

```bash
# Task 2.4 pytest suite
python3 -m pytest task_2_4_tests -q
```

## 7) Combined Checker (Task 2.2 + 2.4)

```bash
# Combined standalone checker
python3 task_2_4_tests/main.py
```

## 8) Optional Base URL Override

```bash
# Use a different API base URL for scripts
API_BASE_URL=http://localhost:3000 bash scripts/task_2_2_check.sh
API_BASE_URL=http://localhost:3000 bash scripts/task_2_4_check.sh
```

## 9) All-in-One Script

```bash
# Run health + Task 2.2/2.4 CLI checks + combined checker + pytest
bash scripts/task_2_all_check.sh
```

Optional base URL override:

```bash
API_BASE_URL=http://localhost:3000 bash scripts/task_2_all_check.sh
```

Note: `scripts/task_2_all_check.sh` runs the Task 2.4 pytest suite last because that suite intentionally verifies rate limiting.
