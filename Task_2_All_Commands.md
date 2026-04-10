# Task 2.2 + Task 2.4 + Task 2.5 — All Commands (Quick Reference)

This file consolidates all commands for Task 2.2, Task 2.4, and Task 2.5 checks.

## 0) Order Rule

Use this execution order:

```bash
npm run test:task2_5 --prefix apps/api
python3 task_2_5_tests/main.py
pytest task_2_5_tests -q
python3 task_2_4_tests/main.py
pytest task_2_4_tests -q
```

Reason:
- Task 2.5 has a unit test plus ingestion checks that should run before rate-limit-sensitive tests
- `task_2_4_tests` includes the rate-limit test
- `main.py` should run before Task 2.4 pytest
- Task 2.4 pytest should run last if more API checks will follow
- `pytest ...` is the working command in this shell

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
pytest task_2_2_tests -q
```

## 6) Task 2.5 — CLI Script

```bash
# Task 2.5 streaming ingestion quick check
bash scripts/task_2_5_check.sh
```

## 7) Task 2.5 — Unit Test

```bash
# Task 2.5 parser/facade unit test
npm run test:task2_5 --prefix apps/api
```

## 8) Task 2.5 — Standalone Checker

```bash
# Task 2.5 standalone checker
python3 task_2_5_tests/main.py
```

## 9) Task 2.5 — Pytest

```bash
# Task 2.5 pytest suite
pytest task_2_5_tests -q
```

## 10) Combined Checker (Task 2.2 + 2.4)

```bash
# Combined standalone checker
# Run this before Task 2.4 pytest
python3 task_2_4_tests/main.py
```

## 11) Task 2.4 — Pytest

```bash
# Task 2.4 pytest suite
# Run this last because it triggers the rate limit check
pytest task_2_4_tests -q
```

## 12) Optional Base URL Override

```bash
# Use a different API base URL for scripts
API_BASE_URL=http://localhost:3000 bash scripts/task_2_2_check.sh
API_BASE_URL=http://localhost:3000 bash scripts/task_2_4_check.sh
API_BASE_URL=http://localhost:3000 bash scripts/task_2_5_check.sh
```

## 13) All-in-One Script

```bash
# Run health + Task 2.2/2.4/2.5 CLI checks + unit tests + checkers + pytest
bash scripts/task_2_all_check.sh
```

Optional base URL override:

```bash
API_BASE_URL=http://localhost:3000 bash scripts/task_2_all_check.sh
```

Note: `scripts/task_2_all_check.sh` runs Task 2.5 checks before Task 2.4 pytest and keeps Task 2.4 pytest last.

## 14) Safe Sequential Demo Order

If the commands are run one by one in the terminal, use this exact order:

```bash
# Start Postgres
docker compose up -d postgres

# Initialize schema
docker compose run --rm etl python -c "from db import init_db; init_db()"

# Start API in another terminal, or in the background
DATABASE_URL=postgres://user:password@localhost:5432/hypecheck npm run dev:api

# Health check
curl -s -w '\nstatus=%{http_code}\n' http://localhost:3000/

# Task 2.2 endpoint checks
bash scripts/task_2_2_check.sh

# Task 2.4 endpoint checks
bash scripts/task_2_4_check.sh

# Task 2.5 endpoint checks
bash scripts/task_2_5_check.sh

# Task 2.2 pytest
pytest task_2_2_tests -q

# Task 2.5 unit test
npm run test:task2_5 --prefix apps/api

# Task 2.5 checker
python3 task_2_5_tests/main.py

# Task 2.5 pytest
pytest task_2_5_tests -q

# Combined checker
python3 task_2_4_tests/main.py

# Task 2.4 pytest last
pytest task_2_4_tests -q
```

If the sequence is run again immediately:
- restart the API, or
- wait about 60 seconds for the rate-limit window to reset

## 15) PlantUML

```bash
# PlantUML source files
ls docs/uml
```

Files:

- `docs/uml/hypecheck_object_diagram.puml`
- `docs/uml/task_2_2_2_4_2_5_workflow.puml`

## 16) Port 3000 Troubleshooting

If the API fails with `EADDRINUSE`, port `3000` is already being used by another process.

```bash
# See what is using port 3000
lsof -nP -iTCP:3000 -sTCP:LISTEN
```

Then stop the old process with its PID:

```bash
# Replace <PID> with the process ID from lsof
kill <PID>
```

Then start the API again:

```bash
DATABASE_URL=postgres://user:password@localhost:5432/hypecheck npm run dev:api
```
