import asyncio
import pandas as pd
from datetime import datetime, timezone, timedelta
from db import (
    fetch_sentiment_logs_for_window, 
    fetch_latest_price, 
    fetch_previous_correlation,
    insert_aggregations_batch,
    insert_correlations_batch,
    insert_alert,
    fetch_active_assets
)

# Configurable thresholds matching Backtest Engine
DIVERGENCE_THRESHOLD = 0.5
VOLUME_SPIKE_THRESHOLD = 3.0

class LiveProcessor:
    def __init__(self, session_id):
        self.session_id = session_id
        
        # In live mode, we only use the 1m interval
        self.interval = '1m'
        
        # Get active assets from DB
        assets_data = fetch_active_assets()
        self.assets = [asset['symbol'] for asset in assets_data]

    async def process_window(self, start_time, end_time):
        """
        Calculates sentiment aggregations and divergence for a specific time window.
        Intended to be called every 60 seconds by the main loop.
        """
        print(f"\n[{end_time.strftime('%H:%M:%S')}] Running Live Processor for window: {start_time.strftime('%H:%M:%S')} -> {end_time.strftime('%H:%M:%S')}")
        
        # 1. Fetch data for this window
        logs = fetch_sentiment_logs_for_window(self.session_id, start_time, end_time)
        
        if not logs:
            print("  No messages in this window. Skipping.")
            return

        df = pd.DataFrame(logs)
        
        agg_records = []
        corr_records = []
        alert_count = 0
        
        # 2. Process each asset
        for symbol in self.assets:
            asset_df = df[df['asset_symbol'] == symbol]
            
            if asset_df.empty:
                continue
                
            msg_count = len(asset_df)
            avg_sentiment = asset_df['sentiment_score'].mean()
            
            cred_sum = asset_df['credibility_score'].sum()
            if cred_sum > 0:
                weighted_avg = (asset_df['sentiment_score'] * asset_df['credibility_score']).sum() / cred_sum
            else:
                weighted_avg = avg_sentiment
                
            # Tuple: (asset_symbol, time_bucket, bucket_interval, avg_sentiment_score,
            #          weighted_avg_sentiment, message_volume, backtest_id, session_id)
            agg_records.append((
                symbol,
                start_time,
                self.interval,
                float(round(avg_sentiment, 6)),
                float(round(weighted_avg, 6)),
                msg_count,
                None,             # backtest_id
                self.session_id   # session_id
            ))
            
            # --- 3. Determine Price Divergence ---
            latest_price_doc = fetch_latest_price(symbol, self.session_id)
            current_price = latest_price_doc['price'] if latest_price_doc else 0.0
            
            previous_corr = fetch_previous_correlation(symbol, self.session_id, self.interval)
            
            price_change_pct = 0.0
            if previous_corr and previous_corr['price_at_bucket'] > 0 and current_price > 0:
                price_change_pct = ((current_price - previous_corr['price_at_bucket']) / previous_corr['price_at_bucket']) * 100
            
            # For live mode, we don't naturally normalize against an entire historical day batch.
            # We treat the raw price_change_pct directly against sentiment or apply a fixed scalar if volatility is low.
            # As a basic measure: divergence = sentiment - (price_change_pct / 2.0)
            norm_price_change = price_change_pct / 2.0 if price_change_pct != 0 else 0
            divergence = weighted_avg - norm_price_change
            
            corr_records.append((
                symbol,
                start_time,
                self.interval,
                float(round(avg_sentiment, 6)),
                float(round(weighted_avg, 6)),
                float(round(current_price, 2)),
                float(round(price_change_pct, 4)),
                float(round(divergence, 6)),
                msg_count,
                None,           # backtest_id
                self.session_id # session_id
            ))
            
            # --- 4. Alert Generation ---
            
            # Divergence Alert
            if abs(divergence) > DIVERGENCE_THRESHOLD:
                direction = "bullish sentiment / bearish price" if divergence > 0 else "bearish sentiment / bullish price"
                severity = 'critical' if abs(divergence) > (DIVERGENCE_THRESHOLD * 2) else 'warning'
                insert_alert(
                    asset_symbol=symbol,
                    alert_type='divergence',
                    severity=severity,
                    message=f"Sentiment-price divergence detected for {symbol}: {direction} (divergence={divergence:.3f})",
                    details={
                        'divergence': float(round(divergence, 4)),
                        'weighted_sentiment': float(round(weighted_avg, 4)),
                        'price_change_pct': float(round(price_change_pct, 4)),
                        'price_close': float(round(current_price, 2)),
                        'message_volume': msg_count
                    },
                    event_timestamp=start_time,
                    backtest_id=None,
                    session_id=self.session_id
                )
                alert_count += 1
                
            # Volume Spike Alert
            if previous_corr and previous_corr['message_volume'] > 0:
                # We use the previous bucket as our "mean" baseline for simplicity in real-time
                baseline = previous_corr['message_volume']
                if msg_count > (baseline * VOLUME_SPIKE_THRESHOLD) and msg_count >= 5: # min 5 msgs to kill low-volume noise
                    insert_alert(
                        asset_symbol=symbol,
                        alert_type='volume_spike',
                        severity='info',
                        message=f"Message volume spike for {symbol}: {msg_count} messages (prev: {baseline})",
                        details={
                            'message_volume': msg_count,
                            'mean_volume': baseline,
                            'spike_ratio': float(round(msg_count / baseline, 2))
                        },
                        event_timestamp=start_time,
                        backtest_id=None,
                        session_id=self.session_id
                    )
                    alert_count += 1
                    
        # 5. Insert Batch Records
        if agg_records:
            insert_aggregations_batch(agg_records)
        if corr_records:
            insert_correlations_batch(corr_records)
            
        print(f"  Processed {len(self.assets)} assets.")
        print(f"  Inserted {len(agg_records)} aggregations & {len(corr_records)} correlations.")
        if alert_count > 0:
            print(f"  Generated {alert_count} live alerts.")
