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

| Layer            | Tech                                 | Role                                                |
| :--------------- | :----------------------------------- | :-------------------------------------------------- |
| **ETL Pipeline** | Python 3.12, VADER, Telethon, Pandas | Ingests social data, runs NLP, writes to PostgreSQL |
| **Database**     | PostgreSQL 15                        | Central data warehouse (10 tables, 15 indexes)      |
| **Backend API**  | Node.js 22, Express, Sequelize       | 7 REST endpoints live at `168.144.37.237/api`       |
| **Frontend**     | React 19, Vite 7, Tailwind CSS       | Interactive dual-axis charts (Price vs. Sentiment)  |

### Database Schema (10 Tables)

| Category              | Tables                                                                                  |
| :-------------------- | :-------------------------------------------------------------------------------------- |
| **Core Data**         | `assets`, `sentiment_logs`, `price_history`, `historical_prices`                        |
| **Session Tracking**  | `backtest_runs`, `live_sessions`                                                        |
| **Analysis & Output** | `author_credibility`, `sentiment_aggregations`, `sentiment_price_correlation`, `alerts` |

> See [ETL_DB_SCHEMA.md](ETL_DB_SCHEMA.md) for full schema documentation.

### ETL Modes

| Mode         | Data Source                      | Price Source             | Command                                      |
| :----------- | :------------------------------- | :----------------------- | :------------------------------------------- |
| **Backtest** | Reddit CSV (Kaggle/Pushshift)    | Yahoo Finance (yfinance) | `npm run dev:etl -- --mode backtest --clear` |
| **Live**     | Telegram channels (via Telethon) | Yahoo Finance (yfinance) | `npm run dev:etl`                            |

---

## Getting Started

### Prerequisites

- **Node.js** v22+
- **Python** 3.12+
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

1. Initializes the database schema (10 tables, 15 indexes, creates if not exist)
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
| `npm run setup:web`                          | Installs frontend dependencies                        |
| `npm run setup:api`                          | Installs backend dependencies                         |
| `npm run setup:etl`                          | Creates Python venv and installs requirements         |

## Live Server

The backend API and database are deployed on a shared DigitalOcean Droplet. It can be use instead of running the full stack locally.

| What     | URL                                |
| :------- | :--------------------------------- |
| Frontend | `http://168.144.37.237`            |
| API root | `http://168.144.37.237/api/assets` |

**Available endpoints:**

```
GET /api/assets
GET /api/sentiment/:symbol
GET /api/prices/:symbol
GET /api/correlation/:symbol
GET /api/alerts
GET /api/backtests
GET /api/sessions
```

**Database access** (TablePlus / DBeaver / pgAdmin):

- Host: `168.144.37.237` · Port: `5432` · User: `user` · Password: `password` · DB: `hypecheck`

**Frontend-only local dev** (no need to run Docker or API locally):

set axios request url to http://168.144.37.237

Then just run `npm run dev:web`.

---

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
