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
    """Loads assets from the JSON config."""
    config_path = os.path.join(os.path.dirname(__file__), 'config', 'assets.json')
    with open(config_path, 'r') as f:
        return json.load(f)

class BacktestRunner:
    def __init__(self):
        self.analyzer = SentimentIntensityAnalyzer()
        self.config = load_config()
        self.assets = self.config['assets']

    def identify_asset(self, text):
        """
        Returns the asset symbol if found in text, else None.
        Priority: Exact Symbol Match > Keyword Match.
        """
        text_lower = text.lower()
        
        for asset in self.assets:
            # Check symbol (case sensitive-ish, often tickers are UPPER)
            if f" {asset['symbol']} " in f" {text} ": # simplistic tokenization
                return asset['symbol']
                
            # Check keywords
            for kw in asset['keywords']:
                if kw in text_lower:
                    return asset['symbol']
        return None

    def run(self):
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
        
        for index, row in df.iterrows():
            try:
                # Combine title and body
                body = str(row['body']) if pd.notna(row['body']) else ""
                title = str(row['title']) if pd.notna(row['title']) else ""
                content = f"{title} \n {body}"
                
                # Identify Asset
                symbol = self.identify_asset(content)
                if not symbol:
                    continue # Skip unrelated posts
                
                # Timestamp parsing (Format: 2022-04-06 09:14:16)
                timestamp_str = str(row['timestamp'])
                try:
                    timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    continue
                
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
        complete_backtest_run(backtest_id, status='completed')
        
        print(f"Backtest Complete! Processed {processed_count} relevant posts ({error_count} errors).")

if __name__ == "__main__":
    runner = BacktestRunner()
    runner.run()
