"""
Correlation & Divergence Engine

Joins sentiment_aggregations with historical_prices to compute the
sentiment-price divergence. Generates alerts when divergence exceeds
configurable thresholds.
"""

import pandas as pd
from datetime import datetime
from db import (
    fetch_aggregations_for_backtest,
    fetch_historical_prices_for_asset,
    insert_correlations_batch,
    insert_alert
)


# Configurable thresholds
DIVERGENCE_THRESHOLD = 0.5       # abs(divergence) > this triggers an alert
VOLUME_SPIKE_THRESHOLD = 3.0     # message_volume > (mean * this) triggers a volume spike alert


class CorrelationEngine:
    def __init__(self, divergence_threshold=DIVERGENCE_THRESHOLD,
                 volume_spike_threshold=VOLUME_SPIKE_THRESHOLD):
        self.divergence_threshold = divergence_threshold
        self.volume_spike_threshold = volume_spike_threshold

    def run(self, backtest_id, interval='1d'):
        """
        Computes correlation between sentiment and price for a backtest run.
        
        Args:
            backtest_id: ID of the backtest run.
            interval: Time bucket interval to use (default '1d').
        """
        print(f"\n{'='*60}")
        print(f"Correlation & Divergence Engine")
        print(f"Backtest ID: {backtest_id} | Interval: {interval}")
        print(f"{'='*60}")

        # Fetch aggregated sentiment data
        agg_data = fetch_aggregations_for_backtest(backtest_id, interval)
        if not agg_data:
            print("No aggregation data found. Run the aggregation engine first.")
            return

        agg_df = pd.DataFrame(agg_data)
        agg_df['time_bucket'] = pd.to_datetime(agg_df['time_bucket'])
        # Extract date for joining with historical_prices
        agg_df['join_date'] = agg_df['time_bucket'].dt.date

        assets = agg_df['asset_symbol'].unique()
        print(f"Assets to correlate: {list(assets)}")

        # Determine date range from aggregation data
        min_date = agg_df['join_date'].min()
        max_date = agg_df['join_date'].max()
        print(f"Date range: {min_date} → {max_date}")

        total_correlations = 0
        total_alerts = 0

        for symbol in assets:
            print(f"\n--- Processing {symbol} ---")

            # Get sentiment data for this asset
            asset_agg = agg_df[agg_df['asset_symbol'] == symbol].copy()
            asset_agg = asset_agg.sort_values('time_bucket')

            # Fetch historical prices from DB
            price_data = fetch_historical_prices_for_asset(symbol, min_date, max_date)
            if not price_data:
                print(f"  No historical prices found for {symbol}. Skipping.")
                continue

            price_df = pd.DataFrame(price_data)
            price_df['join_date'] = pd.to_datetime(price_df['event_date']).dt.date

            # Compute price_change_pct (day-over-day)
            price_df = price_df.sort_values('join_date')
            price_df['price_change_pct'] = price_df['price_close'].pct_change() * 100
            price_df['price_change_pct'] = price_df['price_change_pct'].fillna(0)

            # Join sentiment with price on date
            merged = pd.merge(
                asset_agg,
                price_df[['join_date', 'price_close', 'price_change_pct']],
                on='join_date',
                how='inner'
            )

            if merged.empty:
                print(f"  No matching dates between sentiment and prices for {symbol}.")
                continue

            print(f"  Matched {len(merged)} date buckets.")

            # Compute divergence
            # Normalize price_change_pct to [-1, 1] range for comparison with sentiment
            max_abs_pct = merged['price_change_pct'].abs().max()
            if max_abs_pct > 0:
                merged['norm_price_change'] = merged['price_change_pct'] / max_abs_pct
            else:
                merged['norm_price_change'] = 0

            # Divergence = weighted_sentiment - normalized_price_change
            # Positive divergence = sentiment is bullish but price is dropping
            # Negative divergence = sentiment is bearish but price is rising
            merged['divergence'] = merged['weighted_avg_sentiment'] - merged['norm_price_change']

            # Build correlation records for batch insert
            corr_records = []
            for _, row in merged.iterrows():
                corr_records.append((
                    symbol,
                    row['time_bucket'],
                    interval,
                    round(row['avg_sentiment_score'], 6) if pd.notna(row['avg_sentiment_score']) else 0,
                    round(row['weighted_avg_sentiment'], 6) if pd.notna(row['weighted_avg_sentiment']) else 0,
                    round(row['price_close'], 2) if pd.notna(row['price_close']) else 0,
                    round(row['price_change_pct'], 4) if pd.notna(row['price_change_pct']) else 0,
                    round(row['divergence'], 6) if pd.notna(row['divergence']) else 0,
                    int(row['message_volume']) if pd.notna(row['message_volume']) else 0,
                    backtest_id,
                    None  # session_id
                ))

            insert_correlations_batch(corr_records)
            total_correlations += len(corr_records)
            print(f"  Inserted {len(corr_records)} correlation records.")

            # --- Alert Generation ---
            alerts_generated = self._generate_alerts(merged, symbol, backtest_id)
            total_alerts += alerts_generated

        print(f"\n{'='*60}")
        print(f"Correlation Complete!")
        print(f"Total correlation records: {total_correlations}")
        print(f"Total alerts generated: {total_alerts}")
        print(f"{'='*60}\n")

    def _generate_alerts(self, merged_df, symbol, backtest_id):
        """Checks for divergence and volume spike anomalies and inserts alerts."""
        alert_count = 0

        # 1. Divergence alerts
        divergence_rows = merged_df[merged_df['divergence'].abs() > self.divergence_threshold]
        for _, row in divergence_rows.iterrows():
            div_val = row['divergence']
            direction = "bullish sentiment / bearish price" if div_val > 0 else "bearish sentiment / bullish price"
            severity = 'critical' if abs(div_val) > (self.divergence_threshold * 2) else 'warning'

            insert_alert(
                asset_symbol=symbol,
                alert_type='divergence',
                severity=severity,
                message=f"Sentiment-price divergence detected for {symbol}: {direction} (divergence={div_val:.3f})",
                details={
                    'divergence': round(div_val, 4),
                    'weighted_sentiment': round(row['weighted_avg_sentiment'], 4),
                    'price_change_pct': round(row['price_change_pct'], 4),
                    'price_close': round(row['price_close'], 2),
                    'message_volume': int(row['message_volume'])
                },
                event_timestamp=row['time_bucket'],
                backtest_id=backtest_id
            )
            alert_count += 1

        # 2. Volume spike alerts
        mean_volume = merged_df['message_volume'].mean()
        if mean_volume > 0:
            spike_threshold = mean_volume * self.volume_spike_threshold
            spike_rows = merged_df[merged_df['message_volume'] > spike_threshold]
            for _, row in spike_rows.iterrows():
                insert_alert(
                    asset_symbol=symbol,
                    alert_type='volume_spike',
                    severity='info',
                    message=f"Message volume spike for {symbol}: {int(row['message_volume'])} messages (avg: {int(mean_volume)})",
                    details={
                        'message_volume': int(row['message_volume']),
                        'mean_volume': round(mean_volume, 1),
                        'spike_ratio': round(row['message_volume'] / mean_volume, 2)
                    },
                    event_timestamp=row['time_bucket'],
                    backtest_id=backtest_id
                )
                alert_count += 1

        if alert_count > 0:
            print(f"  Generated {alert_count} alerts for {symbol}.")

        return alert_count


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python correlation_engine.py <backtest_id>")
        sys.exit(1)
    
    backtest_id = int(sys.argv[1])
    engine = CorrelationEngine()
    engine.run(backtest_id)
