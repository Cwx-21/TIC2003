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
apps/etl/venv/bin/python -m pytest task_2_4_tests -q
```

7) Run Task 2.4 standalone checker

```bash
apps/etl/venv/bin/python task_2_4_tests/main.py
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
