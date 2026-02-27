import os
import psycopg2
from psycopg2.extras import Json, execute_values
from psycopg2.pool import SimpleConnectionPool
import time
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Connection Pool (Singleton)
# ---------------------------------------------------------------------------
_pool = None

def _get_pool():
    """Returns a singleton connection pool. Creates one if it doesn't exist."""
    global _pool
    if _pool is None or _pool.closed:
        try:
            _pool = SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                dsn=os.getenv('DATABASE_URL')
            )
        except Exception as e:
            print(f"Error creating connection pool: {e}")
            return None
    return _pool

def get_db_connection():
    """Gets a connection from the pool."""
    pool = _get_pool()
    if pool:
        try:
            return pool.getconn()
        except Exception as e:
            print(f"Error getting connection from pool: {e}")
            return None
    return None

def release_connection(conn):
    """Returns a connection back to the pool."""
    pool = _get_pool()
    if pool and conn:
        pool.putconn(conn)

# ---------------------------------------------------------------------------
# Schema Initialization
# ---------------------------------------------------------------------------
def init_db():
    """Initializes the database tables if they don't exist."""
    print("Initializing Database Schema...")
    conn = get_db_connection()
    if not conn:
        print("Failed to connect to DB for initialization.")
        return

    # --- Table definitions (order matters for FK references) ---
    tables = [
        # 1. assets — central registry (must be first, others FK to it)
        """
        CREATE TABLE IF NOT EXISTS assets (
            symbol VARCHAR(20) PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            type VARCHAR(10) NOT NULL CHECK (type IN ('crypto', 'stock')),
            keywords JSONB DEFAULT '[]',
            subreddits JSONB DEFAULT '[]',
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        # 2. backtest_runs — session metadata for backtests
        """
        CREATE TABLE IF NOT EXISTS backtest_runs (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100),
            dataset_source VARCHAR(50),
            status VARCHAR(20) DEFAULT 'running'
                CHECK (status IN ('running', 'completed', 'failed')),
            start_time TIMESTAMP,
            end_time TIMESTAMP,
            parameters JSONB,
            total_rows INT,
            processed_rows INT DEFAULT 0,
            error_count INT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        # 3. live_sessions — session metadata for live listening
        """
        CREATE TABLE IF NOT EXISTS live_sessions (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100),
            status VARCHAR(20) DEFAULT 'running'
                CHECK (status IN ('running', 'completed', 'stopped', 'error')),
            channels_monitored JSONB,
            assets_tracked JSONB,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ended_at TIMESTAMP,
            total_messages_processed INT DEFAULT 0,
            parameters JSONB
        )
        """,
        # 4. author_credibility — whale watcher engine
        """
        CREATE TABLE IF NOT EXISTS author_credibility (
            author_id VARCHAR(255),
            source VARCHAR(20),
            baseline_credibility FLOAT DEFAULT 1.0,
            total_posts INT DEFAULT 0,
            spam_flags INT DEFAULT 0,
            is_bot BOOLEAN DEFAULT FALSE,
            last_evaluated_at TIMESTAMP,
            PRIMARY KEY (author_id, source)
        )
        """,
        # 5. sentiment_logs — raw sentiment data (fact table)
        """
        CREATE TABLE IF NOT EXISTS sentiment_logs (
            id SERIAL PRIMARY KEY,
            asset_symbol VARCHAR(20) NOT NULL,
            source VARCHAR(20) NOT NULL,
            content TEXT,
            sentiment_score FLOAT,
            credibility_score FLOAT,
            raw_metadata JSONB,
            event_timestamp TIMESTAMP NOT NULL,
            backtest_id INT NULL,
            session_id INT NULL,
            author_id VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        # 6. price_history — live price snapshots
        """
        CREATE TABLE IF NOT EXISTS price_history (
            id SERIAL PRIMARY KEY,
            asset_symbol VARCHAR(20) NOT NULL,
            price FLOAT NOT NULL,
            currency VARCHAR(5) DEFAULT 'USD',
            event_timestamp TIMESTAMP NOT NULL,
            backtest_id INT NULL,
            session_id INT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        # 7. historical_prices — bulk OHLCV for backtesting
        """
        CREATE TABLE IF NOT EXISTS historical_prices (
            id SERIAL PRIMARY KEY,
            asset_symbol VARCHAR(20) NOT NULL,
            price_open FLOAT,
            price_close FLOAT,
            price_high FLOAT,
            price_low FLOAT,
            volume FLOAT,
            event_date DATE NOT NULL,
            source VARCHAR(30),
            UNIQUE (asset_symbol, event_date)
        )
        """,
        # 8. sentiment_aggregations — pre-computed time-bucketed averages
        """
        CREATE TABLE IF NOT EXISTS sentiment_aggregations (
            id SERIAL PRIMARY KEY,
            asset_symbol VARCHAR(20) NOT NULL,
            time_bucket TIMESTAMP NOT NULL,
            bucket_interval VARCHAR(10) NOT NULL DEFAULT '1h',
            avg_sentiment_score FLOAT,
            weighted_avg_sentiment FLOAT,
            message_volume INT,
            backtest_id INT NULL,
            session_id INT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        # 9. sentiment_price_correlation — core analysis output
        """
        CREATE TABLE IF NOT EXISTS sentiment_price_correlation (
            id SERIAL PRIMARY KEY,
            asset_symbol VARCHAR(20) NOT NULL,
            time_bucket TIMESTAMP NOT NULL,
            bucket_interval VARCHAR(10) NOT NULL DEFAULT '1h',
            avg_sentiment FLOAT,
            weighted_sentiment FLOAT,
            price_at_bucket FLOAT,
            price_change_pct FLOAT,
            sentiment_price_divergence FLOAT,
            message_volume INT,
            backtest_id INT NULL,
            session_id INT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        # 10. alerts — divergence and anomaly events
        """
        CREATE TABLE IF NOT EXISTS alerts (
            id SERIAL PRIMARY KEY,
            asset_symbol VARCHAR(20) NOT NULL,
            alert_type VARCHAR(30) NOT NULL
                CHECK (alert_type IN ('divergence', 'volume_spike', 'sentiment_reversal', 'spam_surge')),
            severity VARCHAR(10) DEFAULT 'info'
                CHECK (severity IN ('info', 'warning', 'critical')),
            message TEXT,
            details JSONB,
            event_timestamp TIMESTAMP NOT NULL,
            backtest_id INT NULL,
            session_id INT NULL,
            is_acknowledged BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
    ]

    # --- Indexes ---
    indexes = [
        # Existing indexes (upgraded to VARCHAR(20) columns)
        "CREATE INDEX IF NOT EXISTS idx_sentiment_logs_asset_time ON sentiment_logs(asset_symbol, event_timestamp DESC);",
        "CREATE INDEX IF NOT EXISTS idx_price_history_asset_time ON price_history(asset_symbol, event_timestamp DESC);",
        "CREATE INDEX IF NOT EXISTS idx_sentiment_agg_asset_time ON sentiment_aggregations(asset_symbol, time_bucket DESC);",
        "CREATE INDEX IF NOT EXISTS idx_sentiment_logs_backtest ON sentiment_logs(backtest_id);",
        "CREATE INDEX IF NOT EXISTS idx_sentiment_logs_author ON sentiment_logs(author_id);",
        # New: Correlation lookups
        "CREATE INDEX IF NOT EXISTS idx_correlation_asset_time ON sentiment_price_correlation(asset_symbol, time_bucket DESC);",
        "CREATE INDEX IF NOT EXISTS idx_correlation_backtest ON sentiment_price_correlation(backtest_id);",
        "CREATE INDEX IF NOT EXISTS idx_correlation_session ON sentiment_price_correlation(session_id);",
        # New: Alert queries
        "CREATE INDEX IF NOT EXISTS idx_alerts_asset_time ON alerts(asset_symbol, event_timestamp DESC);",
        "CREATE INDEX IF NOT EXISTS idx_alerts_type ON alerts(alert_type, created_at DESC);",
        # New: Historical price lookups
        "CREATE INDEX IF NOT EXISTS idx_hist_price_asset_date ON historical_prices(asset_symbol, event_date DESC);",
        # New: Session-scoped queries
        "CREATE INDEX IF NOT EXISTS idx_sentiment_logs_session ON sentiment_logs(session_id);",
        "CREATE INDEX IF NOT EXISTS idx_price_history_session ON price_history(session_id);",
        # New: Source-based filtering
        "CREATE INDEX IF NOT EXISTS idx_sentiment_logs_source ON sentiment_logs(source);",
        # New: Composite for aggregation computation
        "CREATE INDEX IF NOT EXISTS idx_sentiment_logs_asset_source_time ON sentiment_logs(asset_symbol, source, event_timestamp DESC);",
    ]

    try:
        cur = conn.cursor()
        for command in tables:
            cur.execute(command)
        for command in indexes:
            cur.execute(command)
        conn.commit()
        print("Database initialized successfully (10 tables, 15 indexes).")
    except Exception as e:
        print(f"Error creating tables: {e}")
        conn.rollback()
    finally:
        release_connection(conn)

def seed_assets(assets_config):
    """Seeds the assets table from the JSON config (upsert)."""
    conn = get_db_connection()
    if not conn: return

    try:
        cur = conn.cursor()
        for asset in assets_config:
            cur.execute(
                """
                INSERT INTO assets (symbol, name, type, keywords, subreddits)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (symbol) DO UPDATE SET
                    name = EXCLUDED.name,
                    keywords = EXCLUDED.keywords,
                    subreddits = EXCLUDED.subreddits
                """,
                (
                    asset['symbol'],
                    asset['name'],
                    asset['type'],
                    Json(asset.get('keywords', [])),
                    Json(asset.get('subreddits', []))
                )
            )
        conn.commit()
        print(f"Seeded {len(assets_config)} assets into DB.")
    except Exception as e:
        print(f"Error seeding assets: {e}")
        conn.rollback()
    finally:
        release_connection(conn)

# ---------------------------------------------------------------------------
# Backtest Run Management
# ---------------------------------------------------------------------------
def create_backtest_run(name, dataset_source, parameters, total_rows=None, start_time=None, end_time=None):
    """Creates a backtest run record and returns its ID."""
    conn = get_db_connection()
    if not conn: return None

    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO backtest_runs (name, dataset_source, status, start_time, end_time, parameters, total_rows)
            VALUES (%s, %s, 'running', %s, %s, %s, %s)
            RETURNING id
            """,
            (name, dataset_source, start_time, end_time, Json(parameters), total_rows)
        )
        run_id = cur.fetchone()[0]
        conn.commit()
        return run_id
    except Exception as e:
        print(f"Error creating backtest run: {e}")
        conn.rollback()
        return None
    finally:
        release_connection(conn)

def update_backtest_progress(backtest_id, processed_rows, error_count=0):
    """Updates progress counters for a backtest run."""
    conn = get_db_connection()
    if not conn: return

    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE backtest_runs SET processed_rows = %s, error_count = %s WHERE id = %s",
            (processed_rows, error_count, backtest_id)
        )
        conn.commit()
    except Exception as e:
        print(f"Error updating backtest progress: {e}")
        conn.rollback()
    finally:
        release_connection(conn)

def complete_backtest_run(backtest_id, status='completed'):
    """Marks a backtest run as completed or failed."""
    conn = get_db_connection()
    if not conn: return

    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE backtest_runs SET status = %s, end_time = %s WHERE id = %s",
            (status, datetime.now(timezone.utc), backtest_id)
        )
        conn.commit()
    except Exception as e:
        print(f"Error completing backtest run: {e}")
        conn.rollback()
    finally:
        release_connection(conn)

# ---------------------------------------------------------------------------
# Live Session Management
# ---------------------------------------------------------------------------
def create_live_session(name, channels, assets_tracked, parameters=None):
    """Creates a live session record and returns its ID."""
    conn = get_db_connection()
    if not conn: return None

    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO live_sessions (name, channels_monitored, assets_tracked, parameters)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (name, Json(channels), Json(assets_tracked), Json(parameters or {}))
        )
        session_id = cur.fetchone()[0]
        conn.commit()
        return session_id
    except Exception as e:
        print(f"Error creating live session: {e}")
        conn.rollback()
        return None
    finally:
        release_connection(conn)

def update_live_session_count(session_id, total_messages):
    """Updates the total messages processed for a live session."""
    conn = get_db_connection()
    if not conn: return

    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE live_sessions SET total_messages_processed = %s WHERE id = %s",
            (total_messages, session_id)
        )
        conn.commit()
    except Exception as e:
        print(f"Error updating live session count: {e}")
        conn.rollback()
    finally:
        release_connection(conn)

def complete_live_session(session_id, status='completed'):
    """Marks a live session as completed/stopped/error."""
    conn = get_db_connection()
    if not conn: return

    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE live_sessions SET status = %s, ended_at = %s WHERE id = %s",
            (status, datetime.now(timezone.utc), session_id)
        )
        conn.commit()
    except Exception as e:
        print(f"Error completing live session: {e}")
        conn.rollback()
    finally:
        release_connection(conn)

# ---------------------------------------------------------------------------
# Sentiment Inserts
# ---------------------------------------------------------------------------
def insert_sentiment(symbol, source, content, sentiment, credibility, metadata, event_timestamp, backtest_id=None, session_id=None, author_id=None):
    """Inserts a single sentiment record."""
    conn = get_db_connection()
    if not conn: return

    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO sentiment_logs
            (asset_symbol, source, content, sentiment_score, credibility_score, raw_metadata, event_timestamp, backtest_id, session_id, author_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (symbol, source, content, sentiment, credibility, Json(metadata), event_timestamp, backtest_id, session_id, author_id)
        )
        conn.commit()
    except Exception as e:
        print(f"Error inserting sentiment: {e}")
        conn.rollback()
    finally:
        release_connection(conn)

def insert_sentiment_batch(records):
    """
    Batch-inserts sentiment records using execute_values for high performance.
    records: list of tuples (symbol, source, content, sentiment, credibility, metadata_dict, event_timestamp, backtest_id, session_id, author_id)
    """
    if not records:
        return

    conn = get_db_connection()
    if not conn: return

    try:
        cur = conn.cursor()
        # Convert metadata dicts to Json objects
        values = [
            (r[0], r[1], r[2], r[3], r[4], Json(r[5]), r[6], r[7], r[8], r[9])
            for r in records
        ]
        execute_values(
            cur,
            """
            INSERT INTO sentiment_logs
            (asset_symbol, source, content, sentiment_score, credibility_score, raw_metadata, event_timestamp, backtest_id, session_id, author_id)
            VALUES %s
            """,
            values,
            page_size=500
        )
        conn.commit()
    except Exception as e:
        print(f"Error batch-inserting sentiments: {e}")
        conn.rollback()
    finally:
        release_connection(conn)

# ---------------------------------------------------------------------------
# Price Inserts
# ---------------------------------------------------------------------------
def insert_price(symbol, price, event_timestamp, backtest_id=None, session_id=None):
    """Inserts a price record."""
    conn = get_db_connection()
    if not conn: return

    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO price_history (asset_symbol, price, event_timestamp, backtest_id, session_id)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (symbol, price, event_timestamp, backtest_id, session_id)
        )
        conn.commit()
    except Exception as e:
        print(f"Error inserting price: {e}")
        conn.rollback()
    finally:
        release_connection(conn)

# ---------------------------------------------------------------------------
# Author Credibility
# ---------------------------------------------------------------------------
def upsert_author_credibility(author_id, source, credibility_score, is_spam=False, is_bot=False):
    """Upserts an author's credibility record — tracks reputation over time."""
    conn = get_db_connection()
    if not conn: return

    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO author_credibility (author_id, source, baseline_credibility, total_posts, spam_flags, is_bot, last_evaluated_at)
            VALUES (%s, %s, %s, 1, %s, %s, %s)
            ON CONFLICT (author_id, source) DO UPDATE SET
                baseline_credibility = (author_credibility.baseline_credibility * author_credibility.total_posts + EXCLUDED.baseline_credibility)
                                       / (author_credibility.total_posts + 1),
                total_posts = author_credibility.total_posts + 1,
                spam_flags = author_credibility.spam_flags + EXCLUDED.spam_flags,
                is_bot = EXCLUDED.is_bot OR author_credibility.is_bot,
                last_evaluated_at = EXCLUDED.last_evaluated_at
            """,
            (author_id, source, credibility_score, 1 if is_spam else 0, is_bot, datetime.now(timezone.utc))
        )
        conn.commit()
    except Exception as e:
        print(f"Error upserting author credibility: {e}")
        conn.rollback()
    finally:
        release_connection(conn)

# ---------------------------------------------------------------------------
# Asset Queries
# ---------------------------------------------------------------------------
def fetch_active_assets():
    """Fetches all active assets from the DB. Returns list of dicts."""
    conn = get_db_connection()
    if not conn: return []

    try:
        cur = conn.cursor()
        cur.execute("SELECT symbol, name, type, keywords FROM assets WHERE is_active = TRUE")
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        print(f"Error fetching assets: {e}")
        return []
    finally:
        release_connection(conn)

# ---------------------------------------------------------------------------
# Historical Price Inserts
# ---------------------------------------------------------------------------
def insert_historical_prices_batch(records):
    """
    Batch-inserts historical OHLCV price records.
    records: list of tuples (asset_symbol, price_open, price_close, price_high, price_low, volume, event_date, source)
    Uses ON CONFLICT to safely handle re-runs.
    """
    if not records:
        return 0

    conn = get_db_connection()
    if not conn: return 0

    try:
        cur = conn.cursor()
        execute_values(
            cur,
            """
            INSERT INTO historical_prices
            (asset_symbol, price_open, price_close, price_high, price_low, volume, event_date, source)
            VALUES %s
            ON CONFLICT (asset_symbol, event_date) DO NOTHING
            """,
            records,
            page_size=500
        )
        inserted = cur.rowcount
        conn.commit()
        return inserted
    except Exception as e:
        print(f"Error batch-inserting historical prices: {e}")
        conn.rollback()
        return 0
    finally:
        release_connection(conn)

# ---------------------------------------------------------------------------
# Sentiment Log Queries (for aggregation)
# ---------------------------------------------------------------------------
def fetch_sentiment_logs_for_backtest(backtest_id):
    """
    Fetches sentiment logs for a given backtest run.
    Returns list of dicts with keys: asset_symbol, sentiment_score, credibility_score, event_timestamp.
    """
    conn = get_db_connection()
    if not conn: return []

    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT asset_symbol, sentiment_score, credibility_score, event_timestamp
            FROM sentiment_logs
            WHERE backtest_id = %s
            ORDER BY event_timestamp
            """,
            (backtest_id,)
        )
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        print(f"Error fetching sentiment logs: {e}")
        return []
    finally:
        release_connection(conn)

# ---------------------------------------------------------------------------
# Aggregation Inserts & Queries
# ---------------------------------------------------------------------------
def insert_aggregations_batch(records):
    """
    Batch-inserts sentiment aggregation records.
    records: list of tuples (asset_symbol, time_bucket, bucket_interval, avg_sentiment_score, weighted_avg_sentiment, message_volume, backtest_id, session_id)
    """
    if not records:
        return

    conn = get_db_connection()
    if not conn: return

    try:
        cur = conn.cursor()
        execute_values(
            cur,
            """
            INSERT INTO sentiment_aggregations
            (asset_symbol, time_bucket, bucket_interval, avg_sentiment_score, weighted_avg_sentiment, message_volume, backtest_id, session_id)
            VALUES %s
            """,
            records,
            page_size=500
        )
        conn.commit()
    except Exception as e:
        print(f"Error batch-inserting aggregations: {e}")
        conn.rollback()
    finally:
        release_connection(conn)

def fetch_aggregations_for_backtest(backtest_id, interval='1d'):
    """
    Fetches sentiment aggregations for a given backtest and interval.
    Returns list of dicts.
    """
    conn = get_db_connection()
    if not conn: return []

    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT asset_symbol, time_bucket, avg_sentiment_score, weighted_avg_sentiment, message_volume
            FROM sentiment_aggregations
            WHERE backtest_id = %s AND bucket_interval = %s
            ORDER BY asset_symbol, time_bucket
            """,
            (backtest_id, interval)
        )
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        print(f"Error fetching aggregations: {e}")
        return []
    finally:
        release_connection(conn)

# ---------------------------------------------------------------------------
# Historical Price Queries (for correlation)
# ---------------------------------------------------------------------------
def fetch_historical_prices_for_asset(symbol, start_date, end_date):
    """
    Fetches historical prices for an asset within a date range.
    Returns list of dicts with keys: event_date, price_open, price_close, price_high, price_low, volume.
    """
    conn = get_db_connection()
    if not conn: return []

    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT event_date, price_open, price_close, price_high, price_low, volume
            FROM historical_prices
            WHERE asset_symbol = %s AND event_date BETWEEN %s AND %s
            ORDER BY event_date
            """,
            (symbol, start_date, end_date)
        )
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        print(f"Error fetching historical prices: {e}")
        return []
    finally:
        release_connection(conn)

# ---------------------------------------------------------------------------
# Correlation Inserts
# ---------------------------------------------------------------------------
def insert_correlations_batch(records):
    """
    Batch-inserts correlation records.
    records: list of tuples (asset_symbol, time_bucket, bucket_interval, avg_sentiment, weighted_sentiment,
                             price_at_bucket, price_change_pct, sentiment_price_divergence, message_volume, backtest_id, session_id)
    """
    if not records:
        return

    conn = get_db_connection()
    if not conn: return

    try:
        cur = conn.cursor()
        execute_values(
            cur,
            """
            INSERT INTO sentiment_price_correlation
            (asset_symbol, time_bucket, bucket_interval, avg_sentiment, weighted_sentiment,
             price_at_bucket, price_change_pct, sentiment_price_divergence, message_volume, backtest_id, session_id)
            VALUES %s
            """,
            records,
            page_size=500
        )
        conn.commit()
    except Exception as e:
        print(f"Error batch-inserting correlations: {e}")
        conn.rollback()
    finally:
        release_connection(conn)

# ---------------------------------------------------------------------------
# Alert Inserts
# ---------------------------------------------------------------------------
def insert_alert(asset_symbol, alert_type, severity, message, details, event_timestamp, backtest_id=None, session_id=None):
    """Inserts a single alert record."""
    conn = get_db_connection()
    if not conn: return

    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO alerts
            (asset_symbol, alert_type, severity, message, details, event_timestamp, backtest_id, session_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (asset_symbol, alert_type, severity, message, Json(details), event_timestamp, backtest_id, session_id)
        )
        conn.commit()
    except Exception as e:
        print(f"Error inserting alert: {e}")
        conn.rollback()
    finally:
        release_connection(conn)

# ---------------------------------------------------------------------------
# Clear Data
# ---------------------------------------------------------------------------
def clear_all_data():
    """Truncates all data tables (preserves schema)."""
    conn = get_db_connection()
    if not conn: return

    try:
        cur = conn.cursor()
        # Order matters — truncate child tables before parents
        cur.execute("TRUNCATE TABLE alerts RESTART IDENTITY CASCADE;")
        cur.execute("TRUNCATE TABLE sentiment_price_correlation RESTART IDENTITY CASCADE;")
        cur.execute("TRUNCATE TABLE sentiment_aggregations RESTART IDENTITY CASCADE;")
        cur.execute("TRUNCATE TABLE sentiment_logs RESTART IDENTITY CASCADE;")
        cur.execute("TRUNCATE TABLE price_history RESTART IDENTITY CASCADE;")
        cur.execute("TRUNCATE TABLE historical_prices RESTART IDENTITY CASCADE;")
        cur.execute("TRUNCATE TABLE backtest_runs RESTART IDENTITY CASCADE;")
        cur.execute("TRUNCATE TABLE live_sessions RESTART IDENTITY CASCADE;")
        cur.execute("TRUNCATE TABLE author_credibility;")
        # Note: assets table is NOT truncated (reference data)
        conn.commit()
        print("Database cleared successfully.")
    except Exception as e:
        print(f"Error clearing database: {e}")
        conn.rollback()
    finally:
        release_connection(conn)

def close_pool():
    """Closes all connections in the pool. Call on shutdown."""
    global _pool
    if _pool and not _pool.closed:
        _pool.closeall()
        print("Connection pool closed.")
