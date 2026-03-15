# HypeCheck ETL Database Architecture & Schema Documentation

This document outlines the database schema architecture for the HypeCheck system. It details the purpose, structure, and relationships of each table, demonstrating how the schema supports both historical backtesting and live sentiment monitoring against asset price movements.

---

## 1. Core Tables

### 1.1 `assets` (Asset Registry)

**Purpose:** Central registry for all tracked financial instruments (cryptocurrencies, stocks).

| Column       | Type         | Constraints                         | Description                        |
| :----------- | :----------- | :---------------------------------- | :--------------------------------- |
| `symbol`     | VARCHAR(20)  | **PK**                              | Ticker symbol (e.g., `BTC`, `GME`) |
| `name`       | VARCHAR(100) | NOT NULL                            | Full name (e.g., `Bitcoin`)        |
| `type`       | VARCHAR(10)  | NOT NULL, CHECK (`crypto`, `stock`) | Asset classification               |
| `keywords`   | JSONB        | DEFAULT `'[]'`                      | NLP keywords for text matching     |
| `subreddits` | JSONB        | DEFAULT `'[]'`                      | Monitored subreddits               |
| `is_active`  | BOOLEAN      | DEFAULT `TRUE`                      | Whether asset is actively tracked  |
| `created_at` | TIMESTAMP    | DEFAULT `CURRENT_TIMESTAMP`         | Record creation time               |

**Relationships:** Primary FK target for `sentiment_logs`, `price_history`, `historical_prices`, `sentiment_price_correlation`, and `alerts`.

---

### 1.2 `sentiment_logs` (Raw Sentiment Ingestion)

**Purpose:** Stores every processed message with its computed sentiment and credibility scores. The foundational, unaggregated data layer.

| Column              | Type         | Constraints                    | Description                                 |
| :------------------ | :----------- | :----------------------------- | :------------------------------------------ |
| `id`                | SERIAL       | **PK**                         | Auto-increment ID                           |
| `asset_symbol`      | VARCHAR(20)  | NOT NULL, FK → `assets`        | Referenced asset                            |
| `source`            | VARCHAR(20)  | NOT NULL                       | Data source (`reddit_backtest`, `telegram`) |
| `content`           | TEXT         |                                | Raw message text                            |
| `sentiment_score`   | FLOAT        |                                | VADER compound score (-1.0 to 1.0)          |
| `credibility_score` | FLOAT        |                                | Author credibility weight                   |
| `raw_metadata`      | JSONB        |                                | Source-specific metadata                    |
| `event_timestamp`   | TIMESTAMP    | NOT NULL                       | When the message was posted                 |
| `backtest_id`       | INT          | NULLABLE, FK → `backtest_runs` | NULL = live data                            |
| `session_id`        | INT          | NULLABLE, FK → `live_sessions` | Live session reference                      |
| `author_id`         | VARCHAR(255) | FK → `author_credibility`      | Author identifier                           |
| `created_at`        | TIMESTAMP    | DEFAULT `CURRENT_TIMESTAMP`    | Record creation time                        |

**Indexes:** `(asset_symbol, event_timestamp)`, `(backtest_id)`, `(session_id)`, `(author_id)`, `(source)`, `(asset_symbol, source, event_timestamp)`

---

### 1.3 `price_history` (Live Price Polling)

**Purpose:** Captures high-frequency price snapshots during live listening sessions.

| Column            | Type        | Constraints                    | Description            |
| :---------------- | :---------- | :----------------------------- | :--------------------- |
| `id`              | SERIAL      | **PK**                         | Auto-increment ID      |
| `asset_symbol`    | VARCHAR(20) | NOT NULL, FK → `assets`        | Referenced asset       |
| `price`           | FLOAT       | NOT NULL                       | Price at snapshot      |
| `currency`        | VARCHAR(5)  | DEFAULT `'USD'`                | Price currency         |
| `event_timestamp` | TIMESTAMP   | NOT NULL                       | Snapshot time          |
| `backtest_id`     | INT         | NULLABLE                       | Backtest reference     |
| `session_id`      | INT         | NULLABLE, FK → `live_sessions` | Live session reference |
| `created_at`      | TIMESTAMP   | DEFAULT `CURRENT_TIMESTAMP`    | Record creation time   |

**Indexes:** `(asset_symbol, event_timestamp)`, `(session_id)`

---

### 1.4 `historical_prices` (Backtest OHLCV Store)

**Purpose:** Stores daily OHLCV data fetched from yfinance for backtesting periods.

| Column         | Type        | Constraints             | Description              |
| :------------- | :---------- | :---------------------- | :----------------------- |
| `id`           | SERIAL      | **PK**                  | Auto-increment ID        |
| `asset_symbol` | VARCHAR(20) | NOT NULL, FK → `assets` | Referenced asset         |
| `price_open`   | FLOAT       |                         | Day's opening price      |
| `price_close`  | FLOAT       |                         | Day's closing price      |
| `price_high`   | FLOAT       |                         | Day's highest price      |
| `price_low`    | FLOAT       |                         | Day's lowest price       |
| `volume`       | FLOAT       |                         | Trading volume           |
| `event_date`   | DATE        | NOT NULL                | Calendar date            |
| `source`       | VARCHAR(30) |                         | Data source (`yfinance`) |

**Constraints:** UNIQUE `(asset_symbol, event_date)`
**Indexes:** `(asset_symbol, event_date)`

---

## 2. Execution & State Tracking Tables

### 2.1 `backtest_runs` (Simulation Tracking)

**Purpose:** Records metadata for historical backtest executions. Ensures simulated data is walled off from production live data.

| Column           | Type         | Constraints                                                   | Description             |
| :--------------- | :----------- | :------------------------------------------------------------ | :---------------------- |
| `id`             | SERIAL       | **PK**                                                        | Auto-increment ID       |
| `name`           | VARCHAR(100) |                                                               | Human-readable run name |
| `dataset_source` | VARCHAR(50)  |                                                               | CSV filename used       |
| `status`         | VARCHAR(20)  | DEFAULT `'running'`, CHECK (`running`, `completed`, `failed`) | Execution state         |
| `start_time`     | TIMESTAMP    |                                                               | When run started        |
| `end_time`       | TIMESTAMP    |                                                               | When run finished       |
| `parameters`     | JSONB        |                                                               | Run configuration       |
| `total_rows`     | INT          |                                                               | Total CSV rows          |
| `processed_rows` | INT          | DEFAULT `0`                                                   | Rows processed so far   |
| `error_count`    | INT          | DEFAULT `0`                                                   | Error count             |
| `created_at`     | TIMESTAMP    | DEFAULT `CURRENT_TIMESTAMP`                                   | Record creation time    |

---

### 2.2 `live_sessions` (Live Ingestion Tracking)

**Purpose:** Records metadata for active and past Telegram listening sessions.

| Column                     | Type         | Constraints                                                             | Description               |
| :------------------------- | :----------- | :---------------------------------------------------------------------- | :------------------------ |
| `id`                       | SERIAL       | **PK**                                                                  | Auto-increment ID         |
| `name`                     | VARCHAR(100) |                                                                         | Session name              |
| `status`                   | VARCHAR(20)  | DEFAULT `'running'`, CHECK (`running`, `completed`, `stopped`, `error`) | Execution state           |
| `channels_monitored`       | JSONB        |                                                                         | Telegram channels tracked |
| `assets_tracked`           | JSONB        |                                                                         | Assets monitored          |
| `started_at`               | TIMESTAMP    | DEFAULT `CURRENT_TIMESTAMP`                                             | Session start             |
| `ended_at`                 | TIMESTAMP    |                                                                         | Session end               |
| `total_messages_processed` | INT          | DEFAULT `0`                                                             | Message count             |
| `parameters`               | JSONB        |                                                                         | Session configuration     |

---

## 3. Analysis & Aggregation Tables

### 3.1 `author_credibility` (Whale Watcher Engine)

**Purpose:** Tracks user reputation across platforms to identify bots and spam.

| Column                 | Type         | Constraints        | Description                     |
| :--------------------- | :----------- | :----------------- | :------------------------------ |
| `author_id`            | VARCHAR(255) | **PK** (composite) | User identifier                 |
| `source`               | VARCHAR(20)  | **PK** (composite) | Platform (`reddit`, `telegram`) |
| `baseline_credibility` | FLOAT        | DEFAULT `1.0`      | Core score modifier             |
| `total_posts`          | INT          | DEFAULT `0`        | Lifetime post count             |
| `spam_flags`           | INT          | DEFAULT `0`        | Spam detection count            |
| `is_bot`               | BOOLEAN      | DEFAULT `FALSE`    | Bot classification              |
| `last_evaluated_at`    | TIMESTAMP    |                    | Last credibility update         |

---

### 3.2 `sentiment_aggregations` (Pre-computed Time Buckets)

**Purpose:** Stores pre-calculated, time-bucketed sentiment averages. Reduces API computation from aggregating thousands of raw logs to reading a few rows.

| Column                   | Type        | Constraints                 | Description                  |
| :----------------------- | :---------- | :-------------------------- | :--------------------------- |
| `id`                     | SERIAL      | **PK**                      | Auto-increment ID            |
| `asset_symbol`           | VARCHAR(20) | NOT NULL, FK → `assets`     | Referenced asset             |
| `time_bucket`            | TIMESTAMP   | NOT NULL                    | Bucket start time            |
| `bucket_interval`        | VARCHAR(10) | NOT NULL, DEFAULT `'1h'`    | Interval (`1h`, `4h`, `1d`)  |
| `avg_sentiment_score`    | FLOAT       |                             | Simple arithmetic mean       |
| `weighted_avg_sentiment` | FLOAT       |                             | Credibility-weighted mean    |
| `message_volume`         | INT         |                             | Number of messages in bucket |
| `backtest_id`            | INT         | NULLABLE                    | Backtest reference           |
| `session_id`             | INT         | NULLABLE                    | Live session reference       |
| `created_at`             | TIMESTAMP   | DEFAULT `CURRENT_TIMESTAMP` | Record creation time         |

**Indexes:** `(asset_symbol, time_bucket)`

---

### 3.3 `sentiment_price_correlation` (Divergence Analysis)

**Purpose:** Stores the mathematical correlation between sentiment and price movements. Measures divergence to identify market manipulation or FOMO spikes.

| Column                       | Type        | Constraints                 | Description                   |
| :--------------------------- | :---------- | :-------------------------- | :---------------------------- |
| `id`                         | SERIAL      | **PK**                      | Auto-increment ID             |
| `asset_symbol`               | VARCHAR(20) | NOT NULL, FK → `assets`     | Referenced asset              |
| `time_bucket`                | TIMESTAMP   | NOT NULL                    | Bucket start time             |
| `bucket_interval`            | VARCHAR(10) | NOT NULL, DEFAULT `'1h'`    | Interval                      |
| `avg_sentiment`              | FLOAT       |                             | Simple sentiment mean         |
| `weighted_sentiment`         | FLOAT       |                             | Credibility-weighted mean     |
| `price_at_bucket`            | FLOAT       |                             | Closing price for bucket      |
| `price_change_pct`           | FLOAT       |                             | % change from previous bucket |
| `sentiment_price_divergence` | FLOAT       |                             | Sentiment vs price delta      |
| `message_volume`             | INT         |                             | Messages in bucket            |
| `backtest_id`                | INT         | NULLABLE                    | Backtest reference            |
| `session_id`                 | INT         | NULLABLE                    | Live session reference        |
| `created_at`                 | TIMESTAMP   | DEFAULT `CURRENT_TIMESTAMP` | Record creation time          |

**Indexes:** `(asset_symbol, time_bucket)`, `(backtest_id)`, `(session_id)`

---

### 3.4 `alerts` (Anomaly Events)

**Purpose:** Logs specific, actionable events detected by the correlation engine. Used to populate alert feeds on the dashboard.

| Column            | Type        | Constraints                                                                        | Description                |
| :---------------- | :---------- | :--------------------------------------------------------------------------------- | :------------------------- |
| `id`              | SERIAL      | **PK**                                                                             | Auto-increment ID          |
| `asset_symbol`    | VARCHAR(20) | NOT NULL, FK → `assets`                                                            | Referenced asset           |
| `alert_type`      | VARCHAR(30) | NOT NULL, CHECK (`divergence`, `volume_spike`, `sentiment_reversal`, `spam_surge`) | Event classification       |
| `severity`        | VARCHAR(10) | DEFAULT `'info'`, CHECK (`info`, `warning`, `critical`)                            | Severity level             |
| `message`         | TEXT        |                                                                                    | Human-readable description |
| `details`         | JSONB       |                                                                                    | Structured alert metadata  |
| `event_timestamp` | TIMESTAMP   | NOT NULL                                                                           | When the anomaly occurred  |
| `backtest_id`     | INT         | NULLABLE                                                                           | Backtest reference         |
| `session_id`      | INT         | NULLABLE                                                                           | Live session reference     |
| `is_acknowledged` | BOOLEAN     | DEFAULT `FALSE`                                                                    | Dashboard acknowledgment   |
| `created_at`      | TIMESTAMP   | DEFAULT `CURRENT_TIMESTAMP`                                                        | Record creation time       |

**Indexes:** `(asset_symbol, event_timestamp)`, `(alert_type, created_at)`

---

## 4. Index Summary

| Table                         | Index                                  | Columns                                        |
| :---------------------------- | :------------------------------------- | :--------------------------------------------- |
| `sentiment_logs`              | `idx_sentiment_logs_asset_time`        | `(asset_symbol, event_timestamp DESC)`         |
| `sentiment_logs`              | `idx_sentiment_logs_backtest`          | `(backtest_id)`                                |
| `sentiment_logs`              | `idx_sentiment_logs_session`           | `(session_id)`                                 |
| `sentiment_logs`              | `idx_sentiment_logs_author`            | `(author_id)`                                  |
| `sentiment_logs`              | `idx_sentiment_logs_source`            | `(source)`                                     |
| `sentiment_logs`              | `idx_sentiment_logs_asset_source_time` | `(asset_symbol, source, event_timestamp DESC)` |
| `price_history`               | `idx_price_history_asset_time`         | `(asset_symbol, event_timestamp DESC)`         |
| `price_history`               | `idx_price_history_session`            | `(session_id)`                                 |
| `historical_prices`           | `idx_hist_price_asset_date`            | `(asset_symbol, event_date DESC)`              |
| `sentiment_aggregations`      | `idx_sentiment_agg_asset_time`         | `(asset_symbol, time_bucket DESC)`             |
| `sentiment_price_correlation` | `idx_correlation_asset_time`           | `(asset_symbol, time_bucket DESC)`             |
| `sentiment_price_correlation` | `idx_correlation_backtest`             | `(backtest_id)`                                |
| `sentiment_price_correlation` | `idx_correlation_session`              | `(session_id)`                                 |
| `alerts`                      | `idx_alerts_asset_time`                | `(asset_symbol, event_timestamp DESC)`         |
| `alerts`                      | `idx_alerts_type`                      | `(alert_type, created_at DESC)`                |

**Total: 10 tables, 15 indexes**

---

## Architecture Notes

**Pre-computation strategy:** Heavy reliance on ETL pre-computation. Instead of computing `SELECT AVG(sentiment) GROUP BY hour` on millions of rows at API query time, the Python ETL writes to `sentiment_aggregations` and `sentiment_price_correlation` asynchronously. This ensures API response times remain constant regardless of dataset size.

**Price data source:** All historical and live prices use **yfinance** (free, no API key). Crypto tickers use Yahoo Finance pairs (e.g., `BTC-USD`), stocks use tickers directly (e.g., `TSLA`).

**Sequelize ORM note:** The API layer (`apps/api/schemas/`) mirrors this schema with Sequelize models. One divergence: `author_credibility` uses an auto-increment INTEGER `author_id` as sole PK in Sequelize instead of the composite `(author_id VARCHAR, source)` PK defined here. This is because Sequelize does not natively support composite foreign key associations — `sentiment_logs.belongsTo(author_credibility)` requires a single-column reference. When querying by platform, filter with `{ where: { author_id, source } }` manually.
