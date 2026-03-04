"""
Tests for the Sentiment Aggregation Engine.

Tests the aggregation logic in isolation using mocked data
(no database required).
"""

import pytest
import pandas as pd
from datetime import datetime


def compute_aggregation(records, interval='1h'):
    """
    Pure-function version of the aggregation logic for testing.
    Takes a list of sentiment record dicts, returns aggregated results.
    """
    INTERVAL_MAP = {'1h': '1h', '4h': '4h', '1d': '1D'}
    pandas_freq = INTERVAL_MAP.get(interval)

    if not records:
        return []

    df = pd.DataFrame(records)
    df['event_timestamp'] = pd.to_datetime(df['event_timestamp'])
    df = df.set_index('event_timestamp')

    results = []
    for symbol in df['asset_symbol'].unique():
        asset_df = df[df['asset_symbol'] == symbol]
        resampled = asset_df.resample(pandas_freq)

        for bucket_time, group in resampled:
            if group.empty:
                continue

            msg_count = len(group)
            avg_sentiment = group['sentiment_score'].mean()
            cred_sum = group['credibility_score'].sum()

            if cred_sum > 0:
                weighted_avg = (group['sentiment_score'] * group['credibility_score']).sum() / cred_sum
            else:
                weighted_avg = avg_sentiment

            results.append({
                'asset_symbol': symbol,
                'time_bucket': bucket_time,
                'interval': interval,
                'avg_sentiment': round(avg_sentiment, 6),
                'weighted_avg_sentiment': round(weighted_avg, 6),
                'message_volume': msg_count
            })

    return results


class TestSentimentAggregation:
    """Tests for the sentiment aggregation logic."""

    @pytest.fixture
    def sample_data(self):
        """Creates a small dataset with known values for verification."""
        return [
            {'asset_symbol': 'BTC', 'sentiment_score': 0.8, 'credibility_score': 0.9, 'event_timestamp': '2022-01-01 10:00:00'},
            {'asset_symbol': 'BTC', 'sentiment_score': 0.6, 'credibility_score': 0.5, 'event_timestamp': '2022-01-01 10:30:00'},
            {'asset_symbol': 'BTC', 'sentiment_score': -0.3, 'credibility_score': 0.8, 'event_timestamp': '2022-01-01 11:15:00'},
            {'asset_symbol': 'BTC', 'sentiment_score': 0.1, 'credibility_score': 0.2, 'event_timestamp': '2022-01-01 11:45:00'},
            {'asset_symbol': 'ETH', 'sentiment_score': 0.5, 'credibility_score': 0.7, 'event_timestamp': '2022-01-01 10:00:00'},
            {'asset_symbol': 'ETH', 'sentiment_score': -0.2, 'credibility_score': 0.6, 'event_timestamp': '2022-01-01 10:20:00'},
        ]

    def test_hourly_bucket_count(self, sample_data):
        """Test that hourly bucketing produces the correct number of buckets."""
        results = compute_aggregation(sample_data, '1h')
        btc_buckets = [r for r in results if r['asset_symbol'] == 'BTC']
        eth_buckets = [r for r in results if r['asset_symbol'] == 'ETH']
        # BTC has data in hours 10 and 11 → 2 buckets
        assert len(btc_buckets) == 2
        # ETH has data only in hour 10 → 1 bucket
        assert len(eth_buckets) == 1

    def test_daily_bucket_count(self, sample_data):
        """Test that daily bucketing collapses everything into 1 bucket per asset."""
        results = compute_aggregation(sample_data, '1d')
        btc_buckets = [r for r in results if r['asset_symbol'] == 'BTC']
        eth_buckets = [r for r in results if r['asset_symbol'] == 'ETH']
        assert len(btc_buckets) == 1
        assert len(eth_buckets) == 1

    def test_message_volume(self, sample_data):
        """Test that message_volume correctly counts rows per bucket."""
        results = compute_aggregation(sample_data, '1h')
        btc_hour_10 = [r for r in results if r['asset_symbol'] == 'BTC' and r['time_bucket'].hour == 10][0]
        assert btc_hour_10['message_volume'] == 2

    def test_simple_average(self, sample_data):
        """Test that avg_sentiment matches the simple arithmetic mean."""
        results = compute_aggregation(sample_data, '1h')
        btc_hour_10 = [r for r in results if r['asset_symbol'] == 'BTC' and r['time_bucket'].hour == 10][0]
        # (0.8 + 0.6) / 2 = 0.7
        assert abs(btc_hour_10['avg_sentiment'] - 0.7) < 0.001

    def test_weighted_average(self, sample_data):
        """Test that weighted_avg_sentiment matches hand-calculated value."""
        results = compute_aggregation(sample_data, '1h')
        btc_hour_10 = [r for r in results if r['asset_symbol'] == 'BTC' and r['time_bucket'].hour == 10][0]
        # weighted = (0.8*0.9 + 0.6*0.5) / (0.9 + 0.5) = (0.72 + 0.30) / 1.4 = 1.02 / 1.4 ≈ 0.728571
        expected = (0.8 * 0.9 + 0.6 * 0.5) / (0.9 + 0.5)
        assert abs(btc_hour_10['weighted_avg_sentiment'] - round(expected, 6)) < 0.001

    def test_empty_input(self):
        """Test that empty input returns empty results."""
        results = compute_aggregation([], '1h')
        assert results == []

    def test_zero_credibility(self):
        """Test that zero credibility falls back to simple average."""
        data = [
            {'asset_symbol': 'BTC', 'sentiment_score': 0.5, 'credibility_score': 0.0, 'event_timestamp': '2022-01-01 10:00:00'},
            {'asset_symbol': 'BTC', 'sentiment_score': 0.3, 'credibility_score': 0.0, 'event_timestamp': '2022-01-01 10:30:00'},
        ]
        results = compute_aggregation(data, '1h')
        assert len(results) == 1
        # Fallback to simple average: (0.5 + 0.3) / 2 = 0.4
        assert abs(results[0]['weighted_avg_sentiment'] - 0.4) < 0.001
