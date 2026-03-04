"""
Tests for the Correlation & Divergence Engine.

Tests the correlation and divergence logic in isolation using
mocked DataFrames (no database required).
"""

import pytest
import pandas as pd
import numpy as np


def compute_correlation(agg_records, price_records, divergence_threshold=0.5):
    """
    Pure-function version of the correlation logic for testing.
    
    Args:
        agg_records: list of dicts with keys: asset_symbol, time_bucket, avg_sentiment_score, weighted_avg_sentiment, message_volume
        price_records: list of dicts with keys: event_date, price_close
        divergence_threshold: threshold for generating alerts
        
    Returns:
        tuple: (correlations_list, alerts_list)
    """
    if not agg_records:
        return [], []

    agg_df = pd.DataFrame(agg_records)
    agg_df['time_bucket'] = pd.to_datetime(agg_df['time_bucket'])
    agg_df['join_date'] = agg_df['time_bucket'].dt.date

    price_df = pd.DataFrame(price_records)
    price_df['event_date'] = pd.to_datetime(price_df['event_date'])
    price_df['join_date'] = price_df['event_date'].dt.date

    # Price change calculation
    price_df = price_df.sort_values('join_date')
    price_df['price_change_pct'] = price_df['price_close'].pct_change() * 100
    price_df['price_change_pct'] = price_df['price_change_pct'].fillna(0)

    # Join
    merged = pd.merge(
        agg_df,
        price_df[['join_date', 'price_close', 'price_change_pct']],
        on='join_date',
        how='inner'
    )

    if merged.empty:
        return [], []

    # Normalize price change
    max_abs_pct = merged['price_change_pct'].abs().max()
    if max_abs_pct > 0:
        merged['norm_price_change'] = merged['price_change_pct'] / max_abs_pct
    else:
        merged['norm_price_change'] = 0

    merged['divergence'] = merged['weighted_avg_sentiment'] - merged['norm_price_change']

    # Build results
    correlations = []
    alerts = []

    for _, row in merged.iterrows():
        corr = {
            'asset_symbol': row['asset_symbol'],
            'time_bucket': row['time_bucket'],
            'price_close': round(row['price_close'], 2),
            'price_change_pct': round(row['price_change_pct'], 4),
            'divergence': round(row['divergence'], 6),
            'message_volume': int(row['message_volume'])
        }
        correlations.append(corr)

        if abs(row['divergence']) > divergence_threshold:
            alerts.append({
                'asset_symbol': row['asset_symbol'],
                'alert_type': 'divergence',
                'divergence': round(row['divergence'], 4),
                'event_timestamp': row['time_bucket']
            })

    return correlations, alerts


class TestCorrelationEngine:
    """Tests for the correlation and divergence computation logic."""

    @pytest.fixture
    def sample_agg_data(self):
        """Aggregation data: 5 days of BTC sentiment."""
        return [
            {'asset_symbol': 'BTC', 'time_bucket': '2022-01-01', 'avg_sentiment_score': 0.5, 'weighted_avg_sentiment': 0.6, 'message_volume': 100},
            {'asset_symbol': 'BTC', 'time_bucket': '2022-01-02', 'avg_sentiment_score': 0.7, 'weighted_avg_sentiment': 0.8, 'message_volume': 150},
            {'asset_symbol': 'BTC', 'time_bucket': '2022-01-03', 'avg_sentiment_score': -0.3, 'weighted_avg_sentiment': -0.2, 'message_volume': 200},
            {'asset_symbol': 'BTC', 'time_bucket': '2022-01-04', 'avg_sentiment_score': 0.1, 'weighted_avg_sentiment': 0.05, 'message_volume': 80},
            {'asset_symbol': 'BTC', 'time_bucket': '2022-01-05', 'avg_sentiment_score': 0.9, 'weighted_avg_sentiment': 0.85, 'message_volume': 300},
        ]

    @pytest.fixture
    def sample_price_data(self):
        """Price data: 5 days of BTC prices."""
        return [
            {'event_date': '2022-01-01', 'price_close': 47000.0},
            {'event_date': '2022-01-02', 'price_close': 47500.0},
            {'event_date': '2022-01-03', 'price_close': 46000.0},
            {'event_date': '2022-01-04', 'price_close': 46200.0},
            {'event_date': '2022-01-05', 'price_close': 43000.0},
        ]

    def test_correlation_count(self, sample_agg_data, sample_price_data):
        """Test that we get one correlation record per matched date."""
        correlations, _ = compute_correlation(sample_agg_data, sample_price_data)
        assert len(correlations) == 5

    def test_price_change_pct_first_row(self, sample_agg_data, sample_price_data):
        """Test that the first row has 0% price change."""
        correlations, _ = compute_correlation(sample_agg_data, sample_price_data)
        assert correlations[0]['price_change_pct'] == 0.0

    def test_price_change_pct_calculation(self, sample_agg_data, sample_price_data):
        """Test price change percentage is calculated correctly."""
        correlations, _ = compute_correlation(sample_agg_data, sample_price_data)
        # Day 2: (47500 - 47000) / 47000 * 100 ≈ 1.0638%
        expected_pct = (47500 - 47000) / 47000 * 100
        assert abs(correlations[1]['price_change_pct'] - round(expected_pct, 4)) < 0.01

    def test_divergence_alert_generation(self, sample_agg_data, sample_price_data):
        """Test that alerts are generated when divergence exceeds the threshold."""
        _, alerts = compute_correlation(sample_agg_data, sample_price_data, divergence_threshold=0.5)
        # At least one alert should be generated for these test values
        assert len(alerts) > 0
        assert all(a['alert_type'] == 'divergence' for a in alerts)

    def test_no_alerts_with_high_threshold(self, sample_agg_data, sample_price_data):
        """Test that no alerts are generated when threshold is very high."""
        _, alerts = compute_correlation(sample_agg_data, sample_price_data, divergence_threshold=100.0)
        assert len(alerts) == 0

    def test_empty_aggregation_data(self, sample_price_data):
        """Test that empty aggregation data returns empty results."""
        correlations, alerts = compute_correlation([], sample_price_data)
        assert correlations == []
        assert alerts == []

    def test_no_matching_dates(self):
        """Test that non-overlapping dates produce empty results."""
        agg = [{'asset_symbol': 'BTC', 'time_bucket': '2022-06-01', 'avg_sentiment_score': 0.5, 'weighted_avg_sentiment': 0.5, 'message_volume': 10}]
        price = [{'event_date': '2022-01-01', 'price_close': 47000.0}]
        correlations, alerts = compute_correlation(agg, price)
        assert correlations == []
        assert alerts == []

    def test_divergence_sign(self, sample_agg_data, sample_price_data):
        """
        Test divergence sign interpretation:
        - Positive divergence = bullish sentiment + bearish/flat price
        - Negative divergence = bearish sentiment + bullish price
        """
        correlations, _ = compute_correlation(sample_agg_data, sample_price_data)
        # Day 5: sentiment is 0.85 but price dropped significantly → positive divergence
        day5 = correlations[4]
        assert day5['divergence'] > 0, "Day 5 should have positive divergence (bullish sentiment, bearish price)"
