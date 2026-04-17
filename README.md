# HypeCheck

HypeCheck is a **Social Media Event & Data Processing System** that measures the correlation between social media "hype" and financial reality. It analyzes sentiment from Reddit (historical backtesting) and Telegram (live monitoring) against asset prices to detect divergence, manipulation patterns, and FOMO-driven rallies.

## Project Structure

```
TIC2003/
├── apps/
│   ├── web/              # React + Vite Frontend (Dashboard)
│   ├── api/              # Node.js + Express Backend (REST API)
│   │   ├── database/     # Sequelize connection
│   │   └── schemas/      # 10 Sequelize model definitions
│   └── etl/              # Python ETL Pipeline (Sentiment + Price Ingestion)
├── docker-compose.yml
├── PROJECT.MD            # Project specification & architecture
└── ETL_DB_SCHEMA.md      # Database schema documentation
```

## Architecture

| Layer            | Tech                              | Role                                                |
| :--------------- | :-------------------------------- | :-------------------------------------------------- |
| **ETL Pipeline** | Python 3, VADER, Telethon, Pandas | Ingests social data, runs NLP, writes to PostgreSQL |
| **Database**     | PostgreSQL 15                     | Central data warehouse (11 tables, 18 indexes)      |
| **Backend API**  | Node.js, Express, Sequelize       | ORM models defined, REST endpoints in progress      |
| **Frontend**     | React, Vite, Tailwind CSS         | Interactive dual-axis charts (Price vs. Sentiment)  |

### Database Schema (10 Tables)

| Category              | Tables                                                                                  |
| :-------------------- | :-------------------------------------------------------------------------------------- |
| **Core Data**         | `assets`, `sentiment_logs`, `price_history`, `historical_prices`                        |
| **Session Tracking**  | `backtest_runs`, `live_sessions`                                                        |
| **Analysis & Output** | `author_credibility`, `sentiment_aggregations`, `sentiment_price_correlation`, `alerts`, `stream_ingestion_events` |

> See [ETL_DB_SCHEMA.md](ETL_DB_SCHEMA.md) for full schema documentation.

### Design Patterns

| Pattern | Implementation | Location |
| :------------- | :------------------------------------------------------------------------------ | :----------------------------------------------- |
| **Facade** | `StreamIngestionFacade.ingest()` coordinates validation, parsing, and persistence behind a single entry point | `apps/api/services/streams/streamIngestionFacade.js` |
| **Factory** | `StreamParserFactory.getParser(format)` selects the correct parser by format string without coupling callers to concrete classes | `apps/api/services/streams/streamParsers.js` |
| **Strategy** | Each parser subclass (`JsonStreamParser`, `CsvStreamParser`, etc.) implements the same `parse()` interface, making formats interchangeable | `apps/api/services/streams/streamParsers.js` |
| **Repository** | `StreamEventRepository` encapsulates all Sequelize ORM calls, keeping persistence logic out of the facade and route handlers | `apps/api/services/streams/streamEventRepository.js` |
| **Observer** | `AlertObserver` / `DatabaseAlertObserver` decouple anomaly detection from `insert_alert` — `LiveProcessor` notifies registered observers rather than calling the DB directly | `apps/etl/live_engine.py` |
| **Singleton** | One Sequelize connection pool (Node.js) and one psycopg2 `SimpleConnectionPool` (Python) are created once and shared across the process lifetime | `apps/api/database/index.js`, `apps/etl/db.py` |
| **Pipeline** | `BacktestRunner.run()` executes three sequential post-processing stages (price ingestion → aggregation → correlation) after CSV ingest | `apps/etl/backtest_engine.py` |
| **Template Method** | `TweetStreamParser.parse()` defines the fixed parsing skeleton; `extractText()`, `extractMetrics()`, `extractEntities()` are overridable hooks for subclass customisation | `apps/api/services/streams/streamParsers.js` |
| **Chain of Responsibility** | `TweetRequiredFieldsValidator → TweetTextLengthValidator → TweetTimestampValidator` — each handler validates one rule and passes to the next, decoupling validation concerns | `apps/api/services/streams/streamIngestionFacade.js` |
| **Builder** | `TweetEnvelopeBuilder` constructs the standard ingest envelope from a raw Twitter API v2 tweet object using fluent method chaining | `apps/api/services/streams/streamIngestionFacade.js` |
| **Decorator** | `RetryingStreamIngestionFacade` wraps any facade instance with exponential-backoff retry logic for transient DB errors without modifying the wrapped class | `apps/api/services/streams/streamIngestionFacade.js` |
| **Strategy** | `HmacSignatureVerifier` (production) and `NullSignatureVerifier` (development) implement the same `BaseSignatureVerifier` interface — active verifier selected at startup from `TWEET_WEBHOOK_SECRET` | `apps/api/middleware/tweetSignature.js` |
| **Null Object** | `NullSignatureVerifier` satisfies the full Strategy interface while doing nothing — eliminates null-check branches in the route handler and prints a dev-mode warning | `apps/api/middleware/tweetSignature.js` |

### ETL Modes

| Mode         | Data Source                      | Price Source             | Command                                      |
| :----------- | :------------------------------- | :----------------------- | :------------------------------------------- |
| **Backtest** | Reddit CSV (Kaggle/Pushshift)    | Yahoo Finance (yfinance) | `npm run dev:etl -- --mode backtest --clear` |
| **Live**     | Telegram channels (via Telethon) | Yahoo Finance (yfinance) | `npm run dev:etl`                            |

---

## Getting Started

### Prerequisites

- **Node.js** v18+
- **Python** 3.9+
- **Docker** (for PostgreSQL) or a local PostgreSQL 15 installation

<details>
<summary><strong>Python & PostgreSQL Installation Guide</strong></summary>

**For Windows:**

1. **Python:** Download from python.org. **Important:** Check "Add Python to PATH" during install.
2. **PostgreSQL:** Download from postgresql.org. Remember the password you set for `postgres`.
3. **Verify:** Open PowerShell → `python --version` and `psql --version`.

**For macOS:**

1. **Python:** `brew install python`
2. **PostgreSQL:** `brew install postgresql@15` then `brew services start postgresql@15`
3. **Verify:** `python3 --version` and `psql --version`
</details>

---

### Quick Start (Recommended)

**Step 1: Start PostgreSQL via Docker**

```bash
npm run docker:up
```

> This starts PostgreSQL on `localhost:5432` (user: `user`, password: `password`, database: `hypecheck`).

**Step 2: Install All Dependencies**

```bash
npm install           # Root dependencies
npm run setup:api     # Backend dependencies
npm run setup:web     # Frontend dependencies
npm run setup:etl     # Creates Python venv & installs packages
```

**Step 3: Configure Environment Variables**

Create `apps/etl/.env`:

```env
DATABASE_URL=postgres://user:password@localhost:5432/hypecheck

# Required only for Live Mode (Telegram)
TELEGRAM_API_ID=your_id
TELEGRAM_API_HASH=your_hash
```

**Step 4: Download Backtest Data**

Download the [WallStreetBets 2022 Dataset](https://www.kaggle.com/datasets/gpreda/wallstreetbets-2022) from Kaggle and place it in:

```
apps/etl/data/wallstreetbets_2022.csv
```

> The `data/` directory is gitignored — each team member must download the CSV separately (~221 MB).

**Step 5: Run Services (3 terminals)**

```bash
# Terminal 1 — Backend API
npm run dev:api            # → http://localhost:3000

# Terminal 2 — Frontend Dashboard
npm run dev:web            # → http://localhost:5173

# Terminal 3 — ETL Pipeline (pick one)
npm run dev:etl -- --mode backtest --clear   # Backtest mode (Reddit CSV)
npm run dev:etl                              # Live mode (Telegram)
```

#### What `--mode backtest --clear` Does

1. Initializes the database schema (11 tables, 18 indexes, creates if not exist)
2. Truncates all data tables (fresh start)
3. Seeds the `assets` table from `config/assets.json`
4. Creates a `backtest_runs` record with status tracking
5. Processes ~1.1M CSV rows through VADER sentiment analysis
6. Batch-inserts relevant records (500 rows/batch) into `sentiment_logs`
7. Upserts author credibility scores into `author_credibility`
8. Marks the backtest run as `completed` with final counts

---

### Without Docker (Local PostgreSQL)

1. Ensure PostgreSQL is running locally
2. Create the database: `CREATE DATABASE hypecheck;`
3. Update `apps/etl/.env` with your local PostgreSQL credentials
4. Follow Steps 2–5 above

---

## Scripts Reference

All scripts are run from the **root** directory:

| Command                                      | Description                                           |
| :------------------------------------------- | :---------------------------------------------------- |
| `npm run docker:up`                          | Starts PostgreSQL, API, and ETL in Docker containers  |
| `npm run docker:down`                        | Stops and removes Docker containers                   |
| `npm run dev:web`                            | Starts the React frontend (port 5173)                 |
| `npm run dev:api`                            | Starts the Express API (port 3000)                    |
| `npm run dev:etl`                            | Starts the ETL in **Live Mode** (Telegram)            |
| `npm run dev:etl -- --mode backtest --clear` | Starts the ETL in **Backtest Mode** (clears DB first) |
| `npm run test:task2_5:unit`                  | Runs the Task 2.5 Node unit test                      |
| `npm run setup:web`                          | Installs frontend dependencies                        |
| `npm run setup:api`                          | Installs backend dependencies                         |
| `npm run setup:etl`                          | Creates Python venv and installs requirements         |

## Task 2.5 Streaming Ingestion

Task 2.5 adds a generic PostgreSQL landing zone for future streaming payloads. The new API endpoints are:

- `GET /api/streams/health`
- `POST /api/streams/ingest`
- `GET /api/streams/events`

Supported formats:

- `json`
- `csv`
- `xml`
- `txt`
- `xls`
- `xlsx`
- `binary`

### Stream Structure Classification

Every ingested payload is automatically classified into one of three structural tiers based on its format. The classification is set by each parser and stored in the `structure_kind` column of `stream_ingestion_events`. It can also be overridden by the caller via the `x-structure-kind` request header or `structure_kind` query parameter.

| Structure Kind | Formats | Description |
| :------------------ | :-------------------------- | :--------------------------------------------------------------- |
| `structured` | `json`, `csv`, `xls`, `xlsx` | Fully parsed, machine-readable. Payload stored in `payload_json`. |
| `semi_structured` | `xml` | Partially parsed — structural summary in `payload_json`, raw document in `payload_text`. |
| `unstructured` | `txt`, `binary` | No structural parsing. Raw text in `payload_text` or Base64 bytes in `payload_base64`. |

### Files That Implement Structure Classification

| File | Role |
| :------------------------------------------------------------ | :----------------------------------------------------------------------------- |
| `apps/api/utils/streaming.js` | Defines `STRUCTURE_BY_FORMAT` map and `inferStructureKind()` resolver |
| `apps/api/services/streams/streamParsers.js` | Each parser subclass assigns `structure_kind` in its `parse()` result |
| `apps/api/services/streams/streamIngestionFacade.js` | Resolves final `structure_kind` (caller override or parser default) before persistence |
| `apps/api/services/streams/streamEventRepository.js` | Stores and filters records by `structure_kind` |
| `apps/api/schemas/stream_ingestion_events.js` | Defines `structure_kind` column with `isIn` validation constraint |
| `apps/api/routes/streams.js` | Exposes `structure_kind` as a filter on `GET /api/streams/events` |
| `apps/etl/db.py` | Creates the `stream_ingestion_events` table with `structure_kind` CHECK constraint |
| `apps/api/tests/task_2_5.unit.test.js` | Asserts `structure_kind` values in unit tests |

Reference docs:

- `Task_2_5_Testing.md`
- `docs/uml/hypecheck_object_diagram.puml`
- `docs/uml/task_2_2_2_4_2_5_workflow.puml`

## Tracked Assets

Configured in `apps/etl/config/assets.json`:

| Symbol | Name              | Type   | Keywords                        |
| :----- | :---------------- | :----- | :------------------------------ |
| BTC    | Bitcoin           | Crypto | bitcoin, btc, satoshi           |
| ETH    | Ethereum          | Crypto | ethereum, eth, vitalik          |
| TSLA   | Tesla             | Stock  | tesla, tsla, elon, musk         |
| NVDA   | NVIDIA            | Stock  | nvidia, nvda, ai, gpu           |
| GME    | GameStop          | Stock  | gme, gamestop, deepfuckingvalue |
| AMC    | AMC Entertainment | Stock  | amc, aron, cinema               |
