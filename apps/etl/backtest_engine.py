"""
Backtest Engine

Replays a historical Reddit CSV dataset (WallStreetBets 2022) through the full
HypeCheck sentiment analysis pipeline. Implements a three-phase pipeline pattern:

  Phase 0 — CSV Ingestion:
    Reads the dataset row by row, identifies the relevant asset, scores sentiment
    via VADER, computes author credibility, and batch-inserts into sentiment_logs.

  Phase 1 — Post-Processing Pipeline (three sequential steps):
    Step 1: Ingest historical OHLCV prices via yfinance for the detected date range.
    Step 2: Aggregate raw sentiment into time-bucketed averages (SentimentAggregator).
    Step 3: Join sentiment with price data and compute divergence (CorrelationEngine).

Each backtest run is tracked in backtest_runs with progress counters, enabling
the API to report status while the pipeline is executing.
"""

import pandas as pd
import time
import os
import json
from datetime import datetime
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from db import (
    insert_sentiment_batch, create_backtest_run,
    update_backtest_progress, complete_backtest_run,
    upsert_author_credibility, seed_assets
)
from credibility_engine import calculate_credibility

# Config
CSV_PATH = os.path.join(os.path.dirname(__file__), 'data', 'wallstreetbets_2022.csv')
BATCH_SIZE = 500  # Rows per batch insert


def load_config():
    """
    Loads the asset registry from config/assets.json.

    Returns:
        dict: Parsed JSON config with 'assets' and 'telegram_channels' keys.
    """
    config_path = os.path.join(os.path.dirname(__file__), 'config', 'assets.json')
    with open(config_path, 'r') as f:
        return json.load(f)


class BacktestRunner:
    """
    Orchestrates the full backtest pipeline from CSV ingestion to correlation analysis.

    Loads the WallStreetBets 2022 dataset, processes each row through asset
    identification, VADER sentiment analysis, and credibility scoring, then
    flushes records to the database in batches. After CSV processing, delegates
    to SentimentAggregator and CorrelationEngine to complete the pipeline.

    Attributes:
        analyzer (SentimentIntensityAnalyzer): VADER compound sentiment scorer.
        config (dict): Parsed asset config from config/assets.json.
        assets (list[dict]): Active asset definitions used for keyword matching.
    """

    def __init__(self):
        self.analyzer = SentimentIntensityAnalyzer()
        self.config = load_config()
        self.assets = self.config['assets']

    def identify_asset(self, text):
        """
        Identifies the tracked asset mentioned in a Reddit post.

        Checks for an exact symbol token match first (higher precision), then
        falls back to keyword matching. Returns the first asset that matches.

        Args:
            text (str): Combined title + body text of the Reddit post.

        Returns:
            str | None: Matched asset symbol (e.g., 'GME'), or None if no match.
        """
        text_lower = text.lower()

        for asset in self.assets:
            # Check symbol (case sensitive-ish, often tickers are UPPER)
            if f" {asset['symbol']} " in f" {text} ":  # simplistic tokenization
                return asset['symbol']

            # Check keywords
            for kw in asset['keywords']:
                if kw in text_lower:
                    return asset['symbol']
        return None

    def run(self):
        """
        Executes the full backtest pipeline.

        Phase 0: Reads the CSV row-by-row, identifies assets, scores sentiment,
        and batch-inserts into sentiment_logs in chunks of BATCH_SIZE rows.

        Phase 1 (post-processing pipeline):
          Step 1 — ingest_historical_prices(): fetches OHLCV from yfinance.
          Step 2 — SentimentAggregator.run(): aggregates sentiment into buckets.
          Step 3 — CorrelationEngine.run(): joins sentiment with price and generates alerts.
        """
        if not os.path.exists(CSV_PATH):
            print(f"Error: Backtest data file not found at {CSV_PATH}")
            return

        # Seed assets table from config
        seed_assets(self.assets)

        print(f"Loading backtest data from {CSV_PATH}...")
        try:
            # Read only necessary columns to save memory
            df = pd.read_csv(CSV_PATH, usecols=['title', 'body', 'timestamp', 'score', 'id', 'url'])
        except Exception as e:
            print(f"Error reading CSV: {e}")
            return

        total_rows = len(df)
        print(f"Starting Backtest on {total_rows} rows...")

        # Create a new backtest run with total_rows & status tracking
        backtest_name = f"Reddit Backtest {datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backtest_id = create_backtest_run(
            name=backtest_name,
            dataset_source=os.path.basename(CSV_PATH),
            parameters={'file': CSV_PATH, 'rows': total_rows},
            total_rows=total_rows
        )
        if not backtest_id:
            print("Failed to initialize backtest run in DB.")
            return

        print(f"Initialized Backtest Run ID: {backtest_id}")

        processed_count = 0
        error_count = 0
        batch_buffer = []
        min_date = None
        max_date = None

        # --- Phase 0: CSV Ingestion ---
        for index, row in df.iterrows():
            try:
                # Combine title and body
                body = str(row['body']) if pd.notna(row['body']) else ""
                title = str(row['title']) if pd.notna(row['title']) else ""
                content = f"{title} \n {body}"

                # Identify Asset
                symbol = self.identify_asset(content)
                if not symbol:
                    continue  # Skip unrelated posts

                # Timestamp parsing (Format: 2022-04-06 09:14:16)
                timestamp_str = str(row['timestamp'])
                try:
                    timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    continue

                # Track date range for historical price ingestion
                ts_date = timestamp.date()
                if min_date is None or ts_date < min_date:
                    min_date = ts_date
                if max_date is None or ts_date > max_date:
                    max_date = ts_date

                # VADER Analysis
                score = self.analyzer.polarity_scores(content)['compound']

                # Credibility
                metadata = {
                    'score': int(row['score']) if pd.notna(row['score']) else 0,
                    'id': str(row['id']) if pd.notna(row['id']) else "",
                    'url': str(row['url']) if pd.notna(row['url']) else ""
                }
                credibility = calculate_credibility('reddit', metadata, content)

                # Author ID
                author_col = df.columns
                if 'author' in author_col and pd.notna(row.get('author')):
                    author_id = str(row['author'])
                else:
                    post_id = str(row['id']) if pd.notna(row['id']) else str(index)
                    author_id = f"reddit_user_{post_id}"

                # Determine if content looks spammy (for credibility tracking)
                is_spam = credibility < 0.3

                # Add to batch buffer
                # Tuple: (symbol, source, content, sentiment, credibility, metadata, timestamp, backtest_id, session_id, author_id)
                batch_buffer.append((
                    symbol, 'reddit_backtest', title, score, credibility,
                    metadata, timestamp, backtest_id, None, author_id
                ))

                # Update author credibility in DB (persists reputation over time)
                upsert_author_credibility(
                    author_id=author_id,
                    source='reddit',
                    credibility_score=credibility,
                    is_spam=is_spam
                )

                processed_count += 1

                # Flush batch when buffer is full
                if len(batch_buffer) >= BATCH_SIZE:
                    insert_sentiment_batch(batch_buffer)
                    batch_buffer = []
                    # Update progress every batch
                    update_backtest_progress(backtest_id, processed_count, error_count)
                    print(f"[Backtest] Processed {processed_count} rows... (Batch flushed)")

                if processed_count % 100 == 0 and len(batch_buffer) > 0:
                    print(f"[Backtest] {timestamp} | {symbol} | Sentiment: {score:.2f} | Cred: {credibility:.2f}")

            except Exception as e:
                error_count += 1
                print(f"Error processing row {index}: {e}")
                continue

        # Flush remaining records in buffer
        if batch_buffer:
            insert_sentiment_batch(batch_buffer)
            print(f"[Backtest] Final batch flushed ({len(batch_buffer)} records)")

        # Mark backtest as completed
        update_backtest_progress(backtest_id, processed_count, error_count)

        print(f"\nCSV Processing Complete! {processed_count} relevant posts ({error_count} errors).")
        print(f"Date range detected: {min_date} → {max_date}")

        # =====================================================================
        # Phase 1 Post-Processing Pipeline
        # =====================================================================

        # Step 1: Ingest historical prices for the backtest date range
        print("\n[Phase 1 - Step 1/3] Historical Price Ingestion...")
        from historical_price_ingest import ingest_historical_prices
        date_range = (str(min_date), str(max_date)) if min_date and max_date else None
        ingest_historical_prices(date_range=date_range)

        # Step 2: Aggregate sentiment into time buckets
        print("\n[Phase 1 - Step 2/3] Sentiment Aggregation...")
        from aggregation_engine import SentimentAggregator
        SentimentAggregator().run(backtest_id)

        # Step 3: Compute correlation & generate alerts
        print("\n[Phase 1 - Step 3/3] Correlation & Divergence Analysis...")
        from correlation_engine import CorrelationEngine
        CorrelationEngine().run(backtest_id)

        # Mark as fully completed
        complete_backtest_run(backtest_id, status='completed')
        print("\n" + "=" * 60)
        print(f"Backtest Pipeline Complete! (Run ID: {backtest_id})")
        print("=" * 60)


if __name__ == "__main__":
    runner = BacktestRunner()
    runner.run()
