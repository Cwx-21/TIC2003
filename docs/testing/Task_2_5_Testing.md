# Task 2.5 Testing Guide (Streaming Ingestion + Unit Test)

This guide verifies the new generic streaming-ingestion flow that accepts structured, semi-structured, and unstructured payloads for PostgreSQL persistence.

## 0) Technical Workflow (Task 2.5)

1. Start PostgreSQL and initialize the schema.
2. Start the API with `DATABASE_URL` pointing at the local Postgres instance.
3. Verify `/api/streams/health` reports the supported formats.
4. Verify `/api/streams/ingest` accepts `json`, `csv`, `xml`, `txt`, and `xlsx` payloads.
5. Verify `/api/streams/events` returns recent ingestion records.
6. Run the unit test that validates the facade/factory parser flow.
7. Run the Task 2.5 pytest suite.

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

Streams health:

```bash
curl -s "http://localhost:3000/api/streams/health" | jq
```

JSON ingest:

```bash
curl -s -H "Content-Type: application/json" \
  --data-binary '{"source":"manual-json","stream_name":"task-2-5","format":"json","metadata":{"source":"cli"},"payload":[{"asset":"BTC","score":0.8}]}' \
  "http://localhost:3000/api/streams/ingest" | jq
```

CSV ingest:

```bash
curl -s -H "Content-Type: text/csv" \
  --data-binary $'symbol,price\nBTC,65000\nETH,3000' \
  "http://localhost:3000/api/streams/ingest?source=manual-csv&stream_name=task-2-5&format=csv" | jq
```

XML ingest:

```bash
curl -s -H "Content-Type: application/xml" \
  --data-binary '<feed><asset symbol="BTC">bullish</asset></feed>' \
  "http://localhost:3000/api/streams/ingest?source=manual-xml&stream_name=task-2-5&format=xml" | jq
```

Text ingest:

```bash
curl -s -H "Content-Type: text/plain" \
  --data-binary $'Trader notes\nWatch BTC momentum' \
  "http://localhost:3000/api/streams/ingest?source=manual-text&stream_name=task-2-5&format=txt" | jq
```

Spreadsheet/binary ingest:

```bash
printf 'PK\003\004mock-xlsx-payload' | \
curl -s -H "Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" \
  --data-binary @- \
  "http://localhost:3000/api/streams/ingest?source=manual-xlsx&stream_name=task-2-5&format=xlsx" | jq
```

Events query:

```bash
curl -s "http://localhost:3000/api/streams/events?source=manual-json&include_payload=true&limit=10" | jq
```

## 3) Scripted Check

```bash
bash scripts/task_2_5_check.sh
```

Optional base URL override:

```bash
API_BASE_URL=http://localhost:3000 bash scripts/task_2_5_check.sh
```

## 4) Unit Test

```bash
npm run test:task2_5 --prefix apps/api
```

This validates:

- the parser factory chooses the correct parser
- the facade normalizes payloads before persistence
- missing required source data is rejected

## 5) Pytest Checks

```bash
pytest task_2_5_tests -q
python3 task_2_5_tests/main.py
```

Recommended order:

```bash
npm run test:task2_5 --prefix apps/api
python3 task_2_5_tests/main.py
pytest task_2_5_tests -q
```

## 6) Supported Formats

- `json` for structured API/event payloads
- `csv` for structured tabular rows
- `xml` for semi-structured document feeds
- `txt` for unstructured note/log streaming
- `xls` and `xlsx` for spreadsheet/binary uploads
- `binary` for generic raw payload preservation

## 7) PlantUML Files

- `docs/uml/hypecheck_object_diagram.puml`
- `docs/uml/task_2_2_2_4_2_5_workflow.puml`
