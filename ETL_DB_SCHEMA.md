# HypeCheck ETL Database Architecture & Schema Documentation

This document outlines the database schema architecture for the HypeCheck system. It details the purpose, structure, and relationships of each table, demonstrating how the schema supports both historical backtesting and live sentiment monitoring against asset price movements.

## 1. Core Tables

### 1.1 `assets` (Asset Registry)

**Purpose:** Acts as the central registry for all tracked financial instruments (cryptocurrencies, stocks).
**Business Logic:** Replaces hardcoded JSON configuration files, allowing the system to dynamically adjust which assets are being monitored without requiring code deployments or service restarts.
**Key Fields:**

- `symbol` (PK): The primary identifier (e.g., `BTC`, `GME`).
- `type`: Enum for asset classification (`crypto`, `stock`).
- `keywords`: JSONB array of strings used by the NLP engine to identify asset mentions in raw text.
  **Relationships:** Acts as the primary foreign key target for `sentiment_logs`, `price_history`, `historical_prices`, `sentiment_price_correlation`, and `alerts`.

### 1.2 `sentiment_logs` (Raw Sentiment Ingestion)

**Purpose:** Stores every individual message processed by the ETL pipeline along with its computed sentiment and credibility scores.
**Business Logic:** Serves as the foundational, unaggregated data layer. It supports deep audits of specific timeframes and the recalculation of aggregate scores if the NLP algorithms are updated.
**Key Fields:**

- `content`: The raw text of the message.
- `sentiment_score`: The VADER compound score (-1.0 to 1.0).
- `credibility_score`: The author's spam/bot weighting.
- `event_timestamp`: The actual time the message was posted (crucial for backtest accuracy).
  **Relationships:**
- `asset_symbol` -> `assets(symbol)`
- `author_id` -> `author_credibility(author_id)`
- `backtest_id` -> `backtest_runs(id)` (Nullable: NULL denotes live data)
- `session_id` -> `live_sessions(id)` (Nullable)

### 1.3 `price_history` (Live Price Polling)

**Purpose:** Captures high-frequency price snapshots recorded during live listening sessions.
**Business Logic:** Stores the real-time financial reality that live sentiment is measured against.
**Constraints:** Unique constraint on `(asset_symbol, event_timestamp)` to prevent duplicate entries if the polling loop fires multiple times in the same second.
**Relationships:**

- `asset_symbol` -> `assets(symbol)`
- `session_id` -> `live_sessions(id)`

### 1.4 `historical_prices` (Backtest Price Bulk Store)

**Purpose:** Dedicated storage for OHLCV (Open, High, Low, Close, Volume) data imported from CSVs or APIs for historical periods.
**Business Logic:** Separated from `price_history` because bulk historical data is typically generated at daily/hourly granularity rather than the high-frequency polling frequency of live data, requiring different indexing and querying strategies.
**Key Fields:**

- `price_open`, `price_close`, `price_high`, `price_low`, `volume`.
- `event_date`: Time identifier for the candle.
  **Relationships:** `asset_symbol` -> `assets(symbol)`

## 2. Execution & State Tracking Tables

### 2.1 `live_sessions` (Live Ingestion Tracking)

**Purpose:** Records metadata for active and past live Telegram listening sessions.
**Business Logic:** Enables querying data by specific time periods or system runs. If a session crashes or ingested bad data, its associated records can be easily isolated or purged.
**Key Fields:**

- `status`: Execution state (`running`, `completed`, `error`).
- `channels_monitored`: JSONB array of Telegram channels tracked during this run.

### 2.2 `backtest_runs` (Simulation Tracking)

**Purpose:** Records metadata for historical backtest executions.
**Business Logic:** Ensures simulated data (e.g., 2021 Reddit archives injected into the DB in 2026) is strictly walled off from production live data.
**Key Fields:**

- `dataset_source`: Name or path of the CSV/dataset used.
- `total_rows`, `processed_rows`: Used for progress tracking in the UI.

## 3. Analysis & Aggregation Tables

### 3.1 `author_credibility` ("Whale Watcher" Engine)

**Purpose:** The master ledger tracking user reputation across platforms to spot bots and spam rings.
**Business Logic:** Replaces individual, stateless post credibility scoring. By tracking authors over time, the system can dynamically lower the credibility weight of users who consistently post "pump" keywords right before price drops.
**Key Fields:**

- `baseline_credibility`: The core score modifier.
- `spam_flags`, `is_bot`: Identifiers for suppression algorithms.
  **Relationships:** Referenced by `sentiment_logs`.

### 3.2 `sentiment_aggregations` (UI Pre-computation)

**Purpose:** Stores pre-calculated, time-bucketed (e.g., 1-minute, 1-hour) sentiment averages.
**Business Logic:** Drastically reduces the computational load on the Node.js API. Instead of aggregating 10,000 raw logs to render a 1-day chart, the API fetches 24 rows from this table.
**Key Fields:**

- `time_bucket`: The truncated timeframe.
- `weighted_avg_sentiment`: The final, credibility-adjusted sentiment score for the bucket.

### 3.3 `sentiment_price_correlation` (Divergence Analysis)

**Purpose:** Stores the final mathematical correlation between sentiment shifts and price movements.
**Business Logic:** This is the core intellectual property of HypeCheck. It measures the delta between sentiment and price to identify divergence events (e.g., massive social hype while the price is actively falling).
**Key Fields:**

- `price_change_pct`: Shift in price from the previous bucket.
- `sentiment_price_divergence`: Formatted metric highlighting anomalies.

### 3.4 `alerts` (Anomaly Events)

**Purpose:** A log of specific, actionable events detected by the system.
**Business Logic:** Used to populate user dashboards or trigger external notifications when the model identifies significant market manipulation or FOMO spikes.
**Key Fields:**

- `alert_type`: (`divergence`, `volume_spike`).

---

## Architecture Summary & Justification

**Is this schema sufficient for current requirements?**
Yes. This schema transitions the application from a raw data dump into an analytical engine. By introducing state management (`live_sessions`, `backtest_runs`), separating raw data from aggregated data (`sentiment_aggregations`), and codifying the analysis (`sentiment_price_correlation`), it perfectly aligns with the requirements outlined in PROJECT.MD for historical replay and live signal-to-noise isolation.

**Scalability and Performance Trade-offs:**
The primary design decision made here is the **heavy reliance on ETL pre-computation.**
Instead of calculating sentiment distributions on-the-fly (`SELECT AVG(sentiment) ... GROUP BY hour`), we are trading storage space (by writing to `sentiment_aggregations` and `sentiment_price_correlation`) for read speed.

_Why:_ The Node.js API serving the React frontend scales poorly when performing heavy aggregation on millions of JSONB/Text rows in PostgreSQL. By pre-computing these buckets asynchronously in the Python ETL background workers, API response times to the UI will theoretically remain constant (O(1)) regardless of how large the underlying raw datasets grow.

**Future Extension Points:**

1. **Multi-Source Support:** The `source` columns allow easy integration of X (Twitter), Discord, or TikTok metadata without changing the core structures.
2. **Machine Learning Integrations:** The `sentiment_price_correlation` table provides a perfectly structured, clean dataset that could be used to train predictive ML models in the future.
