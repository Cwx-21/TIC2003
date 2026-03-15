"""
Sentiment Aggregation Engine

Takes raw sentiment_logs for a backtest run and computes
time-bucketed averages (1h, 4h, 1d) with credibility weighting.
Results are written to the sentiment_aggregations table.
"""

import pandas as pd
from db import fetch_sentiment_logs_for_backtest, insert_aggregations_batch


# Mapping of interval labels to Pandas offset aliases
INTERVAL_MAP = {
    '1h': '1h',
    '4h': '4h',
    '1d': '1D',
}


class SentimentAggregator:
    def __init__(self):
        pass

    def run(self, backtest_id, intervals=None):
        """
        Aggregates sentiment data for a backtest run across given time intervals.
        
        Args:
            backtest_id: ID of the backtest run to aggregate.
            intervals: list of interval strings, e.g. ['1h', '4h', '1d'].
                       Defaults to all three.
        """
        if intervals is None:
            intervals = ['1h', '4h', '1d']

        print(f"\n{'='*60}")
        print(f"Sentiment Aggregation Engine")
        print(f"Backtest ID: {backtest_id} | Intervals: {intervals}")
        print(f"{'='*60}")

        # Fetch raw sentiment logs from DB
        print("Fetching sentiment logs from DB...")
        raw_data = fetch_sentiment_logs_for_backtest(backtest_id)

        if not raw_data:
            print("No sentiment logs found for this backtest. Skipping aggregation.")
            return

        print(f"Loaded {len(raw_data)} sentiment records.")

        # Convert to DataFrame
        df = pd.DataFrame(raw_data)
        df['event_timestamp'] = pd.to_datetime(df['event_timestamp'])
        df = df.set_index('event_timestamp')

        # Process each asset separately
        assets = df['asset_symbol'].unique()
        print(f"Assets to aggregate: {list(assets)}")

        total_buckets = 0

        for interval_label in intervals:
            pandas_freq = INTERVAL_MAP.get(interval_label)
            if not pandas_freq:
                print(f"Unknown interval: {interval_label}, skipping.")
                continue

            print(f"\n--- Computing {interval_label} buckets ---")
            batch_records = []

            for symbol in assets:
                asset_df = df[df['asset_symbol'] == symbol].copy()

                if asset_df.empty:
                    continue

                # Resample into time buckets
                resampled = asset_df.resample(pandas_freq)

                for bucket_time, group in resampled:
                    if group.empty:
                        continue

                    msg_count = len(group)
                    avg_sentiment = group['sentiment_score'].mean()

                    # Credibility-weighted average
                    cred_sum = group['credibility_score'].sum()
                    if cred_sum > 0:
                        weighted_avg = (group['sentiment_score'] * group['credibility_score']).sum() / cred_sum
                    else:
                        weighted_avg = avg_sentiment

                    # Tuple: (asset_symbol, time_bucket, bucket_interval, avg_sentiment_score,
                    #          weighted_avg_sentiment, message_volume, backtest_id, session_id)
                    batch_records.append((
                        symbol,
                        bucket_time.to_pydatetime(),
                        interval_label,
                        float(round(avg_sentiment, 6)),
                        float(round(weighted_avg, 6)),
                        int(msg_count),
                        backtest_id,
                        None  # session_id (backtest mode)
                    ))

            if batch_records:
                insert_aggregations_batch(batch_records)
                total_buckets += len(batch_records)
                print(f"  Inserted {len(batch_records)} buckets for interval {interval_label}.")

        print(f"\n{'='*60}")
        print(f"Aggregation Complete! Total buckets inserted: {total_buckets}")
        print(f"{'='*60}\n")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python aggregation_engine.py <backtest_id>")
        sys.exit(1)
    
    backtest_id = int(sys.argv[1])
    aggregator = SentimentAggregator()
    aggregator.run(backtest_id)
