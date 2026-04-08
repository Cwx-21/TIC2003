import pandas as pd
import os
from datetime import datetime
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from db import (
    insert_sentiment_batch, create_backtest_run,
    update_backtest_progress, complete_backtest_run,
    upsert_author_credibility, seed_assets
)
from credibility_engine import calculate_credibility
from config_loader import load_config
from asset_matcher import identify_asset
from pipeline import run_pipeline, DEFAULT_PIPELINE

# Config
CSV_PATH = os.path.join(os.path.dirname(__file__), 'data', 'wallstreetbets_2022.csv')
BATCH_SIZE = 500  # Rows per batch insert


class BacktestRunner:
    def __init__(self):
        self.analyzer = SentimentIntensityAnalyzer()
        self.config = load_config()
        self.assets = self.config['assets']

    def run(self):
        """Orchestrates the full backtest pipeline."""
        df = self._load_csv()
        if df is None:
            return

        backtest_id = self._init_backtest(df)
        if not backtest_id:
            return

        date_range = self._process_rows(df, backtest_id)
        self._run_post_processing(backtest_id, date_range)

    def _load_csv(self):
        """Loads and validates the backtest CSV file."""
        if not os.path.exists(CSV_PATH):
            print(f"Error: Backtest data file not found at {CSV_PATH}")
            return None

        print(f"Loading backtest data from {CSV_PATH}...")
        try:
            df = pd.read_csv(CSV_PATH, usecols=['title', 'body', 'timestamp', 'score', 'id', 'url'])
        except Exception as e:
            print(f"Error reading CSV: {e}")
            return None

        print(f"Starting Backtest on {len(df)} rows...")
        return df

    def _init_backtest(self, df):
        """Creates a new backtest run record in the database."""
        seed_assets(self.assets)
        total_rows = len(df)
        backtest_name = f"Reddit Backtest {datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backtest_id = create_backtest_run(
            name=backtest_name,
            dataset_source=os.path.basename(CSV_PATH),
            parameters={'file': CSV_PATH, 'rows': total_rows},
            total_rows=total_rows
        )
        if not backtest_id:
            print("Failed to initialize backtest run in DB.")
            return None

        print(f"Initialized Backtest Run ID: {backtest_id}")
        return backtest_id

    def _process_rows(self, df, backtest_id):
        """Processes CSV rows: sentiment analysis, credibility scoring, batch insertion."""
        processed_count = 0
        error_count = 0
        batch_buffer = []
        min_date = None
        max_date = None

        for index, row in df.iterrows():
            try:
                body = str(row['body']) if pd.notna(row['body']) else ""
                title = str(row['title']) if pd.notna(row['title']) else ""
                content = f"{title} \n {body}"

                symbol = identify_asset(content, self.assets)
                if not symbol:
                    continue

                timestamp_str = str(row['timestamp'])
                try:
                    timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    continue

                ts_date = timestamp.date()
                if min_date is None or ts_date < min_date:
                    min_date = ts_date
                if max_date is None or ts_date > max_date:
                    max_date = ts_date

                score = self.analyzer.polarity_scores(content)['compound']

                metadata = {
                    'score': int(row['score']) if pd.notna(row['score']) else 0,
                    'id': str(row['id']) if pd.notna(row['id']) else "",
                    'url': str(row['url']) if pd.notna(row['url']) else ""
                }
                credibility = calculate_credibility('reddit', metadata, content)

                author_id = str(row['author']) if 'author' in df.columns and pd.notna(row.get('author')) else f"reddit_user_{str(row['id']) if pd.notna(row['id']) else index}"
                
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

        date_range = (str(min_date), str(max_date)) if min_date and max_date else None
        return date_range

    def _run_post_processing(self, backtest_id, date_range):
        """Runs the post-processing pipeline (price ingestion, aggregation, correlation)."""
        run_pipeline(DEFAULT_PIPELINE, backtest_id, date_range=date_range)

        complete_backtest_run(backtest_id, status='completed')
        print(f"\n{'='*60}")
        print(f"Backtest Pipeline Complete! (Run ID: {backtest_id})")
        print(f"{'='*60}")


if __name__ == "__main__":
    runner = BacktestRunner()
    runner.run()
